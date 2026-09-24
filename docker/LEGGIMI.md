# Trascrittore riunioni (pilota)

Trascini l'audio di una riunione su `Trascrivi.bat` e, accanto all'audio, ottieni il testo con chi ha parlato e quando:

```
[00:12:34] Mario Rossi: allora partiamo dal budget
```

Tutto gira sul tuo PC. Le registrazioni non vengono mandate a nessun servizio esterno.

## Cosa serve

- Windows 10 o 11. Con una scheda NVIDIA è veloce; senza, funziona sulla CPU ma molto più lentamente, e il programma lo scrive chiaramente.
- [Docker Desktop](https://www.docker.com/products/docker-desktop/), installato con le impostazioni predefinite (WSL2).
- Circa 30 GB liberi su disco: Docker occupa circa 20 GB, più i 7 GB di `meeting-transcriber.tar`. Dopo l'installazione puoi recuperare questi 7 GB con tasto destro sul file → OneDrive → "Libera spazio". Non cancellarlo: la cartella è condivisa e sparirebbe anche per gli altri.

## Installazione (una volta sola)

1. Installa Docker Desktop, riavvia il PC e aprilo.
2. Nella cartella condivisa fai doppio clic su `Installa.bat`. Carica il programma (qualche minuto) e ti dice se la GPU funziona.

Quando esce una versione nuova, chi gestisce il pilota avvisa: basta rieseguire `Installa.bat`, che sostituisce quella vecchia.

## Uso

1. Apri Docker Desktop, se non è già aperto.
2. Trascina il file della riunione (m4a, mp3, wav, mp4 di Teams…) sopra `Trascrivi.bat`, un file alla volta.
3. Scrivi quante persone parlano, oppure premi solo Invio se non lo sai.
4. Alla fine, per ogni voce non riconosciuta, ti mostra due frasi di quella persona e ti chiede il nome. Con Invio resta "Persona 1", "Persona 2"… I nomi scritti qui finiscono solo in questa trascrizione.

Accanto all'audio trovi:

- `<nome audio> - trascrizione.txt`: il testo da leggere;
- `<nome audio> - trascrizione.json`: gli stessi dati per i programmi, con la sicurezza del riconoscimento di ogni voce.

Con la GPU un'ora di riunione richiede pochi minuti. Sulla CPU può volerci più della durata dell'audio.

## Farsi riconoscere: la libreria delle voci

Il programma riconosce solo chi ha una cartella in `voci`, dentro la cartella condivisa.

1. Crea la cartella `voci\Nome Cognome`. Quel nome è quello che comparirà nel testo.
2. Mettici almeno **3 registrazioni della tua voce da 10–60 secondi**, in cui parli solo tu: per esempio note vocali del telefono, oppure pezzi di riunioni.
3. Registrazioni fatte in posti e con microfoni diversi (ufficio, call, telefono) aiutano il riconoscimento.

Se il programma non è abbastanza sicuro, preferisce scrivere "Persona N" piuttosto che un nome sbagliato.

**Consenso.** La libreria contiene impronte vocali, che sono dati biometrici. Aggiungi solo la tua voce, e solo dopo aver dato il tuo consenso scritto a chi gestisce il pilota. Per toglierti basta cancellare la tua cartella.

**OneDrive.** Imposta la cartella condivisa su "Mantieni sempre su questo dispositivo" (tasto destro sulla cartella). Le clip rimaste "solo online" non vengono lette.

## Se qualcosa non va

| Messaggio | Cosa fare |
|---|---|
| Docker Desktop non è avviato | Apri Docker Desktop, aspetta che sia pronto e riprova. |
| Il trascrittore non è installato | Esegui `Installa.bat`. |
| Non riesco a leggere l'audio | Controlla che sia un file audio o video. Se è su OneDrive, tasto destro → "Mantieni sempre su questo dispositivo" e riprova. |
| ATTENZIONE: nessuna GPU disponibile, elaboro su CPU | Funziona lo stesso, ma lento. Aggiorna il driver NVIDIA e riavvia Docker Desktop. |
| Memoria della GPU esaurita | In `meeting.ini` (nella cartella condivisa) abbassa `batch_size` a 4 e riprova, poi a 2. |

Per qualsiasi altro errore manda una foto della finestra a chi gestisce il pilota.
