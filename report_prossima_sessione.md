# Punto della situazione - 2 novembre 2026

Da leggere per primo quando si riprende il lavoro. Dettagli in `README.md`, `docs/ISTRUZIONI.md`, `docs/PROTOCOLLO_LORA.md` e `raspberry/LEGGIMI.md`.

## Fatto

**Sito** (GitHub Pages, in futuro www.birdsongtech.it)
- Tre pagine con il logo birdsongtech, colori grafite e arancio, sfondo grigio uniforme:
  - **Home**: ultimo canto con foto, i 5 passaggi "Dal canneto al tuo schermo", mappa OpenStreetMap senza chiave, specie ascoltate, ringraziamenti alla Città Metropolitana di Roma Capitale.
  - **Archivio**: ricerca per specie, date, affidabilità e "solo con audio".
  - **Visualizzatore 3D** (`player.html`): motore di venomez-viper adattato, punti e linee più luminosi, logo, scheda con foto, presenza a Torre Flavia e dati del rilevamento, microfono.
- Stazione unica, chiamata ovunque "Monumento Naturale Palude di Torre Flavia". Coordinate: 41.95970 N, 12.05215 E.
- **116 specie** in `raspberry/specie.csv`: quelle presenti regolarmente secondo la checklist Battisti et al. 2021. Ognuna ha una **foto** da Wikimedia Commons (800×600) con autore e licenza, in `assets/specie/`.
- Contatti: birdsongtech@gmail.com.

**Pubblicazione dati**
- `pubblica.py` legge il log, aggiorna il database, associa i `.wav` messi in `da_importare/`, li carica su Internet Archive e genera `data/rilevamenti.js`.
- `aggiorna_birdsong.bat`: un doppio clic scarica il log dal Raspberry (pi@192.168.1.100), pubblica e fa il push su GitHub.

**Raspberry Pi** (stazione base)
- Nuovo `gateway.py`, installato e funzionante: protocollo BS1, conferme con l'ora esatta, scrittura di `/home/pi/birdsong_log.csv`.
- Display LCD, driver e servizi **non toccati**. Telegram tolto.

**Radio**
- Firmware 2.7.26.
- Heltec V4 in campo: CLIENT_MUTE, antenna esterna su palo da 4 m.
- Heltec V3 alla base: CLIENT_BASE, a 15 m di altezza.
- Canale privato `birdsongtech`, primario. Distanza 2,5 km, con nodi della rete in mezzo.
- Bluetooth della V4 acceso per la manutenzione. La configurazione dei nodi la gestisci tu.

## Decisioni prese

- Audio su **Internet Archive**, un item al mese. Pagine, dati e foto su **GitHub**.
- File audio: `TF01_AAAAMMGG_hhmmss.wav`, al massimo 16 s.
- Due trasmissioni al giorno, con l'ora sincronizzata dal Raspberry tramite i messaggi BS1.
- Ascolto della XIAO:
  - ottobre-febbraio: spenta dalle 23 alle 5;
  - marzo e luglio-settembre: spenta dalle 23 fino a 90 minuti prima dell'alba;
  - aprile-giugno: sempre accesa.
- **Fase di test: V4 sempre accesa**, che fa anche da caricatore. Alimentazione: pannello 18 V 10 W con riduttore a 5 V, 2 × EVE 18650 in parallelo.

## Da fare

1. Copiare sul Raspberry le tabelle aggiornate:
   `scp raspberry\stazioni.csv raspberry\specie.csv pi@192.168.1.100:/home/pi/`, poi `ssh -t pi@192.168.1.100 "sudo systemctl restart birdsong"`.
2. Account su archive.org, poi `pip install internetarchive` e `ia configure`. La prima volta conviene provare con `ARCHIVE_PROVA = True` in `pubblica.py`.
3. **Quando arriva la XIAO:**
   - prova della seriale TEXTMSG tra V4 e PC (sezione 1 di `docs/PROTOCOLLO_LORA.md`);
   - prova dal telefono dei messaggi `BS1 H` e `BS1 D`, poi cancellare il rilevamento di prova sul Pi;
   - firmware della XIAO: ascolto, riconoscimento, coda, protocollo BS1, orari, nomi dei file;
   - allineare `specie.csv` alle etichette del modello AI.
4. Durante il test, misurare il consumo di V4 e XIAO e la corrente di carica. Poi decidere se tenere la V4 sempre accesa o usare un modulo MPPT separato.
5. Dominio www.birdsongtech.it: registrarlo, poi record CNAME `www` → `meshroma.github.io`, impostazioni Pages, HTTPS.
6. Chiedere a venomez-viper il permesso per il visualizzatore 3D: il progetto originale non ha una licenza dichiarata.
