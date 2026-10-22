<#
Host launcher of the transcriber: the only place that knows how to run its Docker image.
Installa.bat, Trascrivi.bat, Verifica.bat and agents all go through it.

  powershell -NoProfile -ExecutionPolicy Bypass -File trascrittore.ps1 <command> [arguments]

Run "help" for the commands. Trascrivi.bat and Verifica.bat use two more, "interactive" and "verify",
which ask the person questions and then run the same commands. Every command ends with one JSON result summary on standard output;
lines for people go to standard error. This file stays ASCII: Windows PowerShell 5.1 reads a
script without a byte order mark in the ANSI code page.
#>

# Agents run this without a console; there the encoding cannot be set, and every summary is ASCII anyway.
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch { }

$Image = 'trascrittore:latest'
# One transcription at a time: Docker refuses a second container with this name.
$TranscriptionName = 'trascrittore-trascrizione'
$Here = $PSScriptRoot
$Voices = Join-Path $Here 'voci'
$Config = Join-Path $Here 'trascrittore.ini'
$DataDir = Join-Path $env:LOCALAPPDATA 'Trascrittore'
$Cache = Join-Path $DataDir 'cache'
$GpuModeFile = Join-Path $DataDir 'gpu-mode.txt'
$GpuMode = if (Test-Path -LiteralPath $GpuModeFile) { (Get-Content -LiteralPath $GpuModeFile -Raw).Trim() } else { 'gpu' }
if ($GpuMode -notin @('gpu', 'cpu')) { $GpuMode = 'gpu' }
$ListenDir = Join-Path $DataDir 'ascolto'
$SkillSource = Join-Path $Here 'skill-trascrittore.md'
$SkillName = 'trascrittore'
# In the interactive mode used by Trascrivi.bat, a person reads the lines and no summary is printed.
$script:Interactive = $false

$Help = @"
Trascrittore: trascrive registrazioni in italiano con i nomi di chi parla, tutto sul PC.

Uso: powershell -NoProfile -ExecutionPolicy Bypass -File "$Here\trascrittore.ps1" <comando> [argomenti]

Comandi:
  transcribe <registrazione> [--speakers N] [--out-dir <cartella>]
      Trascrive un file audio o video. Scrive "<nome> - trascrizione.txt" e ".json" accanto alla
      registrazione, o nella cartella indicata. Una trascrizione alla volta per PC. Dura minuti:
      avvialo in background e aspetta che finisca.
  listen <trascrizione.json> "Persona 2" [--clip N] [--recording <file>] [--open]
      Prepara una clip della voce da ascoltare: la migliore, o con --clip N la N-esima. Con --open
      la apre nel lettore predefinito del PC, perche' la persona senta di chi e' la voce prima di
      darle un nome. Una voce alla volta: la persona risponde prima di ascoltare la prossima. Vale
      anche per le voci riconosciute. Una voce senza clip intere si ascolta dal suo tratto piu' lungo.
  name <trascrizione.json> "Persona 2=Nome Cognome" [...] [--recording <file>]
      Da' i nomi alle voci "Persona N": riscrive i due file della trascrizione senza trascrivere di
      nuovo, aggiunge le clip di ogni voce nominata alla libreria "voci" e apre la cartella delle
      clip aggiunte. Usa solo nomi che la persona ha confermato o scritto, dopo "listen".
      Solo se la persona lo chiede, per una voce riconosciuta:
        --confirm "Nome Cognome"   conferma la voce e aggiunge altre sue clip (ripetibile);
        "Nome Cognome=Altro Nome" --correct   corregge il nome e da' le clip alla persona giusta.
      Stato "similar_name": un nome somiglia a una persona della libreria e non e' stato salvato
      niente. Chiedi chi intendeva e ripeti con il nome esatto della cartella, oppure aggiungi
      --new-person "Nome Cognome" se e' davvero una persona nuova.
      Stato "over_cap": i nomi sono applicati, e "over_cap" propone clip da togliere a chi ha
      superato il limite. Toglile con remove-clips solo se la persona conferma.
  remove-clips "Nome Cognome" "<clip.wav>" [...]
      Toglie dalla libreria le clip proposte in "over_cap", dopo la conferma della persona.
  check [<trascrizione.json> ...]
      Verifica quanto bene la libreria riconosce le voci a cui una persona ha dato il nome, nelle
      trascrizioni da cui sono state aggiunte clip e in quelle indicate, e suggerisce una soglia.
      Non cambia mai trascrittore.ini.
  trial [--reviewed]
      Riporta il periodo di prova della selezione automatica delle clip. Quando "ready" e' vero,
      chiedi alla persona se ha ascoltato tutte le clip aggiunte e cancellato quelle brutte: solo se
      risponde di si', ripeti con --reviewed e la selezione iniziera' a scartare da sola.
  help
      Mostra questo testo.

Ogni comando scrive le righe per le persone su stderr e finisce con un riepilogo JSON su stdout:
"status" (ok, over_cap, similar_name, invalid_arguments, invalid_settings, file_not_found,
unreadable_recording, gpu_out_of_memory, busy, docker_not_running, not_installed, interrupted, error)
e "message" in italiano, piu' i campi del comando. Uscita: 0 riuscito (anche over_cap), 2 argomenti
non validi, 3 un'altra trascrizione in corso, 130 interrotto, 1 ogni altro caso.
"@


function Write-Line([string]$Text = '') {
    [Console]::Error.WriteLine($Text)
}

function Get-ExitCode([string]$Status) {
    switch ($Status) {
        'ok' { return 0 }
        'over_cap' { return 0 }
        'invalid_arguments' { return 2 }
        'busy' { return 3 }
        'interrupted' { return 130 }
        default { return 1 }
    }
}

function Write-Summary($Summary) {
    if ($script:Interactive) { return }
    $json = $Summary | ConvertTo-Json -Compress -Depth 6
    # ASCII JSON reads the same whatever code page the caller uses.
    $json = [regex]::Replace($json, '[^\x00-\x7F]', { param($match) '\u{0:x4}' -f [int][char]$match.Value })
    [Console]::Out.WriteLine($json)
}

function Exit-With([string]$Command, [string]$Status, [string]$Message) {
    Write-Line "Errore: $Message"
    Write-Summary ([ordered]@{ command = $Command; status = $Status; message = $Message })
    exit (Get-ExitCode $Status)
}

function Split-Arguments([string]$Command, [object[]]$Arguments, [string[]]$ValueOptions, [string[]]$SwitchOptions, [string[]]$RepeatOptions = @()) {
    $positional = New-Object System.Collections.ArrayList
    $options = @{}
    foreach ($option in $RepeatOptions) { $options[$option] = New-Object System.Collections.ArrayList }
    for ($i = 0; $i -lt $Arguments.Count; $i++) {
        $argument = [string]$Arguments[$i]
        # Windows PowerShell 5.1 passes these to docker incorrectly, and no valid input needs them.
        if ($argument.Contains('"') -or ($argument.EndsWith('\') -and -not (Test-Path -LiteralPath $argument))) {
            Exit-With $Command 'invalid_arguments' "Argomento non valido: $argument"
        }
        if ($ValueOptions -contains $argument -or $RepeatOptions -contains $argument) {
            if ($i + 1 -ge $Arguments.Count) { Exit-With $Command 'invalid_arguments' "Manca il valore di $argument." }
            $i++
            if ($RepeatOptions -contains $argument) { [void]$options[$argument].Add([string]$Arguments[$i]) }
            else { $options[$argument] = [string]$Arguments[$i] }
        }
        elseif ($SwitchOptions -contains $argument) { $options[$argument] = $true }
        elseif ($argument.StartsWith('--')) { Exit-With $Command 'invalid_arguments' "Opzione sconosciuta: $argument. Vedi: trascrittore.ps1 help" }
        else { [void]$positional.Add($argument) }
    }
    return @{ Positional = @($positional); Options = $options }
}

function Resolve-HostFile([string]$Path) {
    if (-not $Path) { return $null }
    try { $full = [IO.Path]::GetFullPath([IO.Path]::Combine((Get-Location).ProviderPath, $Path)) }
    catch { return $null }
    if (Test-Path -LiteralPath $full -PathType Leaf) { return $full }
    return $null
}

function Get-JsonString([string]$Path, [string]$Key) {
    # A regular expression instead of ConvertFrom-Json, which refuses files over 2 MB in PowerShell 5.1.
    try { $text = [IO.File]::ReadAllText($Path, [Text.Encoding]::UTF8) } catch { return $null }
    $match = [regex]::Match($text, '"' + $Key + '":\s*"((?:[^"\\]|\\.)*)"')
    if (-not $match.Success) { return $null }
    return ('"' + $match.Groups[1].Value + '"') | ConvertFrom-Json
}

function Find-Recording([string]$Transcript) {
    # The recording the transcript names, or the file of the same name beside the transcript.
    $recorded = Get-JsonString $Transcript 'recording'
    if ($recorded -and (Test-Path -LiteralPath $recorded -PathType Leaf)) { return $recorded }
    $file = Get-JsonString $Transcript 'file'
    if ($file) {
        $beside = Join-Path (Split-Path -Parent $Transcript) $file
        if (Test-Path -LiteralPath $beside -PathType Leaf) { return $beside }
    }
    return $null
}

function Assert-Docker([string]$Command) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Exit-With $Command 'docker_not_running' "Docker Desktop non e' installato. Installalo e riprova."
    }
    & docker info 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Exit-With $Command 'docker_not_running' "Docker Desktop non e' avviato. Aprilo, aspetta che sia pronto e riprova."
    }
    & docker image inspect $Image 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Exit-With $Command 'not_installed' "Il trascrittore non e' installato: esegui prima Installa.bat."
    }
}

function Test-Busy {
    $running = & docker ps -q --filter ('name=^' + $TranscriptionName + '$') 2>$null
    return [bool]$running
}

function New-Plan([string]$Command) {
    New-Item -ItemType Directory -Force -Path $Voices, $Cache | Out-Null
    $plan = @{
        Command = $Command
        Transcription = $false
        Mounts = New-Object System.Collections.ArrayList
        HostPaths = New-Object System.Collections.ArrayList
        Arguments = New-Object System.Collections.ArrayList
    }
    Add-Mount $plan $Cache '/cache'
    return $plan
}

function Add-Mount($Plan, [string]$HostFolder, [string]$ContainerFolder, [switch]$ReadOnly) {
    # "C:\" would end the argument with a backslash, which Windows PowerShell 5.1 quotes wrongly.
    $source = if ($HostFolder.EndsWith('\')) { $HostFolder + '.' } else { $HostFolder }
    $spec = $source + ':' + $ContainerFolder + $(if ($ReadOnly) { ':ro' } else { '' })
    [void]$Plan.Mounts.Add('-v')
    [void]$Plan.Mounts.Add($spec)
    [void]$Plan.HostPaths.Add($ContainerFolder + '=' + $HostFolder.TrimEnd('\'))
}

function Get-DockerArguments($Plan, [bool]$Gpu) {
    # The trailing | keeps the value from ending with a backslash.
    $arguments = @('run', '--rm', '-e', 'TZ=Europe/Rome', '-e', ('TRANSCRIBER_HOST_PATHS=' + ($Plan.HostPaths -join '|') + '|'))
    if ($Plan.Transcription) { $arguments += @('--name', $TranscriptionName) }
    if ($Gpu) { $arguments += @('--gpus', 'all', '-e', 'TRANSCRIBER_REQUIRE_GPU=1') }
    $arguments += @($Plan.Mounts)
    if (Test-Path -LiteralPath $Config -PathType Leaf) {
        # The person's file holds only what they changed; the image has the defaults for everything else.
        $arguments += @('-v', ($Config + ':/config/trascrittore.ini:ro'), '-e', 'TRANSCRIBER_SETTINGS=/config/trascrittore.ini')
    }
    $arguments += $Image
    $arguments += @($Plan.Arguments)
    return , $arguments
}

function Invoke-Plan($Plan) {
    # The installer checks the GPU before selecting the active image. A later GPU failure
    # must be reported, not turned into a slow CPU transcription.
    $script:RunLines = @()
    $gpu = $Plan.Transcription -and $GpuMode -eq 'gpu'
    $dockerArguments = Get-DockerArguments $Plan $gpu
    $script:RunLines = @(& docker @dockerArguments)
    $script:RunCode = $LASTEXITCODE
}

function Exit-WithoutSummary($Plan) {
    # The container ended without the command's summary: say why, as far as the exit status tells.
    if ($script:RunCode -eq 125) {
        if ($Plan.Transcription -and (Test-Busy)) {
            Exit-With $Plan.Command 'busy' "Un'altra trascrizione e' in corso su questo PC: aspetta che finisca e riprova."
        }
        if ($Plan.Transcription -and $GpuMode -eq 'gpu') {
            Exit-With $Plan.Command 'error' "Docker non riesce a usare la GPU NVIDIA: controlla il driver, riavvia Docker Desktop e riprova."
        }
        Exit-With $Plan.Command 'error' "Docker non e' riuscito ad avviare il trascrittore: leggi i messaggi qui sopra."
    }
    if ($script:RunCode -eq 137) {
        Exit-With $Plan.Command 'error' ("Il trascrittore e' stato fermato per mancanza di memoria. Chiudi gli altri " +
            "programmi, oppure dai piu' memoria a Docker Desktop, e riprova.")
    }
    Exit-With $Plan.Command 'error' "Il trascrittore si e' fermato senza un risultato (codice $($script:RunCode)): leggi i messaggi qui sopra."
}

function Invoke-Summary($Plan) {
    # Run the command and return its summary; stdout carries nothing else, so capturing it delays nothing.
    Invoke-Plan $Plan
    $summary = ConvertFrom-Summary $script:RunLines
    if (-not $summary) { Exit-WithoutSummary $Plan }
    return $summary
}

function Clear-ListeningFiles {
    # The listening files are only for the check before naming. One still open in the player stays until the next listen.
    Get-ChildItem -LiteralPath $ListenDir -Filter 'ascolta *.wav' -ErrorAction SilentlyContinue |
        Remove-Item -ErrorAction SilentlyContinue
}

function Complete-Plan($Plan) {
    # Pass the command's own summary and exit status through, or write one when there is none.
    $summary = Invoke-Summary $Plan
    foreach ($line in $script:RunLines) { [Console]::Out.WriteLine($line) }
    if ($Plan.Open -and $summary.status -eq 'ok') { Open-ListeningFile $summary }
    if ($Plan.Command -eq 'name') {
        Open-ClipFolders $summary
        Clear-ListeningFiles
    }
    exit $script:RunCode
}

function Open-ClipFolders($Summary) {
    # After a naming saves clips, the person reviews them there and deletes the bad ones.
    if ($Summary.status -notin @('ok', 'over_cap')) { return }
    $folders = @($Summary.named | Where-Object { $_.clips_added -and $_.folder } | ForEach-Object { $_.folder } | Select-Object -Unique)
    foreach ($folder in $folders) {
        if (Test-Path -LiteralPath $folder -PathType Container) {
            try { Invoke-Item -LiteralPath $folder } catch { Write-Line "Le clip aggiunte sono in $folder" }
        }
    }
}

function ConvertFrom-Summary([object[]]$Lines) {
    $last = $Lines | Where-Object { $_ -and $_.TrimStart().StartsWith('{') } | Select-Object -Last 1
    if (-not $last) { return $null }
    try { return $last | ConvertFrom-Json } catch { return $null }
}

function Add-TranscriptMounts($Plan, [string]$Transcript, [string]$Recording, [switch]$ReadOnly) {
    Add-Mount $Plan (Split-Path -Parent $Transcript) '/transcript' -ReadOnly:$ReadOnly
    [void]$Plan.Arguments.Add('/transcript/' + (Split-Path -Leaf $Transcript))
    if ($Recording) {
        Add-Mount $Plan (Split-Path -Parent $Recording) '/recording' -ReadOnly
        $Plan.RecordingArgument = '/recording/' + (Split-Path -Leaf $Recording)
    }
}

function New-TranscribePlan([object[]]$Arguments) {
    $parsed = Split-Arguments 'transcribe' $Arguments @('--speakers', '--out-dir') @()
    if ($parsed.Positional.Count -ne 1) {
        Exit-With 'transcribe' 'invalid_arguments' 'Indica una registrazione: transcribe <file> [--speakers N] [--out-dir <cartella>]'
    }
    $recording = Resolve-HostFile $parsed.Positional[0]
    if (-not $recording) { Exit-With 'transcribe' 'file_not_found' ('File non trovato: ' + $parsed.Positional[0]) }
    Assert-Docker 'transcribe'
    if (Test-Busy) {
        Exit-With 'transcribe' 'busy' "Un'altra trascrizione e' in corso su questo PC: aspetta che finisca e riprova."
    }

    $plan = New-Plan 'transcribe'
    $plan.Transcription = $true
    Add-Mount $plan (Split-Path -Parent $recording) '/recording'
    Add-Mount $plan $Voices '/voci' -ReadOnly
    [void]$plan.Arguments.AddRange(@('transcribe', ('/recording/' + (Split-Path -Leaf $recording))))
    if ($parsed.Options['--speakers']) { [void]$plan.Arguments.AddRange(@('--speakers', $parsed.Options['--speakers'])) }
    if ($parsed.Options['--out-dir']) {
        $outDir = [IO.Path]::GetFullPath([IO.Path]::Combine((Get-Location).ProviderPath, $parsed.Options['--out-dir']))
        New-Item -ItemType Directory -Force -Path $outDir | Out-Null
        Add-Mount $plan $outDir '/out'
        [void]$plan.Arguments.AddRange(@('--out-dir', '/out'))
    }
    return $plan
}

function New-TranscriptPlan([string]$Command, [object[]]$Arguments) {
    # name and listen: a transcript, its labels, and the recording the clips are cut from.
    if ($Command -eq 'name') { $parsed = Split-Arguments $Command $Arguments @('--recording') @('--correct') @('--confirm', '--new-person') }
    else { $parsed = Split-Arguments $Command $Arguments @('--recording', '--clip') @('--open') }
    $labelCount = $parsed.Positional.Count - 1
    if ($Command -eq 'name') { $labelCount += $parsed.Options['--confirm'].Count }
    if ($parsed.Positional.Count -lt 1 -or $labelCount -lt 1) {
        $example = if ($Command -eq 'name') { '"Persona 2=Nome Cognome"' } else { '"Persona 2"' }
        Exit-With $Command 'invalid_arguments' "Indica la trascrizione .json e almeno una voce: $Command <trascrizione.json> $example"
    }
    if ($Command -eq 'listen' -and $labelCount -gt 1) {
        # Clips opened together cannot be told apart: the person hears one voice and answers before the next.
        Exit-With $Command 'invalid_arguments' 'Una voce alla volta: listen <trascrizione.json> "Persona 2". La persona la ascolta e risponde prima della prossima.'
    }
    $transcript = Resolve-HostFile $parsed.Positional[0]
    if (-not $transcript) { Exit-With $Command 'file_not_found' ('Trascrizione non trovata: ' + $parsed.Positional[0]) }
    if ($parsed.Options['--recording']) {
        $recording = Resolve-HostFile $parsed.Options['--recording']
        if (-not $recording) { Exit-With $Command 'file_not_found' ('Registrazione non trovata: ' + $parsed.Options['--recording']) }
    }
    else { $recording = Find-Recording $transcript }
    Assert-Docker $Command

    $plan = New-Plan $Command
    $plan.RecordingArgument = $null
    [void]$plan.Arguments.Add($Command)
    Add-TranscriptMounts $plan $transcript $recording -ReadOnly:($Command -ne 'name')
    [void]$plan.Arguments.AddRange(@($parsed.Positional | Select-Object -Skip 1))
    if ($plan.RecordingArgument) { [void]$plan.Arguments.AddRange(@('--recording', $plan.RecordingArgument)) }
    if ($Command -eq 'name') {
        Add-Mount $plan $Voices '/voci'
        foreach ($option in @('--confirm', '--new-person')) {
            foreach ($value in $parsed.Options[$option]) { [void]$plan.Arguments.AddRange(@($option, $value)) }
        }
        if ($parsed.Options['--correct']) { [void]$plan.Arguments.Add('--correct') }
    }
    else { Add-Mount $plan $Voices '/voci' -ReadOnly }
    $plan.Open = [bool]$parsed.Options['--open']
    if ($Command -eq 'listen') {
        New-Item -ItemType Directory -Force -Path $ListenDir | Out-Null
        Add-Mount $plan $ListenDir '/ascolto'
        [void]$plan.Arguments.AddRange(@('--out-dir', '/ascolto'))
        if ($parsed.Options['--clip']) { [void]$plan.Arguments.AddRange(@('--clip', $parsed.Options['--clip'])) }
    }
    return $plan
}

function New-RemovePlan([object[]]$Arguments) {
    $parsed = Split-Arguments 'remove-clips' $Arguments @() @()
    if ($parsed.Positional.Count -lt 2) {
        Exit-With 'remove-clips' 'invalid_arguments' 'Indica la persona e almeno una clip: remove-clips "Nome Cognome" "<clip.wav>" [...]'
    }
    Assert-Docker 'remove-clips'
    $plan = New-Plan 'remove-clips'
    Add-Mount $plan $Voices '/voci'
    [void]$plan.Arguments.Add('remove-clips')
    [void]$plan.Arguments.AddRange(@($parsed.Positional))
    return $plan
}

function Open-ListeningFile($Summary) {
    if ($Summary.file) { Invoke-Item -LiteralPath $Summary.file }
}

function New-CheckPlan([object[]]$Arguments) {
    $parsed = Split-Arguments 'check' $Arguments @() @()
    # The named transcripts on this PC are those the library's clips were cut from, plus any given here.
    $pairs = [ordered]@{}
    foreach ($record in @(Get-ChildItem -LiteralPath $Voices -Recurse -Filter 'clip.json' -ErrorAction SilentlyContinue)) {
        try { $clips = [IO.File]::ReadAllText($record.FullName, [Text.Encoding]::UTF8) | ConvertFrom-Json } catch { continue }
        foreach ($clip in $clips.PSObject.Properties) {
            $transcript = $clip.Value.transcript
            if ($transcript -and -not $pairs.Contains($transcript.ToLowerInvariant())) {
                $pairs[$transcript.ToLowerInvariant()] = @($transcript, $clip.Value.recording)
            }
        }
    }
    foreach ($given in $parsed.Positional) {
        $transcript = Resolve-HostFile $given
        if (-not $transcript) { Exit-With 'check' 'file_not_found' "Trascrizione non trovata: $given" }
        $pairs[$transcript.ToLowerInvariant()] = @($transcript, (Find-Recording $transcript))
    }
    Assert-Docker 'check'

    $plan = New-Plan 'check'
    Add-Mount $plan $Voices '/voci' -ReadOnly
    [void]$plan.Arguments.Add('check')
    $folders = @{}
    foreach ($pair in $pairs.Values) {
        $transcript, $recording = $pair
        if (-not $recording -or -not (Test-Path -LiteralPath $recording -PathType Leaf)) { $recording = Find-Recording $transcript }
        if (-not (Test-Path -LiteralPath $transcript -PathType Leaf) -or -not $recording) {
            [void]$plan.Arguments.AddRange(@('--missing', $transcript))
            continue
        }
        $paths = @()
        foreach ($file in @($transcript, $recording)) {
            $folder = Split-Path -Parent $file
            $key = $folder.ToLowerInvariant()
            if (-not $folders.ContainsKey($key)) {
                $folders[$key] = '/check/' + $folders.Count
                Add-Mount $plan $folder $folders[$key] -ReadOnly
            }
            $paths += $folders[$key] + '/' + (Split-Path -Leaf $file)
        }
        [void]$plan.Arguments.AddRange(@('--pair', $paths[0], $paths[1]))
    }
    return $plan
}

function New-TrialPlan([object[]]$Arguments) {
    $parsed = Split-Arguments 'trial' $Arguments @() @('--reviewed')
    Assert-Docker 'trial'
    $plan = New-Plan 'trial'
    # Passing the trial is recorded in the voice library.
    Add-Mount $plan $Voices '/voci'
    [void]$plan.Arguments.Add('trial')
    if ($parsed.Options['--reviewed']) { [void]$plan.Arguments.Add('--reviewed') }
    return $plan
}

function Format-Minutes([double]$Seconds) {
    $minutes = [math]::Round($Seconds / 60)
    if ($minutes -ge 1) { return "$minutes min" }
    return '<1 min'
}

function Read-YesNo([string]$Question) {
    while ($true) {
        $answer = (Read-Host $Question).Trim().ToLowerInvariant()
        if ($answer -in @('s', 'si', 'y')) { return $true }
        if ($answer -in @('n', 'no')) { return $false }
        Write-Line 'Rispondi s oppure n.'
    }
}

function Read-Choice([string]$Question, [string[]]$Answers) {
    while ($true) {
        $answer = (Read-Host $Question).Trim().ToLowerInvariant()
        if ($answer -eq 'si') { $answer = 's' }
        if ($Answers -contains $answer) { return $answer }
        Write-Line ('Rispondi ' + ($Answers -join ', ') + '.')
    }
}

function Read-Number([string]$Question, [int]$Max) {
    # Returns 0 for an empty answer.
    while ($true) {
        $answer = (Read-Host $Question).Trim()
        if (-not $answer) { return 0 }
        if ($answer -match '^[0-9]+$' -and [int]$answer -ge 1 -and [int]$answer -le $Max) { return [int]$answer }
        Write-Line "Scrivi un numero da 1 a $Max, oppure premi solo Invio."
    }
}

function Test-VoiceByEar([string]$Transcript, $Item, [object[]]$RecordingOption) {
    # The listening check: one clip at a time, the best first, until the person answers.
    # Returns $true to go on with the name, $false when the person rejects the voice, $null on an error.
    $clip = 1
    while ($true) {
        $plan = New-TranscriptPlan 'listen' (@($Transcript, $Item.Label, '--clip', [string]$clip) + $RecordingOption)
        $listening = Invoke-Summary $plan
        if ($listening.status -ne 'ok') { return $null }
        if ($listening.file) {
            Write-Line ''
            Write-Line "Si apre il lettore con la voce di $($Item.Label): ascoltala."
            Invoke-Item -LiteralPath $listening.file
        }
        elseif ($clip -eq 1) {
            Write-Line ''
            Write-Line "$($Item.Label): niente da ascoltare. $($listening.note)"
            return $true
        }
        else { Write-Line "Non ci sono altre clip di $($Item.Label)." }
        $more = $listening.clips -gt $clip
        $question = "E' la voce di $($Item.Name)? (s = si', n = no" + $(if ($more) { ', a = ascolta un''altra clip)' } else { ')' })
        $answer = Read-Choice $question $(if ($more) { @('s', 'n', 'a') } else { @('s', 'n') })
        if ($answer -eq 's') { return $true }
        if ($answer -eq 'n') { return $false }
        $clip++
    }
}

function Invoke-Naming([string]$Transcript, [object[]]$Items, [object[]]$RecordingOption) {
    # Call name as an agent would, and ask the person what name stops on: similar names and clips over the cap.
    $newPeople = @()
    while ($true) {
        $arguments = @($Transcript)
        foreach ($item in $Items) {
            if ($item.Kind -eq 'confirm') { $arguments += @('--confirm', $item.Label) }
            else { $arguments += ($item.Label + '=' + $item.Name) }
        }
        if (@($Items | Where-Object { $_.Kind -eq 'correct' }).Count) { $arguments += '--correct' }
        foreach ($person in $newPeople) { $arguments += @('--new-person', $person) }
        Write-Line ''
        $named = Invoke-Summary (New-TranscriptPlan 'name' ($arguments + $RecordingOption))
        if ($named.status -ne 'similar_name') { break }
        foreach ($entry in @($named.similar | Where-Object { $_ })) {
            $people = @($entry.people)
            Write-Line ''
            Write-Line "'$($entry.name)' somiglia a chi e' gia' nella libreria:"
            for ($i = 0; $i -lt $people.Count; $i++) { Write-Line ('  {0}. {1}' -f ($i + 1), $people[$i]) }
            $choice = Read-Number "Numero della persona che intendevi (Invio = e' una persona nuova, $($entry.name))" $people.Count
            $item = $Items | Where-Object { $_.Label -eq $entry.label } | Select-Object -First 1
            if ($choice) { $item.Name = $people[$choice - 1] }
            else { $newPeople += $entry.name }
        }
    }
    Clear-ListeningFiles
    Open-ClipFolders $named
    foreach ($entry in @($named.over_cap | Where-Object { $_ })) {
        $files = @($entry.remove)
        Write-Line ''
        Write-Line "$($entry.person) ha piu' di $($entry.cap) clip aggiunte. Propongo di togliere queste $($files.Count), delle registrazioni con piu' clip:"
        foreach ($file in $files) { Write-Line "  $file" }
        if (Read-YesNo "Le tolgo dalla libreria? (s/n)") {
            [void](Invoke-Summary (New-RemovePlan (@($entry.person) + $files)))
        }
    }
    return (Get-ExitCode $named.status)
}

function Invoke-NamingQuestions([string]$Transcript, [bool]$AllowRecognized) {
    # The person's path to naming: ask, let them listen, then call the same listen and name commands an agent uses.
    # A recognized speaker is confirmed or corrected only when the person drops a transcript to name it later.
    try { $payload = [IO.File]::ReadAllText($Transcript, [Text.Encoding]::UTF8) | ConvertFrom-Json }
    catch { Write-Line "Non riesco a leggere $Transcript come trascrizione."; return 1 }
    $anonymous = @($payload.speakers | Where-Object { $_.label -like 'Persona *' })
    $recognized = @($payload.speakers | Where-Object { $_.recognized -and $_.label -notlike 'Persona *' })
    $items = @()

    if ($anonymous) {
        Write-Line ''
        Write-Line 'Alcune voci non sono state riconosciute. Scrivi il nome e premi Invio, oppure premi solo Invio per lasciare "Persona N".'
        Write-Line 'Un nome aggiunge la voce alla libreria "voci", cosi le prossime volte viene riconosciuta.'
        foreach ($speaker in $anonymous) {
            $turns = @($payload.turns | Where-Object { $_.speaker -eq $speaker.label })
            Write-Line ''
            Write-Line ('{0}: {1} interventi, {2} di parlato' -f $speaker.label, $turns.Count, (Format-Minutes $speaker.speech_sec))
            $examples = $turns |
                Sort-Object -Property @{ Expression = { ($_.text -split '\s+').Count }; Descending = $true } |
                Select-Object -First 2 |
                Sort-Object -Property @{ Expression = { [double]$_.start_sec } }
            foreach ($turn in $examples) {
                $text = [string]$turn.text
                if ($text.Length -gt 160) { $text = $text.Substring(0, 157).TrimEnd() + '...' }
                Write-Line ('  [{0}] "{1}"' -f $turn.start, $text)
            }
            $name = (Read-Host ('Nome per ' + $speaker.label)).Trim()
            if ($name) { $items += [pscustomobject]@{ Label = $speaker.label; Name = $name; Kind = 'name' } }
        }
    }

    if ($AllowRecognized -and $recognized) {
        Write-Line ''
        if (Read-YesNo 'Vuoi confermare o correggere una voce riconosciuta? (s/n)') {
            while ($recognized) {
                Write-Line ''
                for ($i = 0; $i -lt $recognized.Count; $i++) {
                    Write-Line ('  {0}. {1} ({2} di parlato)' -f ($i + 1), $recognized[$i].label, (Format-Minutes $recognized[$i].speech_sec))
                }
                $choice = Read-Number 'Numero della voce (Invio = basta cosi)' $recognized.Count
                if (-not $choice) { break }
                $label = $recognized[$choice - 1].label
                $recognized = @($recognized | Where-Object { $_.label -ne $label })
                $name = (Read-Host "Nome giusto per $label (Invio = e' davvero $label, aggiungi altre sue clip)").Trim()
                if ($name -and $name -ne $label) { $items += [pscustomobject]@{ Label = $label; Name = $name; Kind = 'correct' } }
                else { $items += [pscustomobject]@{ Label = $label; Name = $label; Kind = 'confirm' } }
            }
        }
    }
    if (-not $items) { return 0 }

    # Like --recording for an agent: a recording that moved can be given here.
    $recordingOption = @()
    if (-not (Find-Recording $Transcript)) {
        Write-Line ''
        Write-Line "Non trovo la registrazione di questa trascrizione ($($payload.file))."
        $answer = (Read-Host 'Trascinala qui e premi Invio, oppure premi solo Invio per dare i nomi senza aggiungere le voci alla libreria').Trim().Trim('"')
        $recording = Resolve-HostFile $answer
        if ($recording) { $recordingOption = @('--recording', $recording) }
        elseif ($answer) { Write-Line "File non trovato: $answer. Do i nomi senza aggiungere le voci alla libreria." }
    }

    Write-Line ''
    Write-Line 'Preparo le voci da ascoltare...'
    $confirmed = @()
    foreach ($item in $items) {
        $heard = Test-VoiceByEar $Transcript $item $recordingOption
        if ($null -eq $heard) { Clear-ListeningFiles; return 1 }
        if ($heard) { $confirmed += $item }
        else { Write-Line "Va bene: $($item.Label) resta com'e' e non aggiungo niente alla libreria." }
    }
    if (-not $confirmed) { Clear-ListeningFiles; return 0 }
    return (Invoke-Naming $Transcript $confirmed $recordingOption)
}

function Invoke-Interactive([object[]]$Arguments) {
    $script:Interactive = $true
    $file = Resolve-HostFile ([string]$Arguments[0])
    if (-not $file) { Write-Line ('File non trovato: ' + $Arguments[0]); exit 1 }
    if ($file.ToLowerInvariant().EndsWith('.json')) { exit (Invoke-NamingQuestions $file $true) }

    $speakers = $null
    while ($true) {
        $answer = (Read-Host 'Quante persone parlano nella registrazione? (Invio = non lo so)').Trim()
        if (-not $answer -or $answer -match '^[1-9][0-9]*$') { $speakers = $answer; break }
        Write-Line 'Scrivi un numero (per esempio 4), oppure premi solo Invio.'
    }
    Write-Line ''
    $arguments = @($file)
    if ($speakers) { $arguments += @('--speakers', $speakers) }
    $summary = Invoke-Summary (New-TranscribePlan $arguments)
    if ($summary.status -ne 'ok') { exit (Get-ExitCode $summary.status) }
    exit (Invoke-NamingQuestions $summary.transcript_json $false)
}

function Invoke-Verify([object[]]$Arguments) {
    # Verifica.bat: the recognition check, then the trial, which the person closes once they reviewed the clips.
    $script:Interactive = $true
    [void](Invoke-Summary (New-CheckPlan $Arguments))
    Write-Line ''
    $trial = Invoke-Summary (New-TrialPlan @())
    if ($trial.status -ne 'ok') { exit (Get-ExitCode $trial.status) }
    if ($trial.ready) {
        Write-Line ''
        if (Read-YesNo 'Hai ascoltato tutte le clip aggiunte alla libreria e cancellato quelle brutte? (s/n)') {
            $trial = Invoke-Summary (New-TrialPlan @('--reviewed'))
        }
        else { Write-Line "Allora ascoltale, cancella quelle brutte e rifai Verifica.bat." }
    }
    exit (Get-ExitCode $trial.status)
}

$SettingsTemplate = @'
; Impostazioni del trascrittore su questo PC.
; Scrivi qui solo quello che vuoi cambiare, sotto la sua sezione. Per esempio:
;
; [whisper]
; batch_size = 4
;
; Tutto il resto viene dal trascrittore, e ogni aggiornamento porta i valori nuovi.
; Le righe che iniziano con ; sono solo note.
'@

function Install-SettingsAndSkill {
    # Setup creates the settings file once; it holds the person's changes.
    if (-not (Test-Path -LiteralPath $Config)) {
        $lines = $SettingsTemplate.Replace("`r`n", "`n").Replace("`n", "`r`n") + "`r`n"
        [IO.File]::WriteAllText($Config, $lines, (New-Object System.Text.UTF8Encoding $false))
    }
    # The skill always comes with the image of the same version, so it is installed every time.
    $text = [IO.File]::ReadAllText($SkillSource, [Text.Encoding]::UTF8).Replace('{{CARTELLA}}', $Here)
    foreach ($root in @((Join-Path $env:USERPROFILE '.claude\skills'), (Join-Path $env:USERPROFILE '.agents\skills'))) {
        $folder = Join-Path $root $SkillName
        New-Item -ItemType Directory -Force -Path $folder | Out-Null
        [IO.File]::WriteAllText((Join-Path $folder 'SKILL.md'), $text, (New-Object System.Text.UTF8Encoding $false))
    }
    Write-Line 'Skill per Claude Code e Codex installata: puoi chiedere al tuo agente di trascrivere una registrazione.'
}


function Invoke-Setup {
    # Verify the local CUDA image before activating it.
    $ErrorActionPreference = 'Stop'

    function Assert-SupportedGpu([string]$Capability) {
        if ($Capability -notmatch '^(\d+)\.(\d+)$') {
            throw "Capacita GPU non riconosciuta: $Capability"
        }
        $major = [int]$Matches[1]
        if ($major -lt 7 -or $major -gt 12) {
            throw "Questa GPU (compute capability $Capability) non e' supportata. Serve una GPU NVIDIA con compute capability 7.0-12.x."
        }
    }

    function Get-InstalledImageId([string]$Tag) {
        $id = & docker image inspect -f '{{.Id}}' $Tag 2>$null
        if ($LASTEXITCODE -eq 0) { return ($id | Select-Object -First 1) }
        return $null
    }

    try {
        if (-not (Test-Path -LiteralPath $SkillSource -PathType Leaf)) {
            throw "Non trovo skill-trascrittore.md accanto a Installa.bat."
        }
        & docker info *> $null
        if ($LASTEXITCODE -ne 0) { throw "Docker Desktop non e' avviato. Aprilo, aspetta che sia pronto e riprova." }

        $smiPaths = @(
            (Join-Path $env:WINDIR 'System32\nvidia-smi.exe')
            (Join-Path $env:ProgramW6432 'NVIDIA Corporation\NVSMI\nvidia-smi.exe')
        )
        $smi = $smiPaths | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
        if (-not $smi) {
            $command = Get-Command nvidia-smi -ErrorAction SilentlyContinue
            $smi = if ($command) { $command.Source } else { $null }
        }
        $gpuLines = if ($smi) { @(& $smi --query-gpu=name,compute_cap --format=csv,noheader 2>$null) } else { @() }
        $smiOk = $smi -and $LASTEXITCODE -eq 0 -and $gpuLines.Count -gt 0
        $gpuMode = 'cpu'
        if ($smiOk) {
            foreach ($line in $gpuLines) {
                if ($line -notmatch ',\s*(\d+\.\d+)\s*$') { throw "nvidia-smi ha restituito un valore inatteso: $line" }
                Assert-SupportedGpu $Matches[1]
                Write-Host "GPU rilevata: $line"
            }
            $gpuMode = 'gpu'
        }
        else {
            $nvidiaController = Get-CimInstance Win32_VideoController -ErrorAction Stop |
                Where-Object { $_.Name -match 'NVIDIA' }
            if ($nvidiaController) {
                throw "Windows vede una GPU NVIDIA ma nvidia-smi non funziona. Aggiorna il driver NVIDIA e riprova."
            }
            Write-Warning "Nessuna GPU NVIDIA rilevata: la trascrizione usera' la CPU, molto piu' lentamente."
        }

        $archive = Join-Path $Here 'trascrittore-cu128.tar'
        if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
            throw "Manca trascrittore-cu128.tar accanto a Installa.bat. Chiedi questo archivio a chi ti ha dato il trascrittore."
        }
        $candidateTag = 'trascrittore:cu128'
        $oldId = Get-InstalledImageId $Image
        $promoted = $false
        try {
            Write-Host "Carico trascrittore-cu128.tar. Ci vuole qualche minuto..."
            & docker load -i $archive
            if ($LASTEXITCODE -ne 0) { throw "Il caricamento dell'immagine non e' riuscito." }
            $candidateId = Get-InstalledImageId $candidateTag
            if (-not $candidateId) { throw "L'archivio non contiene l'immagine $candidateTag." }

            if ($gpuMode -eq 'gpu') {
                Write-Host "Controllo i kernel GPU di PyTorch e CTranslate2..."
                & docker run --rm --gpus all --entrypoint python $candidateTag -m docker.gpu_probe
                if ($LASTEXITCODE -ne 0) { throw "Il controllo GPU e' fallito. La versione gia' installata resta attiva." }
            }
            & docker tag $candidateTag $Image
            if ($LASTEXITCODE -ne 0) { throw "Non riesco ad attivare l'immagine verificata." }
            $promoted = $true

            Install-SettingsAndSkill
            New-Item -ItemType Directory -Force -Path $Cache | Out-Null
            [IO.File]::WriteAllText($GpuModeFile, $gpuMode + "`n", [Text.Encoding]::ASCII)
            if ($oldId -and $oldId -ne $candidateId) {
                & docker image rm $oldId *> $null
                if ($LASTEXITCODE -ne 0) {
                    Write-Warning "La vecchia immagine e' ancora usata da un container; potrai liberare lo spazio dopo la sua chiusura."
                }
            }
            Write-Host "Installazione completata (CUDA 12.8, $gpuMode). Trascina una registrazione su Trascrivi.bat."
        }
        catch {
            if ($promoted) {
                if ($oldId) { & docker tag $oldId $Image | Out-Null }
                else { & docker image rm $Image | Out-Null }
            }
            throw
        }
    }
    catch {
        [Console]::Error.WriteLine("Installazione non riuscita: $($_.Exception.Message)")
        exit 1
    }
}

$command = if ($args.Count) { [string]$args[0] } else { 'help' }
$rest = if ($args.Count -gt 1) { @($args[1..($args.Count - 1)]) } else { @() }
switch ($command) {
    'transcribe' { Complete-Plan (New-TranscribePlan $rest) }
    'name' { Complete-Plan (New-TranscriptPlan 'name' $rest) }
    'listen' { Complete-Plan (New-TranscriptPlan 'listen' $rest) }
    'remove-clips' { Complete-Plan (New-RemovePlan $rest) }
    'check' { Complete-Plan (New-CheckPlan $rest) }
    'trial' { Complete-Plan (New-TrialPlan $rest) }
    'interactive' { Invoke-Interactive $rest }
    'verify' { Invoke-Verify $rest }
    'setup' { Invoke-Setup; exit 0 }
    { $_ -in @('help', '--help', '-h', '/?') } { [Console]::Out.WriteLine($Help); exit 0 }
    default { Exit-With $command 'invalid_arguments' "Comando sconosciuto: $command. Vedi: trascrittore.ps1 help" }
}
