# Protocollo BS1: stazione in campo ↔ stazione base

Specifica per il firmware della **XIAO ESP32-S3 Sense** e per la configurazione delle due **Heltec** (Meshtastic 2.7.26).
Il lato base è già implementato in `raspberry/gateway.py`.

```
 XIAO ESP32-S3 ──UART──> Heltec V4 ~~LoRa / Meshtastic~~> (nodi della rete) ~~> Heltec V3 ──USB──> Raspberry Pi
 (ascolto + AI)          CLIENT_MUTE                                          CLIENT_BASE        gateway.py
        <──────────────────────────── conferme + ora esatta <─────────────────────────────────────
```

## 1. Configurazione Meshtastic

| | Heltec V4 (campo, `TF01`) | Heltec V3 (base) |
|---|---|---|
| Ruolo | `CLIENT_MUTE` | `CLIENT_BASE` |
| Canale primario (indice 0) | `birdsongtech`, PSK privata | `birdsongtech`, stessa PSK |
| Regione / preset radio | gli stessi della rete Meshtastic locale (es. `EU_868`, `LONG_FAST`) | uguali |
| Preferiti | la V3 | la V4 (**necessario** perché CLIENT_BASE le dia priorità) |
| Modulo seriale | attivo, `TEXTMSG` (vedi sotto) | non serve (il Pi usa la USB) |
| MQTT | disattivato | uplink disattivato sul canale `birdsongtech` |
| Short name | es. `TF01` | es. `BASE` |

- Il canale `birdsongtech` deve essere il **primario**, perché in modalità TEXTMSG il modulo seriale trasmette sul canale predefinito.
- Regione e preset devono coincidere con quelli dei nodi della rete che stanno tra le due stazioni, altrimenti i nodi intermedi non ripetono i pacchetti. Se cambi il canale primario, controlla anche che lo slot di frequenza (`lora.channel_num`) resti quello della rete locale.

Comandi per la V4, da PC con la scheda via USB. I pin `rxd` e `txd` sono quelli della V4 collegati alla XIAO: GPIO47 (RX, connettore J2 pin 13) e GPIO48 (TX, J2 pin 14), liberi secondo il datasheet Heltec V4.3.1. Schema completo in `docs/schema_collegamenti.png`.

```
meshtastic --set device.role CLIENT_MUTE
meshtastic --set serial.enabled true --set serial.mode TEXTMSG --set serial.echo false ^
           --set serial.baud BAUD_38400 --set serial.rxd 47 --set serial.txd 48
```

Collegamenti: XIAO D6 (TX, GPIO43) → V4 GPIO47 (RX); XIAO D7 (RX, GPIO44) ← V4 GPIO48 (TX); GND in comune. Entrambe le schede lavorano a 3,3 V. La XIAO è alimentata dal pin 3V3 della V4 (J3 pin 2-3, max 500 mA).

**Prova da fare subito, prima di scrivere il firmware: la XIAO come ponte.** La prova simula i messaggi della XIAO, quindi il PC deve parlare con i **pin GPIO47/48** della V4, non con la sua presa USB-C. Dalla USB-C della V4 passano solo il protocollo binario delle app Meshtastic e i log, quindi serve solo per configurarla. Il ponte lo fa la XIAO stessa: non serve comprare un adattatore USB-seriale, e in più si prova già il cablaggio definitivo.

1. **Carica lo sketch** `firmware/ponte_seriale/ponte_seriale.ino` sulla XIAO con Arduino IDE.
   - Scheda: *XIAO_ESP32S3*.
   - Menu Strumenti: *USB CDC On Boot: Enabled*.
   
   Lo sketch copia tutto quello che arriva dalla USB della XIAO sui pin D6/D7, e viceversa.
2. **Collega solo tre fili**, come nello schema `docs/schema_collegamenti.png`:
   - XIAO D6 (TX) → V4 GPIO47 (RX)
   - XIAO D7 (RX) ← V4 GPIO48 (TX)
   - GND ↔ GND
   
   **Durante la prova non collegare il filo 3V3**: la XIAO prende corrente dalla USB del PC e la V4 dalla sua USB-C o dalla batteria. Con il 3V3 collegato ci sarebbero due alimentazioni in parallelo.
3. **Apri il monitor seriale** di Arduino IDE sulla porta della XIAO, a 115200 baud (la velocità sulla USB non conta), con fine riga *A capo (NL)*. Va bene anche PuTTY.
4. **Scrivi una riga**, ad esempio `BS1 H TF01 90 4000 0`: il gateway sul Pi deve riceverla e rispondere.
5. **Controlla la risposta**: deve comparire nel monitor come `BASE: BS1 T TF01 1793...`.

Se la risposta non compare, la ricezione su seriale in TEXTMSG non funziona con questo firmware. In quel caso si passa alla modalità `PROTO`, con la libreria Meshtastic per Arduino: il protocollo resta identico.

## 2. Messaggi

Testo ASCII, campi separati da spazi, **massimo 200 caratteri per messaggio**. Ora sempre in **ora locale italiana** (CET/CEST) nel formato `AAAAMMGGhhmmss`.

### Dal campo alla base

**H, risveglio.** Va inviato come primo messaggio a ogni risveglio della V4. Porta anche la telemetria della scheda ambientale (temperatura, pressione, umidità): così le statistiche hanno almeno due misure al giorno anche nei giorni senza canti.
```
BS1 H <stazione> <batteria%> <batteria_mV> <in_coda> <temperatura×10> <pressione×10> <umidità%> <ascolto_oggi_min> <ascolto_ieri_min> <modello>
BS1 H TF01 87 3990 12 124 10154 78 412 1080 m1.0
```
**I campi del messaggio H:**
- `ascolto_oggi_min`: minuti in cui la XIAO ha davvero ascoltato da mezzanotte (ora locale) a ora. Si escludono le ore di spegnimento programmato, lo scarico WiFi e il sonno per batteria bassa.
- `ascolto_ieri_min`: totale del giorno prima. Serve perché l'ultimo `H` della giornata parte alle 20:30, prima della fine dell'ascolto.
- `modello`: versione del modello di riconoscimento caricato sulla XIAO, senza spazi (per esempio `m1.0`). Ogni rilevamento viene registrato con la versione attiva in quel momento. Quando si aggiorna il modello si cambia la versione: così i dati di modelli diversi restano distinguibili.

**Campi mancanti.** I campi dal sesto in poi sono facoltativi, ma vanno in ordine. Un valore mancante in mezzo si scrive `-`, per esempio senza sensori: `BS1 H TF01 87 3990 12 - - - 412 1080 m1.0`. Un `H` con solo i primi quattro campi resta valido.

**D, rilevamenti.** Più rilevamenti per messaggio, separati da `;`.
```
BS1 D <stazione> <seq> <batteria%> <rec>;<rec>;...
rec = <AAAAMMGGhhmmss>,<CODICE_SPECIE>,<confidenza%>,<temperatura×10>,<pressione×10>,<umidità%>[,c]

BS1 D TF01 41 87 20261102064512,ERIRUB,91,124,10154,78;20261102065003,CETCET,88,125,10154,79
```
- `seq` è il numero del messaggio, crescente da 1 a 65535 e poi di nuovo da 1. Ogni rilevamento in coda tiene il `seq` del messaggio in cui è stato spedito.
- `CODICE_SPECIE` è un codice di 6 lettere preso da `raspberry/specie.csv`. Le etichette del modello AI vanno mappate su questi codici.
- Temperatura e pressione si moltiplicano per 10 e si scrivono come interi (`12.4 °C` → `124`, `1015.4 hPa` → `10154`). L'umidità relativa è un intero in percentuale (`78`). Se manca un sensore, lascia il campo vuoto: `...,91,,,`.
- Il punto di rugiada non si trasmette: lo calcola `pubblica.py` da temperatura e umidità.
- Il settimo campo `c`, facoltativo, indica un **campione di controllo**: un rilevamento sotto la soglia di salvataggio, conservato a caso per valutare il modello. Vedi la sezione 5.
- Ogni rilevamento occupa circa 40 caratteri, quindi ci stanno circa 4 rilevamenti per messaggio.

### Dalla base al campo

Alla XIAO le risposte arrivano dalla seriale come `<ShortName base>: <testo>`.

**T, ora esatta.** È la risposta a H.
```
BS1 T <stazione> <ora_unix_UTC>
```

**A, conferma.** Arriva circa 8 secondi dopo l'ultimo D ricevuto e contiene anche l'ora.
```
BS1 A <stazione> <ora_unix_UTC> <seq>,<seq>,...
BS1 A TF01 1793628826 41,42
```
La XIAO toglie dalla coda i rilevamenti con quei `seq`. Il Pi scarta comunque i doppioni, quindi ritrasmettere un rilevamento già arrivato non fa danni.

## 3. Ciclo di trasmissione (2 volte al giorno)

Orari suggeriti: **12:30** e **20:30**, lontani dal coro dell'alba.

1. **Fase di test (V4 sempre accesa):** la XIAO passa subito al punto 2.
   *Con V4 spenta tra un invio e l'altro (possibile soluzione definitiva):* la XIAO accende la V4 e aspetta **90 s**, il tempo perché la V4 ritrovi la rete.
2. Invia `H` e aspetta `T` per al massimo 60 s.
   - Se `T` arriva: imposta l'orologio.
   - Se non arriva: ritenta `H` una volta. Se fallisce ancora, salta al punto 5.
3. Invia i `D` in coda, **uno ogni 15 s**, al massimo 15 messaggi per risveglio (circa 60 rilevamenti), così occupa poco tempo radio della rete condivisa e resta nei limiti di duty cycle europei.
4. Aspetta `A` per al massimo 120 s dall'ultimo `D`. Rimanda una sola volta i `D` non confermati, poi attende di nuovo.
5. Torna ad ascoltare. Nella soluzione con V4 spenta, prima la spegne. I rilevamenti non confermati restano in coda per il ciclo successivo.

La coda vive nella flash della XIAO (es. LittleFS, file `coda.csv`), così sopravvive a un riavvio.

## 4. Orologio

- La XIAO usa il fuso `CET-1CEST,M3.5.0,M10.5.0/3`, con `setenv("TZ", ...)` e `tzset()`. Imposta l'ora con `settimeofday()` dal valore UTC ricevuto in `T` o `A`.
- **All'accensione** (batteria nuova, reset) la XIAO non conosce l'ora. Prima di cominciare ad ascoltare deve fare subito un ciclo H/T. Finché non ha l'ora non salva registrazioni: con un timestamp sbagliato non potrebbero più essere associate al rilevamento.
- L'orologio interno in deep sleep deriva. La sincronizzazione due volte al giorno basta.

## 5. File audio

- Nome: `<stazione>_<AAAAMMGG>_<hhmmss>.wav`, per esempio `TF01_20261102_064512.wav`. Il timestamp deve essere **identico** a quello del rilevamento nel messaggio `D`: è così che `pubblica.py` associa l'audio al rilevamento.
- Durata massima **16 s**. Formato consigliato: WAV PCM 16 bit mono, 16 kHz, circa 32 KB al secondo, cioè circa 0,5 MB per file.
- I file restano sulla microSD (64 GB, oltre 100.000 file) e si scaricano dal basso, senza smontare la scatola: vedi sotto. Sul PC vanno in `da_importare\`.

### Scarico dal basso (Wi-Fi su richiesta)

La scatola sta in cima al palo e si tira giù solo per emergenze, quindi tutto si fa da terra col telefono.

1. **Di base** il Wi-Fi della XIAO è spento. Resta attivo solo il Bluetooth Low Energy in ascolto, con il nome `TF01-XIAO` e il consumo minimo.
2. **Attivazione:** dal telefono, via BLE, si manda il comando `WIFI ON`, protetto da un codice. In alternativa, più avanti, si può aggiungere il messaggio `BS1 W TF01` dalla base via LoRa.
3. La XIAO **sospende l'ascolto** e accende un punto di accesso Wi-Fi (`birdsongtech-TF01`, con password) per **20 minuti**.
4. Col browser del telefono o del portatile si apre `http://192.168.4.1`, dove si trovano:
   - l'elenco dei file con dimensione e stato;
   - lo scarico del singolo file o di tutti quelli nuovi;
   - lo stato della batteria e lo spazio libero.
5. **Cancellazione:** i file si cancellano dalla microSD solo con un comando esplicito, dopo averli copiati sul PC. Di base si tengono: lo spazio basta per anni.
6. A fine scarico, o allo scadere dei 20 minuti, il Wi-Fi si spegne e l'ascolto riprende.

Velocità indicative: Bluetooth 30-80 KB/s, circa 10-15 s per file; Wi-Fi 1-2 MB/s, meno di 1 s per file. Il Bluetooth serve solo come "interruttore".

Dalla stessa pagina si può caricare un **nuovo firmware (OTA)**, così anche gli aggiornamenti non richiedono di smontare la scatola. Conviene tenere sempre un firmware di riserva funzionante: lo schema di partizioni con due slot OTA dell'ESP32 lo fa in automatico.

### Campione di controllo per valutare il modello

Se la XIAO salvasse solo i rilevamenti sopra la soglia (85 %), non si saprebbe mai cosa il modello scarta né quale soglia conviene. Per questo salva anche **un rilevamento su 10, scelto a caso, tra il 50 % e la soglia**:
- il file `.wav` si registra e si nomina come gli altri;
- nel messaggio `D` il rilevamento porta il campo finale `c`;
- nel sito compare nelle fasce di affidabilità "80-90 %" e "fino all'80 %" del grafico *birdsongtech performance*.

I conteggi di quelle fasce sono quindi **un decimo** di quelli reali. Il sito lo indica sotto il grafico.

Parametri nel firmware: `SOGLIA_SALVA = 0.85`, `SOGLIA_CAMPIONE = 0.50`, `FRAZIONE_CAMPIONE = 0.10`. Se si cambiano, va annotato in questo documento con la data.

## 6. Orari di ascolto

| Periodo | XIAO spenta (deep sleep) |
|---|---|
| Ottobre - febbraio | dalle 23:00 alle 05:00 |
| Marzo, luglio - settembre | dalle 23:00 fino a **90 minuti prima dell'alba** |
| Aprile - giugno | mai (usignoli, cannareccioni, rapaci notturni, migratori) |

La XIAO calcola l'alba dalla data e dalle coordinate della stazione: 41.9597 N, 12.0522 E.

## 7. Alimentazione

Schema completo in `docs/schema_collegamenti.png`, bilancio in `docs/BILANCIO_ENERGETICO.md`.

**Il percorso dell'energia:**
1. **Pannello 18 V 10 W → modulo MPPT DIY_CHARGER V12.0**, con queste impostazioni:
   - ponticello MPPT su **18V**;
   - Sunlight Detect su **OFF**;
   - uscite 5V/12V e USB-C **non usate**.
   
   Il modulo carica le batterie fino a circa 2,4 A, a 4,2 V. Il caricatore della V4, che arriva al massimo a 500 mA, e il convertitore diymore non si usano più.
2. **Morsetti BATTERY del modulo → 2 × EVE 18650 in parallelo**, passando per l'**INA219**:
   - VIN+ verso il modulo e la V4;
   - VIN− verso le batterie.
3. **Connettore batteria (SH1.25) della V4** collegato allo stesso + e alla massa comune. La V4 si alimenta dalle batterie e non dall'uscita 5 V del modulo, che costerebbe circa il 40 % di energia in più.
4. **XIAO** dal pin 3V3 della V4. INA219 e BME280 dal 3V3 della XIAO, sul bus I²C D4/D5: INA219 all'indirizzo 0x40, BME280 a 0x76/0x77.

### Fase di test: V4 sempre accesa

La V4 resta accesa. La configurazione dei nodi è gestita da te. Il Bluetooth resta acceso, per la manutenzione da sotto il palo.

- La modalità risparmio di Meshtastic (`power.is_power_saving`) mette la scheda in sleep. Provala solo dopo aver verificato che il collegamento seriale con la XIAO funzioni, e ricontrolla che continui a funzionare anche con il risparmio attivo.
- La XIAO legge l'INA219 ogni minuto (tensione e corrente) e:
  - mette i valori reali nei campi `batteria%` e `batteria_mV` dei messaggi H e D;
  - registra il bilancio di ogni giornata: Ah entrati, Ah usciti, carica minima e massima.
  
  Dopo una settimana di dati si confermano o si correggono le stime del bilancio energetico.

### Protezione delle batterie

La protezione da scarica del modulo MPPT vale solo per le sue uscite, che non usiamo. La gestisce quindi la XIAO:
- sotto **3,45 V** smette di ascoltare e va in sonno profondo, svegliandosi ogni ora per ricontrollare la tensione;
- riprende sopra **3,70 V**;
- sotto **3,30 V** manda un ultimo `BS1 H` come allarme. Anche Meshtastic spegne la V4 quando la batteria è molto bassa.

### Da valutare dopo i test
- **4 batterie invece di 2**, per circa 5 giorni coperti di fila d'inverno invece di 2-2,5.
- **Meno consumi:** Bluetooth della V4 spento sul campo, schermo OLED spento dopo pochi secondi, XIAO a 160 MHz.
