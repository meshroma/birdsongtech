# Punto della situazione - 2 novembre 2026

Da leggere per primo quando si riprende il lavoro. Dettagli in `README.md`, `docs/ISTRUZIONI.md`, `docs/PROTOCOLLO_LORA.md` e `raspberry/LEGGIMI.md`.

## Fatto

**Sito** (GitHub Pages, in futuro www.birdsongtech.it)
- Tre pagine con il logo birdsongtech, colori grafite e arancio, sfondo grigio uniforme:
  - **Home**: ultimo canto con foto, i 5 passaggi "Dal canneto al tuo schermo", mappa OpenStreetMap senza chiave, specie ascoltate, ringraziamenti alla Città Metropolitana di Roma Capitale.
  - **Archivio**: ricerca per specie, date, affidabilità e "solo con audio".
  - **Visualizzatore 3D** (`player.html`): motore di venomez-viper adattato, punti e linee più luminosi, logo, scheda con foto, presenza a Torre Flavia e dati del rilevamento (niente microfono: la registrazione dei visitatori non è prevista).
- Stazione unica, chiamata ovunque "Monumento Naturale Palude di Torre Flavia". Coordinate: 41.95970 N, 12.05215 E.
- **116 specie** in `raspberry/specie.csv`: quelle presenti regolarmente secondo la checklist Battisti et al. 2021. Ognuna ha una **foto** da Wikimedia Commons (800×600) con autore e licenza, in `assets/specie/`.
- Contatti: info@birdsongtech.it.

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
- Scarico dei file e aggiornamenti firmware **da terra**: il Bluetooth accende su richiesta il Wi-Fi della XIAO per 20 minuti (scatola in cima al palo, da tirare giù solo per emergenze). Collegamenti in `docs/schema_collegamenti.png`.
- **Fase di test: V4 sempre accesa.** Alimentazione:
  - pannello 18 V 10 W → modulo MPPT DIY_CHARGER V12.0 (ponticello 18V);
  - 2 × EVE 18650 in parallelo, con INA219 sul + della batteria;
  - V4 dal connettore batteria.
  
  Bilancio in attivo tutto l'anno (`docs/BILANCIO_ENERGETICO.md`).

## Da fare

**A ogni sessione:** aggiornare insieme sito, `docs` (con `docs/ORE_DI_LAVORO.md` e le immagini in `docs/sorgenti/`) e la presentazione in `presentazione/`.

0. **Chiave SSH dal PC al Raspberry** (raspberry/LEGGIMI.md): serve per la copia di sicurezza automatica degli audio sulla SD del Pi e toglie le richieste di password.
0. Creare su Aruba l'alias **riconoscimento-specie@birdsongtech.it**: lo usa il pulsante «Richiedi file CSV per valutazione» dell'archivio. Le richieste si gestiscono come spiegato in `docs/VERIFICHE.md` (`crea_lotto.bat`, cartella `verifiche\`).

1. Copiare sul Raspberry `raspberry/gateway.py` (legge i nuovi campi del messaggio H: minuti di ascolto e versione del modello) e le tabelle aggiornate:
   `scp raspberry\gateway.py raspberry\stazioni.csv raspberry\specie.csv pi@192.168.1.100:/home/pi/`, poi `ssh -t pi@192.168.1.100 "sudo systemctl restart birdsong"`.
2. Account su archive.org, poi `pip install internetarchive` e `ia configure`. La prima volta conviene provare con `ARCHIVE_PROVA = True` in `pubblica.py`.
3. **Quando arriva la XIAO:**
   - prova della seriale TEXTMSG tra V4 e PC (sezione 1 di `docs/PROTOCOLLO_LORA.md`);
   - prova dal telefono dei messaggi `BS1 H` e `BS1 D`, poi cancellare il rilevamento di prova sul Pi;
   - firmware della XIAO:
     - ascolto a **32 kHz** (modello addestrato a 32 kHz), riconoscimento, coda, protocollo BS1, orari, nomi dei file;
     - scarico via Wi-Fi su richiesta e aggiornamento OTA;
     - **modello a più etichette** (multi-label) e classificazione anche durante i 16 s: più specie nello stesso file, con l'ottavo campo del record `D`;
     - **campione di controllo**: 1 rilevamento su 10 tra il 50% e l'85%, con il campo `c`;
     - **minuti di ascolto** (oggi/ieri) e **versione del modello** nel messaggio H (vedi `docs/PROTOCOLLO_LORA.md`);
   - allineare `specie.csv` alle etichette del modello AI.
4. Durante il test, l'INA219 misura consumi e carica reali. Dopo una settimana di dati:
   - aggiornare il bilancio energetico;
   - valutare 4 batterie invece di 2;
   - valutare il DS3231 per l'ora.
5. Dominio www.birdsongtech.it: **registrato**. Ora funziona con un reindirizzamento nascosto di Aruba. Da sostituire con il collegamento diretto a GitHub Pages:
   - in Aruba: disattivare il reindirizzamento e creare il record CNAME `www` → `meshroma.github.io`; per l'indirizzo senza www, 4 record A verso GitHub;
   - su GitHub: Settings → Pages → Custom domain `www.birdsongtech.it`, poi Enforce HTTPS;
   - sul PC: Pull da GitHub Desktop prima del successivo `aggiorna_birdsong.bat`.
   Con il reindirizzamento nascosto l'indirizzo resta sempre la home, quindi i link non si possono condividere; il sito potrebbe vedersi rimpicciolito su telefono.
6. Google Analytics: il codice è solo sulla Home. Chiedere all'ente se servono il banner per il consenso ai cookie e la pagina dell'informativa privacy; in quel caso Analytics va attivato solo dopo il consenso.
7. Chiedere a venomez-viper il permesso per il visualizzatore 3D: il progetto originale non ha una licenza dichiarata.
