<#
Host launcher of the transcriber: the only place that knows how to run its Docker image.
Trascrivi.bat, Verifica.bat and agents all go through it, so people and agents get the same behavior.

  powershell -NoProfile -ExecutionPolicy Bypass -File trascrittore.ps1 <command> [arguments]

Run "help" for the commands. Trascrivi.bat and Verifica.bat use two more, "interactive" and "verify",
which ask the person questions and then run the same commands. Every command ends with one JSON result summary on standard output;
lines for people go to standard error. This file stays ASCII: Windows PowerShell 5.1 reads a
script without a byte order mark in the ANSI code page.
#>

# Agents run this without a console; there the encoding cannot be set, and every summary is ASCII anyway.
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch { }

$Image = 'meeting-transcriber:pilot'
# One transcription at a time: Docker refuses a second container with this name.
$TranscriptionName = 'meeting-transcriber-trascrizione'
$Here = $PSScriptRoot
$Voices = Join-Path $Here 'voci'
$Config = Join-Path $Here 'meeting.ini'
$DataDir = Join-Path $env:LOCALAPPDATA 'MeetingTranscriber'
$Cache = Join-Path $DataDir 'cache'
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
  listen <trascrizione.json> "Persona 2" [...] [--recording <file>] [--open]
      Prepara, per ogni voce, un file con le sue 1-2 clip migliori. Con --open lo apre nel lettore
      predefinito del PC, perche' la persona senta di chi e' la voce prima di darle un nome.
  name <trascrizione.json> "Persona 2=Nome Cognome" [...] [--recording <file>]
      Da' i nomi alle voci "Persona N": riscrive i due file della trascrizione senza trascrivere di
      nuovo, e aggiunge le clip di ogni voce nominata alla libreria "voci". Usa solo nomi che la
      persona ha confermato o scritto, dopo aver ascoltato le clip di "listen".
  check [<trascrizione.json> ...]
      Verifica quanto bene la libreria riconosce le voci a cui una persona ha dato il nome, nelle
      trascrizioni da cui sono state aggiunte clip e in quelle indicate, e suggerisce una soglia.
      Non cambia mai meeting.ini.
  trial [--reviewed]
      Riporta il periodo di prova della selezione automatica delle clip. Quando "ready" e' vero,
      chiedi alla persona se ha ascoltato tutte le clip aggiunte e cancellato quelle brutte: solo se
      risponde di si', ripeti con --reviewed e la selezione iniziera' a scartare da sola.
  help
      Mostra questo testo.

Ogni comando scrive le righe per le persone su stderr e finisce con un riepilogo JSON su stdout:
"status" (ok, invalid_arguments, file_not_found, unreadable_audio, gpu_out_of_memory, busy,
docker_not_running, not_installed, interrupted, error) e "message" in italiano, piu' i campi del
comando. Uscita: 0 riuscito, 2 argomenti non validi, 3 un'altra trascrizione in corso,
130 interrotto, 1 ogni altro errore.
"@


function Write-Line([string]$Text = '') {
    [Console]::Error.WriteLine($Text)
}

function Get-ExitCode([string]$Status) {
    switch ($Status) {
        'ok' { return 0 }
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

function Split-Arguments([string]$Command, [object[]]$Arguments, [string[]]$ValueOptions, [string[]]$SwitchOptions) {
    $positional = New-Object System.Collections.ArrayList
    $options = @{}
    for ($i = 0; $i -lt $Arguments.Count; $i++) {
        $argument = [string]$Arguments[$i]
        # Windows PowerShell 5.1 passes these to docker incorrectly, and no valid input needs them.
        if ($argument.Contains('"') -or ($argument.EndsWith('\') -and -not (Test-Path -LiteralPath $argument))) {
            Exit-With $Command 'invalid_arguments' "Argomento non valido: $argument"
        }
        if ($ValueOptions -contains $argument) {
            if ($i + 1 -ge $Arguments.Count) { Exit-With $Command 'invalid_arguments' "Manca il valore di $argument." }
            $i++
            $options[$argument] = [string]$Arguments[$i]
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

function Get-DockerArguments($Plan, [bool]$Gpu, [bool]$CpuFallback) {
    # The trailing | keeps the value from ending with a backslash.
    $arguments = @('run', '--rm', '-e', 'TZ=Europe/Rome', '-e', ('MEETING_HOST_PATHS=' + ($Plan.HostPaths -join '|') + '|'))
    if ($Plan.Transcription) { $arguments += @('--name', $TranscriptionName) }
    if ($Gpu) { $arguments += @('--gpus', 'all') }
    if ($CpuFallback) { $arguments += @('-e', 'MEETING_GPU_FALLBACK=docker') }
    $arguments += @($Plan.Mounts)
    if (Test-Path -LiteralPath $Config -PathType Leaf) {
        $arguments += @('-v', ($Config + ':/config/meeting.ini:ro'), '-e', 'MEETING_CONFIG=/config/meeting.ini')
    }
    $arguments += $Image
    $arguments += @($Plan.Arguments)
    return , $arguments
}

function Invoke-Plan($Plan) {
    # A transcription asks Docker for the GPU and, when Docker cannot start the container with it
    # (exit status 125), retries on the CPU. The other commands always use the CPU.
    # Standard output is captured: it carries only the summary, and progress on stderr still shows live.
    $script:RunLines = @()
    $attempts = if ($Plan.Transcription) { @('gpu', 'cpu') } else { @('cpu') }
    foreach ($attempt in $attempts) {
        $dockerArguments = Get-DockerArguments $Plan ($attempt -eq 'gpu') ($Plan.Transcription -and $attempt -eq 'cpu')
        $script:RunLines = @(& docker @dockerArguments)
        $script:RunCode = $LASTEXITCODE
        if ($script:RunCode -ne 125) { return }
        if ($Plan.Transcription -and (Test-Busy)) { return }
        if ($attempt -eq 'gpu') {
            Write-Line ''
            Write-Line "Docker non riesce a usare la GPU: riprovo sulla CPU, sara' molto piu' lento."
        }
    }
}

function Exit-WithoutSummary($Plan) {
    # The container ended without the command's summary: say why, as far as the exit status tells.
    if ($script:RunCode -eq 125) {
        if ($Plan.Transcription -and (Test-Busy)) {
            Exit-With $Plan.Command 'busy' "Un'altra trascrizione e' in corso su questo PC: aspetta che finisca e riprova."
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
    if ($Plan.Open -and $summary.status -eq 'ok') { Open-ListeningFiles $summary }
    if ($Plan.Command -eq 'name') { Clear-ListeningFiles }
    exit $script:RunCode
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
    Add-Mount $plan (Split-Path -Parent $recording) '/audio'
    Add-Mount $plan $Voices '/voci' -ReadOnly
    [void]$plan.Arguments.AddRange(@('transcribe', ('/audio/' + (Split-Path -Leaf $recording))))
    if ($parsed.Options['--speakers']) { [void]$plan.Arguments.AddRange(@('--speakers', $parsed.Options['--speakers'])) }
    if ($parsed.Options['--out-dir']) {
        $outDir = [IO.Path]::GetFullPath([IO.Path]::Combine((Get-Location).ProviderPath, $parsed.Options['--out-dir']))
        New-Item -ItemType Directory -Force -Path $outDir | Out-Null
        Add-Mount $plan $outDir '/out'
        [void]$plan.Arguments.AddRange(@('--out-dir', '/out'))
    }
    return $plan
}

function New-TranscriptPlan([string]$Command, [object[]]$Arguments, [string[]]$SwitchOptions) {
    # name and listen: a transcript, its labels, and the recording the clips are cut from.
    $parsed = Split-Arguments $Command $Arguments @('--recording') $SwitchOptions
    if ($parsed.Positional.Count -lt 2) {
        $example = if ($Command -eq 'name') { '"Persona 2=Nome Cognome"' } else { '"Persona 2"' }
        Exit-With $Command 'invalid_arguments' "Indica la trascrizione .json e almeno una voce: $Command <trascrizione.json> $example"
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
    if ($Command -eq 'name') { Add-Mount $plan $Voices '/voci' }
    else { Add-Mount $plan $Voices '/voci' -ReadOnly }
    $plan.Open = [bool]$parsed.Options['--open']
    if ($Command -eq 'listen') {
        New-Item -ItemType Directory -Force -Path $ListenDir | Out-Null
        Add-Mount $plan $ListenDir '/ascolto'
        [void]$plan.Arguments.AddRange(@('--out-dir', '/ascolto'))
    }
    return $plan
}

function Open-ListeningFiles($Summary) {
    foreach ($speaker in @($Summary.speakers)) {
        if ($speaker.file) { Invoke-Item -LiteralPath $speaker.file }
    }
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

function Invoke-NamingQuestions([string]$Transcript) {
    # The person's path to naming: ask, let them listen, then call the same listen and name commands an agent uses.
    try { $payload = [IO.File]::ReadAllText($Transcript, [Text.Encoding]::UTF8) | ConvertFrom-Json }
    catch { Write-Line "Non riesco a leggere $Transcript come trascrizione."; return 1 }
    $anonymous = @($payload.speakers | Where-Object { $_.label -like 'Persona *' })
    if (-not $anonymous) { return 0 }

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
    Write-Line 'Alcune voci non sono state riconosciute. Scrivi il nome e premi Invio, oppure premi solo Invio per lasciare "Persona N".'
    Write-Line 'Un nome aggiunge la voce alla libreria "voci", cosi le prossime volte viene riconosciuta.'
    $names = [ordered]@{}
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
        if ($name) { $names[$speaker.label] = $name }
    }
    if (-not $names.Count) { return 0 }

    Write-Line ''
    Write-Line 'Preparo le voci da ascoltare...'
    $listening = Invoke-Summary (New-TranscriptPlan 'listen' (@($Transcript) + @($names.Keys) + $recordingOption) @())
    if ($listening.status -ne 'ok') { return (Get-ExitCode $listening.status) }

    $pairs = @()
    foreach ($speaker in @($listening.speakers)) {
        $name = $names[$speaker.label]
        if ($speaker.file) {
            Write-Line ''
            Write-Line "Si apre il lettore con la voce di $($speaker.label): ascoltala."
            Invoke-Item -LiteralPath $speaker.file
            if (-not (Read-YesNo "E' la voce di $name? (s/n)")) {
                Write-Line "Va bene: $($speaker.label) resta senza nome e non aggiungo niente alla libreria."
                continue
            }
        }
        $pairs += ($speaker.label + '=' + $name)
    }
    if (-not $pairs) { Clear-ListeningFiles; return 0 }

    Write-Line ''
    $named = Invoke-Summary (New-TranscriptPlan 'name' (@($Transcript) + $pairs + $recordingOption) @())
    Clear-ListeningFiles
    return (Get-ExitCode $named.status)
}

function Invoke-Interactive([object[]]$Arguments) {
    $script:Interactive = $true
    $file = Resolve-HostFile ([string]$Arguments[0])
    if (-not $file) { Write-Line ('File non trovato: ' + $Arguments[0]); exit 1 }
    if ($file.ToLowerInvariant().EndsWith('.json')) { exit (Invoke-NamingQuestions $file) }

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
    exit (Invoke-NamingQuestions $summary.transcript_json)
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

function Install-Skill {
    # Installa.bat calls this: the skill always comes with the image of the same version.
    if (-not (Test-Path -LiteralPath $SkillSource -PathType Leaf)) {
        Write-Line "Non trovo skill-trascrittore.md accanto a trascrittore.ps1: la skill per gli agenti non e' installata."
        exit 1
    }
    $text = [IO.File]::ReadAllText($SkillSource, [Text.Encoding]::UTF8).Replace('{{CARTELLA}}', $Here)
    foreach ($root in @((Join-Path $env:USERPROFILE '.claude\skills'), (Join-Path $env:USERPROFILE '.agents\skills'))) {
        $folder = Join-Path $root $SkillName
        New-Item -ItemType Directory -Force -Path $folder | Out-Null
        [IO.File]::WriteAllText((Join-Path $folder 'SKILL.md'), $text, (New-Object System.Text.UTF8Encoding $false))
    }
    Write-Line 'Skill per Claude Code e Codex installata: puoi chiedere al tuo agente di trascrivere una registrazione.'
    exit 0
}


$command = if ($args.Count) { [string]$args[0] } else { 'help' }
$rest = if ($args.Count -gt 1) { @($args[1..($args.Count - 1)]) } else { @() }
switch ($command) {
    'transcribe' { Complete-Plan (New-TranscribePlan $rest) }
    'name' { Complete-Plan (New-TranscriptPlan 'name' $rest @()) }
    'listen' { Complete-Plan (New-TranscriptPlan 'listen' $rest @('--open')) }
    'check' { Complete-Plan (New-CheckPlan $rest) }
    'trial' { Complete-Plan (New-TrialPlan $rest) }
    'interactive' { Invoke-Interactive $rest }
    'verify' { Invoke-Verify $rest }
    'install-skill' { Install-Skill }
    { $_ -in @('help', '--help', '-h', '/?') } { [Console]::Out.WriteLine($Help); exit 0 }
    default { Exit-With $command 'invalid_arguments' "Comando sconosciuto: $command. Vedi: trascrittore.ps1 help" }
}
