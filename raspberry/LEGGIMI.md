# Raspberry Pi della stazione base

Raspberry Pi 3 (Debian 13), con la Heltec V3 collegata via USB (`/dev/ttyUSB0`) e il display LCD su `/dev/tty1`.

| File | A cosa serve |
|---|---|
| `gateway.py` | Riceve i messaggi `BS1` dalla stazione in campo, risponde con conferma e ora esatta, scrive `birdsong_log.csv` |
| `display_last.py` | Testo del display LCD: ultima ricezione, nodo, file validi (80% o più) dell'ultima ricezione, batteria della stazione. Driver e servizio del display invariati; la versione precedente è in `originali/` |
| `specie.csv` | Tabella codice → nome italiano → nome scientifico (i codici li usa la XIAO) |
| `stazioni.csv` | Sigla della stazione (es. `TF01`) → nome del nodo, coordinate, quota |
| `birdsong.service`, `birdsong-display.service` | I servizi systemd che fanno partire i due script all'accensione (invariati, **da non toccare**) |
| `originali/` | Le tue versioni precedenti, per riferimento |

Tutti i file stanno nella cartella home del Pi (`/home/pi`), come prima.

## Installazione / aggiornamento

Dal Prompt dei comandi del PC, nella cartella `birdsong-backend`:

```
cd "C:\Users\iz0qp\Desktop\birdsong\birdsong AI\birdsong-backend\raspberry"
scp gateway.py specie.csv stazioni.csv pi@192.168.1.100:/home/pi/
ssh pi@192.168.1.100 "sudo systemctl restart birdsong"

Si aggiornano **solo gli script**: driver LCD, `.bash_profile` e servizi restano come sono.

Per aggiornare anche il testo del display:

```
scp display_last.py pi@192.168.1.100:/home/pi/
ssh -t pi@192.168.1.100 "sudo systemctl restart birdsong-display"
```
Il nuovo gateway scrive il registro grezzo nello stesso formato di prima, quindi il display continua a funzionare.
```

Per controllare che il gateway giri e vedere i messaggi in arrivo:

```
ssh pi@192.168.1.100 "journalctl -u birdsong -n 30 --no-pager"
```

Per seguirli in diretta: `ssh pi@192.168.1.100 "journalctl -u birdsong -f"` (Ctrl+C per uscire).

## Cosa produce

- `/home/pi/birdsong_log.csv`: un rilevamento per riga, nel formato che legge `pubblica.py`, con il nome del file audio atteso (`TF01_20261102_064512.wav`). È il file che scarica `aggiorna_birdsong.bat`.
- `/home/pi/telemetria.csv`: batteria, temperatura, pressione e umidità inviate dalla stazione a ogni risveglio (due volte al giorno). Serve alla pagina Statistiche e anche questo lo scarica `aggiorna_birdsong.bat`.
- `/home/pi/log sistema di ascolto Birdsong Palude Torre Flavia.csv`: registro grezzo di tutti i messaggi di testo ricevuti (come prima).

I doppioni (stesso canto ritrasmesso perché la conferma non era arrivata) vengono scartati.

## Scaricare il log senza password

Così `aggiorna_birdsong.bat` scarica il log senza chiedere la password ogni volta. Va fatto una volta sola, sul PC:

```
ssh-keygen -t ed25519
```
(premi Invio a tutte le domande)
```
type %USERPROFILE%\.ssh\id_ed25519.pub | ssh pi@192.168.1.100 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Da quel momento `ssh` e `scp` verso il Pi non chiedono più la password. Serve anche alla **copia di sicurezza** che `pubblica.py` fa a ogni aggiornamento nella cartella `/home/pi/birdsongtech_backup/` (vedi `docs/ISTRUZIONI.md`, "Copie di sicurezza"). La cartella non interferisce con il gateway e il display.

## Ora esatta

Il gateway manda alla stazione in campo l'ora del Raspberry, che a sua volta la prende da internet (NTP). Il Pi deve quindi restare connesso alla rete di casa. Per verificarlo: `ssh pi@192.168.1.100 "timedatectl"` deve mostrare `System clock synchronized: yes`.

## Nuove specie o stazioni

- Una nuova specie riconosciuta dal modello: aggiungi una riga a `specie.csv`, con un codice di 6 lettere: le prime 3 del genere più le prime 3 della specie, es. `Cettia cetti` → `CETCET`. Poi ricopia il file sul Pi e riavvia il servizio. I codici sconosciuti finiscono comunque nel log, con il codice al posto del nome, e il gateway li segnala.
- Una nuova stazione in campo: aggiungi una riga a `stazioni.csv`.
