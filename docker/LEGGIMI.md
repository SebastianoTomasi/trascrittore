# Trascrittore

Trascini una registrazione, audio o video, su `Trascrivi.bat` e, accanto al file, ottieni il testo con chi ha parlato e quando:

```
[00:12:34] Mario Rossi: allora partiamo dal budget
```

Tutto gira sul tuo PC: il trascrittore non manda niente a nessuno e funziona anche senza internet.

## Cosa serve

- Windows 10 o 11. Con una scheda NVIDIA supportata è veloce; senza una GPU NVIDIA, funziona sulla CPU ma molto più lentamente. Le schede NVIDIA più vecchie, come la MX230, non sono supportate perché la trascrizione è troppo lenta.
- Circa 30 GB liberi su disco. L'archivio TAR occupa circa 7 GB e puoi cancellarlo dopo l'installazione.

## Installazione (una volta sola)

1. Installa [Docker Desktop](https://www.docker.com/products/docker-desktop/) con le impostazioni predefinite. Riavvia il PC, apri Docker Desktop e aspetta che sia pronto. Al primo avvio accetta le condizioni d'uso e, se ti chiede di installare o aggiornare WSL, accetta. Se ti chiede di accedere, puoi saltare.
2. Crea una cartella sul PC, per esempio `C:\Trascrittore`, e scaricaci i file dal link di Google Drive che hai ricevuto: `trascrittore-cu128.tar`, `Installa.bat`, `Trascrivi.bat`, `Verifica.bat`, `trascrittore.ps1`, `skill-trascrittore.md`, `LICENZE.md` e questo `LEGGIMI.md`.
   - Meglio una cartella che OneDrive non sincronizza: se `Documenti` o il Desktop sono sincronizzati, OneDrive caricherebbe sul cloud gli archivi e poi la cartella `voci`.
   - Scaricali uno per uno: se scarichi tutta la cartella, Drive la divide in più file zip.
   - Per il file grande Google avvisa che non può controllarlo per i virus: scegli "Scarica comunque".
   - Se il browser dice che i file `.bat` o `.ps1` possono essere pericolosi, scegli "Mantieni".
3. Fai doppio clic su `Installa.bat`. Controlla che la GPU NVIDIA sia supportata, carica l'archivio e prova i calcoli GPU prima di attivarlo. Se il controllo fallisce, la versione già installata resta disponibile. Installa anche la skill che permette a Claude Code e Codex di usare il trascrittore, e crea `trascrittore.ini`, il file delle tue impostazioni.
   - Se Windows mostra "PC protetto da Windows", clicca "Ulteriori informazioni" e poi "Esegui comunque". Può succedere di nuovo la prima volta che usi `Trascrivi.bat` e `Verifica.bat`.
4. Finita l'installazione puoi cancellare `trascrittore-cu128.tar` e recuperare spazio.

Se sposti la cartella, fai di nuovo doppio clic su `Installa.bat`: la skill deve sapere dove si trova il trascrittore.

## Uso

1. Apri Docker Desktop, se non è già aperto.
2. Trascina la registrazione sopra `Trascrivi.bat`: audio o video, per esempio l'mp4 di una call su Teams. Un file alla volta, e deve essere sul PC, non "solo online".
3. Scrivi quante persone parlano, oppure premi solo Invio se non lo sai.
4. Alla fine, per ogni voce non riconosciuta, ti mostra due frasi di quella persona e ti chiede il nome. Con Invio resta "Persona 1", "Persona 2"…
5. Per le voci a cui hai dato un nome si apre il lettore con una clip di 10 secondi di quella voce: ascoltala e conferma che è davvero quella persona. Se non sei sicuro, rispondi `a` e ascolti la clip successiva. Solo quando confermi il nome va nella trascrizione e la voce entra nella libreria `voci`, così le prossime volte viene riconosciuta. Alla fine ti dice in quale cartella sono le clip aggiunte.
6. Se il nome che scrivi somiglia a quello di una persona già nella libreria (per esempio "Marco Rosi" quando c'è "Marco Rossi", "M. Rossi" o solo "Marco"), il programma ti chiede se intendevi lei o una persona nuova, prima di salvare qualsiasi cosa.

Accanto al file trovi:

- `<nome file> - trascrizione.txt`: il testo da leggere;
- `<nome file> - trascrizione.json`: gli stessi dati per i programmi, con la sicurezza del riconoscimento di ogni voce e l'inizio e la fine di ogni frase.

Con una GPU NVIDIA recente un'ora di registrazione richiede pochi minuti. Una GPU meno recente può impiegare di più, pur usando la GPU per tutte le fasi della trascrizione. Solo sulla CPU può volerci più della durata della registrazione. Si fa una trascrizione alla volta: se ne è già in corso una, aspetta che finisca.

**Dare i nomi più tardi.** Trascina il file `<nome file> - trascrizione.json` sopra `Trascrivi.bat`: ti fa le stesse domande sui nomi, senza trascrivere di nuovo. Se nel frattempo hai spostato la registrazione, ti chiede di trascinarla nella finestra.

**Confermare o correggere una voce riconosciuta.** Sempre trascinando il file `.json`, il programma ti chiede anche se vuoi confermare o correggere una voce che ha riconosciuto da solo. Scegli la voce dall'elenco, poi:

- premi solo Invio se è davvero quella persona: dopo l'ascolto aggiunge altre sue clip alla libreria, e ti dice se servono molto (il riconoscimento era incerto) o poco;
- scrivi il nome giusto se l'ha scambiata per un'altra: dopo l'ascolto corregge la trascrizione e dà le clip alla persona giusta. Le clip della persona sbagliata restano dove sono: ascoltale, cancella quelle che non sono sue e fai `Verifica.bat`.

Alla fine di una trascrizione questa domanda non compare: si fa solo quando lo chiedi tu.

## Con Claude Code o Codex

Dopo l'installazione puoi chiedere al tuo agente, per esempio: "trascrivi la registrazione che ho appena salvato con OBS" e poi "chi è Persona 2?". L'agente usa lo stesso trascrittore sul tuo PC, e la trascrizione non esce dal PC, a meno che l'agente non la legga per risponderti.

Un agente può proporti un nome, ma lo usa solo dopo che l'hai confermato, e prima ti fa ascoltare la voce. Una voce già riconosciuta la conferma o la corregge solo se glielo chiedi tu, per esempio "vorrei aggiungere delle clip di Sebastiano".

## Voci da riconoscere

Il programma riconosce solo le persone che hanno una cartella dentro `voci`, accanto a `Trascrivi.bat`.

1. Crea la cartella `voci\Nome Cognome`. Quel nome è quello che comparirà nel testo.
2. Mettici almeno **3 clip da 10–60 secondi** in cui parla solo quella persona: per esempio note vocali del telefono, oppure pezzi di altre registrazioni. Puoi partire dai file che ti ha mandato chi ti ha dato il trascrittore.
3. Vanno bene wav, mp3, m4a, flac, ogg, aac e opus. I video no.
4. Clip fatte in posti e con microfoni diversi (una stanza, una call, il telefono) aiutano il riconoscimento.

Se il programma non è abbastanza sicuro, preferisce scrivere "Persona N" piuttosto che un nome sbagliato.

Per non riconoscere più una persona, cancella la sua cartella dentro `voci`.

### Le voci a cui dai un nome

Quando dai un nome a una voce, le sue clip finiscono in `voci\Nome Cognome\registrazioni`. Il nome del file dice da quale registrazione vengono e da che minuto. Il programma tiene solo le clip migliori di ogni voce, al massimo 8 per registrazione, e scarta da solo quelle che somigliano poco alle altre. Se ne trovi una con altre voci, risate o rumori, puoi cancellarla.

Ogni persona tiene al massimo **64 clip** aggiunte dalle registrazioni (`max_clips` sotto `[library]` in `trascrittore.ini`). Quando una nuova registrazione supera il limite, il programma ti propone quali togliere, prendendole dalle registrazioni con più clip, e le toglie solo se confermi. Le clip che hai messo tu a mano non le tocca mai.

`Verifica.bat` controlla quanto bene vengono riconosciute le voci a cui hai dato un nome, e ti dice se conviene cambiare la soglia: in quel caso ti mostra la riga da scrivere in `trascrittore.ini`. Non la cambia mai da solo. Usalo ogni tanto, dopo aver dato qualche nome.

## Impostazioni

Le impostazioni stanno in `trascrittore.ini`, accanto a `Trascrivi.bat`: aprilo con Blocco note. Il file contiene solo quello che hai cambiato tu, ognuno sotto la sua sezione, per esempio:

```
[whisper]
batch_size = 4
```

Tutto il resto viene dal trascrittore, e ogni aggiornamento porta i valori nuovi. Le righe che iniziano con `;` sono solo note: la riga della sezione, come `[whisper]`, va scritta senza `;` davanti. Se scrivi una riga che il trascrittore non capisce, ti dice quale correggere.

Il trascrittore sceglie da solo il formato adatto alla GPU. Se in una versione precedente hai scritto `device = cpu`, cancellalo per usare la GPU NVIDIA. Puoi cancellare anche `compute_type = float16`, `float32` o `int8_float32` per tornare alla scelta automatica. Se una GPU NVIDIA smette di funzionare, la trascrizione si ferma e mostra un errore: aggiorna il driver NVIDIA, riavvia Docker Desktop e riprova.
Le GPU AMD e Intel non usano CUDA: il trascrittore funziona sulla CPU.

## Aggiornamenti

Quando esce una versione nuova, chi ti ha dato il trascrittore ti avvisa e ti dice quali file riscaricare: `trascrittore-cu128.tar` e, quando cambiano, anche gli script. Mettili nella stessa cartella e fai di nuovo doppio clic su `Installa.bat`. L'installazione verifica la nuova immagine prima di sostituire quella attiva. La cartella `voci` e il tuo `trascrittore.ini` restano come sono.

## Se qualcosa non va

| Messaggio | Cosa fare |
|---|---|
| Docker Desktop non è installato | Installalo come spiegato in "Installazione" e riprova. |
| Docker Desktop non è avviato | Apri Docker Desktop, aspetta che sia pronto e riprova. |
| Il trascrittore non è installato | Esegui `Installa.bat`. |
| Manca trascrittore-cu128.tar | Mettilo nella stessa cartella di `Installa.bat` e ripeti l'installazione. |
| Questa GPU NVIDIA non è supportata | Serve una scheda con compute capability 7.0–12.x. La MX230 non è supportata. |
| Windows vede una GPU NVIDIA ma nvidia-smi non funziona | Aggiorna il driver NVIDIA, riavvia il PC e ripeti `Installa.bat`. L'installer non passa alla CPU se vede una GPU NVIDIA. |
| Un'altra trascrizione è in corso su questo PC | Aspetta che finisca e riprova. |
| Non riesco a leggere la registrazione | Controlla che sia un file audio o video e che sia sul PC: se è "solo online" su OneDrive o Google Drive, scaricalo prima. |
| ATTENZIONE: GPU NVIDIA non utilizzabile, elaboro su CPU | Il PC è stato installato senza GPU NVIDIA. Funziona lo stesso, ma più lentamente. |
| La GPU NVIDIA non funziona | Aggiorna il driver NVIDIA, riavvia Docker Desktop e riprova. Se l'errore compare durante l'installazione, la versione precedente resta attiva. |
| Memoria della GPU esaurita | Apri `trascrittore.ini` con Blocco note e aggiungi in fondo le due righe `[whisper]` e `batch_size = 4`, come nell'esempio di "Impostazioni". Salva e riprova. Se non basta, metti 2, poi 1. Sulle GPU da 4 GB il valore scende già a 1 automaticamente. |
| trascrittore.ini, riga … | Correggi o cancella quella riga di `trascrittore.ini` e riprova. |

Per qualsiasi altro errore manda una foto della finestra a chi ti ha dato il trascrittore.
