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

Comandi per la V4, da PC con la scheda via USB. I pin `rxd` e `txd` sono quelli della V4 collegati alla XIAO; scegli due GPIO liberi dal pinout della V4:

```
meshtastic --set device.role CLIENT_MUTE
meshtastic --set serial.enabled true --set serial.mode TEXTMSG --set serial.echo false ^
           --set serial.baud BAUD_38400 --set serial.rxd <GPIO_RX_V4> --set serial.txd <GPIO_TX_V4>
```

Collegamenti: TX XIAO → RX V4, RX XIAO ← TX V4, GND in comune. Entrambe le schede lavorano a 3,3 V.

**Prova da fare subito, prima di scrivere il firmware.** Collega la V4 a un adattatore USB-seriale sul PC e apri un terminale a 38400 baud.
1. Scrivi una riga, ad esempio `BS1 H TF01 90 4000 0`: il gateway sul Pi deve riceverla e rispondere.
2. La risposta deve comparire sul terminale come `BASE: BS1 T TF01 1793...`.

Se la risposta non compare, la ricezione su seriale in TEXTMSG non funziona con questo firmware. In quel caso si passa alla modalità `PROTO`, con la libreria Meshtastic per Arduino: il protocollo resta identico.

## 2. Messaggi

Testo ASCII, campi separati da spazi, **massimo 200 caratteri per messaggio**. Ora sempre in **ora locale italiana** (CET/CEST) nel formato `AAAAMMGGhhmmss`.

### Dal campo alla base

**H, risveglio.** Va inviato come primo messaggio a ogni risveglio della V4.
```
BS1 H <stazione> <batteria%> <batteria_mV> <rilevamenti_in_coda>
BS1 H TF01 87 3990 12
```

**D, rilevamenti.** Più rilevamenti per messaggio, separati da `;`.
```
BS1 D <stazione> <seq> <batteria%> <rec>;<rec>;...
rec = <AAAAMMGGhhmmss>,<CODICE_SPECIE>,<confidenza%>,<temperatura×10>,<pressione×10>

BS1 D TF01 41 87 20261102064512,ERIRUB,91,124,10154;20261102065003,CETCET,88,125,10154
```
- `seq` è il numero del messaggio, crescente da 1 a 65535 e poi di nuovo da 1. Ogni rilevamento in coda tiene il `seq` del messaggio in cui è stato spedito.
- `CODICE_SPECIE` è un codice di 6 lettere preso da `raspberry/specie.csv`. Le etichette del modello AI vanno mappate su questi codici.
- Temperatura e pressione si moltiplicano per 10 e si scrivono come interi (`12.4 °C` → `124`, `1015.4 hPa` → `10154`). Se manca il sensore, lascia il campo vuoto: `...,91,,`.
- Ogni rilevamento occupa circa 37 caratteri, quindi ci stanno circa 4 rilevamenti per messaggio.

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
- In riserva si scaricano via Bluetooth o Wi-Fi, si copiano sul PC in `da_importare\` e poi si cancellano dalla XIAO.

## 6. Orari di ascolto

| Periodo | XIAO spenta (deep sleep) |
|---|---|
| Ottobre - febbraio | dalle 23:00 alle 05:00 |
| Marzo, luglio - settembre | dalle 23:00 fino a **90 minuti prima dell'alba** |
| Aprile - giugno | mai (usignoli, cannareccioni, rapaci notturni, migratori) |

La XIAO calcola l'alba dalla data e dalle coordinate della stazione: 41.9597 N, 12.0522 E.

## 7. Alimentazione

### Fase di test: V4 sempre accesa

La V4 resta accesa e carica le batterie dal pannello (ingresso solare 4,7-6 V, dopo il riduttore 18 → 5 V). La configurazione dei nodi è gestita da te. Il Bluetooth resta acceso, per la manutenzione da sotto il palo.

- La modalità risparmio di Meshtastic (`power.is_power_saving`) mette la scheda in sleep. Provala solo dopo aver verificato che il collegamento seriale con la XIAO funzioni, e ricontrolla che continui a funzionare anche con il risparmio attivo.
- Durante il test misura con un tester USB, tra riduttore e Heltec, tre valori: il consumo della V4, quello della XIAO e la corrente di carica nelle ore di sole. Con quei numeri si decide la soluzione definitiva.

### Da valutare dopo i test

Se la XIAO **spegne** la V4 tra un invio e l'altro (con un MOSFET o un load switch sulla linea di alimentazione), anche il caricatore solare integrato della V4 si ferma. Due possibilità:
- **(consigliata)** un modulo di carica solare MPPT a parte (es. CN3791), collegato al pannello da 18 V, che carica le due 18650 in parallelo e alimenta XIAO e V4. La V4 si accende e si spegne dalla XIAO.
- la V4 resta sempre accesa e fa da caricatore. In questo caso non si può spegnere: si attiva il risparmio energetico di Meshtastic e si mette in conto il suo consumo continuo nel bilancio energetico.
