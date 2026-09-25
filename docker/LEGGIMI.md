# Trascrittore

Trascini una registrazione, audio o video, su `Trascrivi.bat` e, accanto al file, ottieni il testo con chi ha parlato e quando:

```
[00:12:34] Mario Rossi: allora partiamo dal budget
```

Tutto gira sul tuo PC: il trascrittore non manda niente a nessuno e funziona anche senza internet.

## Cosa serve

- Windows 10 o 11. Con una scheda NVIDIA è veloce; senza, funziona sulla CPU ma molto più lentamente, e il programma lo scrive chiaramente.
- Circa 30 GB liberi su disco: Docker occupa circa 20 GB, più i 7 GB di `trascrittore.tar`, che puoi cancellare dopo l'installazione.

## Installazione (una volta sola)

1. Installa [Docker Desktop](https://www.docker.com/products/docker-desktop/) con le impostazioni predefinite. Riavvia il PC, apri Docker Desktop e aspetta che sia pronto. Al primo avvio accetta le condizioni d'uso e, se ti chiede di installare o aggiornare WSL, accetta. Se ti chiede di accedere, puoi saltare.
2. Crea una cartella sul PC, per esempio `C:\Trascrittore`, e scaricaci i file dal link di Google Drive che hai ricevuto: `trascrittore.tar`, `Installa.bat`, `Trascrivi.bat`, `Verifica.bat`, `trascrittore.ps1`, `skill-trascrittore.md`, `LICENZE.md` e questo `LEGGIMI.md`.
   - Meglio una cartella che OneDrive non sincronizza: se `Documenti` o il Desktop sono sincronizzati, OneDrive caricherebbe sul cloud i 7 GB di `trascrittore.tar` e poi la cartella `voci`.
   - Scaricali uno per uno: se scarichi tutta la cartella, Drive la divide in più file zip.
   - Per il file grande Google avvisa che non può controllarlo per i virus: scegli "Scarica comunque".
   - Se il browser dice che i file `.bat` o `.ps1` possono essere pericolosi, scegli "Mantieni".
3. Fai doppio clic su `Installa.bat`. Ci mette qualche minuto e alla fine ti dice se la GPU funziona. Installa anche la skill che permette a Claude Code e Codex di usare il trascrittore, e crea `trascrittore.ini`, il file delle tue impostazioni.
   - Se Windows mostra "PC protetto da Windows", clicca "Ulteriori informazioni" e poi "Esegui comunque". Può succedere di nuovo la prima volta che usi `Trascrivi.bat` e `Verifica.bat`.
4. Finita l'installazione puoi cancellare `trascrittore.tar` e recuperare 7 GB.

Se sposti la cartella, fai di nuovo doppio clic su `Installa.bat`: la skill deve sapere dove si trova il trascrittore.

## Uso

1. Apri Docker Desktop, se non è già aperto.
2. Trascina la registrazione sopra `Trascrivi.bat`: audio o video, per esempio l'mp4 di una call su Teams. Un file alla volta, e deve essere sul PC, non "solo online".
3. Scrivi quante persone parlano, oppure premi solo Invio se non lo sai.
4. Alla fine, per ogni voce non riconosciuta, ti mostra due frasi di quella persona e ti chiede il nome. Con Invio resta "Persona 1", "Persona 2"…
5. Per le voci a cui hai dato un nome si apre il lettore con qualche secondo di quella voce: ascoltala e conferma che è davvero quella persona. Solo allora il nome va nella trascrizione e la voce entra nella libreria `voci`, così le prossime volte viene riconosciuta.

Accanto al file trovi:

- `<nome file> - trascrizione.txt`: il testo da leggere;
- `<nome file> - trascrizione.json`: gli stessi dati per i programmi, con la sicurezza del riconoscimento di ogni voce.

Con la GPU un'ora di registrazione richiede pochi minuti. Sulla CPU può volerci più della durata della registrazione. Si fa una trascrizione alla volta: se ne è già in corso una, aspetta che finisca.

**Dare i nomi più tardi.** Trascina il file `<nome file> - trascrizione.json` sopra `Trascrivi.bat`: ti fa le stesse domande sui nomi, senza trascrivere di nuovo. Se nel frattempo hai spostato la registrazione, ti chiede di trascinarla nella finestra.

## Con Claude Code o Codex

Dopo l'installazione puoi chiedere al tuo agente, per esempio: "trascrivi la registrazione che ho appena salvato con OBS" e poi "chi è Persona 2?". L'agente usa lo stesso trascrittore sul tuo PC, e la trascrizione non esce dal PC, a meno che l'agente non la legga per risponderti.

Un agente può proporti un nome, ma lo usa solo dopo che l'hai confermato, e prima ti fa ascoltare la voce.

## Voci da riconoscere

Il programma riconosce solo le persone che hanno una cartella dentro `voci`, accanto a `Trascrivi.bat`.

1. Crea la cartella `voci\Nome Cognome`. Quel nome è quello che comparirà nel testo.
2. Mettici almeno **3 clip da 10–60 secondi** in cui parla solo quella persona: per esempio note vocali del telefono, oppure pezzi di altre registrazioni. Puoi partire dai file che ti ha mandato chi ti ha dato il trascrittore.
3. Vanno bene wav, mp3, m4a, flac, ogg, aac e opus. I video no.
4. Clip fatte in posti e con microfoni diversi (una stanza, una call, il telefono) aiutano il riconoscimento.

Se il programma non è abbastanza sicuro, preferisce scrivere "Persona N" piuttosto che un nome sbagliato.

Per non riconoscere più una persona, cancella la sua cartella dentro `voci`.

### Le voci a cui dai un nome

Quando dai un nome a una voce, le sue clip finiscono in `voci\Nome Cognome\registrazioni`. Il nome del file dice da quale registrazione vengono e da che minuto.

All'inizio il programma è in **periodo di prova**: tiene tutte le clip, anche quelle che secondo lui sono brutte. Ascoltale e cancella quelle con altre voci, risate o rumori. Dopo 10 voci con nome fai doppio clic su `Verifica.bat`. Se tra le clip che hai cancellato non ce n'è nessuna che il programma avrebbe tenuto, ti chiede se le hai ascoltate tutte e, se rispondi di sì, da lì in poi scarta da solo le peggiori. Altrimenti ti elenca quelle clip: in quel caso avvisa chi ti ha dato il trascrittore.

`Verifica.bat` controlla anche quanto bene vengono riconosciute le voci a cui hai dato un nome, e ti dice se conviene cambiare la soglia: in quel caso ti mostra la riga da scrivere in `trascrittore.ini`. Non la cambia mai da solo. Usalo ogni tanto, dopo aver dato qualche nome.

## Impostazioni

Le impostazioni stanno in `trascrittore.ini`, accanto a `Trascrivi.bat`: aprilo con Blocco note. Il file contiene solo quello che hai cambiato tu, ognuno sotto la sua sezione, per esempio:

```
[whisper]
batch_size = 4
```

Tutto il resto viene dal trascrittore, e ogni aggiornamento porta i valori nuovi. Le righe che iniziano con `;` sono solo note: la riga della sezione, come `[whisper]`, va scritta senza `;` davanti. Se scrivi una riga che il trascrittore non capisce, ti dice quale correggere.

## Aggiornamenti

Quando esce una versione nuova, chi ti ha dato il trascrittore ti avvisa e ti dice quali file riscaricare: di solito solo `trascrittore.tar`, a volte tutti. Mettili nella stessa cartella e fai di nuovo doppio clic su `Installa.bat`, che sostituisce la versione vecchia. La cartella `voci` e il tuo `trascrittore.ini` restano come sono.

## Se qualcosa non va

| Messaggio | Cosa fare |
|---|---|
| Docker Desktop non è installato | Installalo come spiegato in "Installazione" e riprova. |
| Docker Desktop non è avviato | Apri Docker Desktop, aspetta che sia pronto e riprova. |
| Il trascrittore non è installato | Esegui `Installa.bat`. |
| Un'altra trascrizione è in corso su questo PC | Aspetta che finisca e riprova. |
| Non riesco a leggere la registrazione | Controlla che sia un file audio o video e che sia sul PC: se è "solo online" su OneDrive o Google Drive, scaricalo prima. |
| ATTENZIONE: nessuna GPU disponibile, elaboro su CPU | Funziona lo stesso, ma lento. Aggiorna il driver NVIDIA e riavvia Docker Desktop. |
| Memoria della GPU esaurita | Apri `trascrittore.ini` con Blocco note e aggiungi in fondo le due righe `[whisper]` e `batch_size = 4`, come nell'esempio di "Impostazioni". Salva e riprova. Se non basta, metti 2 al posto di 4. |
| trascrittore.ini, riga … | Correggi o cancella quella riga di `trascrittore.ini` e riprova. |

Per qualsiasi altro errore manda una foto della finestra a chi ti ha dato il trascrittore.
