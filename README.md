# birdsongtech

Monitoraggio bioacustico automatico degli uccelli nel **Monumento Naturale Palude di Torre Flavia** (Ladispoli, Roma), con un archivio pubblico dove chiunque può cercare, ascoltare e vedere in 3D i canti registrati.

- Sito: [www.birdsongtech.it](https://www.birdsongtech.it)
- Contatti: info@birdsongtech.it

## Come funziona

1. **Ascolto**: un microfono collegato a una scheda XIAO ESP32-S3 Sense registra di continuo.
2. **Riconoscimento**: il modello AI a bordo salva il `.wav` quando riconosce una specie con una confidenza sopra la soglia impostata (85-90%).
3. **Trasmissione**: due volte al giorno una scheda Heltec V4, che gestisce anche la ricarica dal pannello solare, invia il log dei riconoscimenti via LoRa (Meshtastic, canale privato).
4. **Raccolta**: alla base una scheda Heltec V3 riceve il log e lo passa via seriale a un Raspberry Pi 3.
5. **Scarico**: in riserva si scaricano i `.wav` dalla XIAO via Bluetooth o Wi-Fi e se ne libera la memoria.
6. **Pubblicazione**: sul PC di casa `aggiorna_birdsong.bat` fa tutto il resto.

## Dove sta cosa

| Cosa | Dove |
|---|---|
| Pagine del sito, logo, foto delle specie, librerie | GitHub (GitHub Pages) |
| Elenco dei rilevamenti (`data/`), database, log | GitHub |
| File audio `.wav` | **Internet Archive** (archive.org), un item al mese: `birdsongtech-torreflavia-AAAA-MM` |
| Copia locale degli audio | sul PC, cartella `audio/` (esclusa da git) |

## File del progetto

| File | A cosa serve |
|---|---|
| `index.html` | Home: ultimo canto, come funziona, mappa della stazione, specie, ringraziamenti |
| `archivio.html` | Ricerca per specie, date e affidabilità |
| `player.html` | Visualizzatore 3D del canto (`player.html?id=...`, `?demo=1` per il canto di prova) |
| `schema.html` | Schema dei flussi di dati |
| `statistiche.html` | Grafici mensili: canti validi al giorno, temperatura e punto di rugiada, umidità, pressione, batteria |
| `pubblica.py` | Log CSV → database → audio su archive.org → dati del sito |
| `aggiorna_birdsong.bat` | Il comando unico da lanciare con doppio clic |
| `foto_specie.py` | Scarica da Wikimedia Commons una foto per specie (4:3, 800×600) con autore e licenza, in `assets/specie/` |
| `prova_sito_locale.bat` | Apre il sito sul PC con gli audio locali, senza pubblicare nulla |
| `assets/` | Logo, favicon, foto delle specie, stile e script comuni, librerie (three.js) |
| `data/rilevamenti.js` / `.json`, `data/statistiche.js` | Dati letti dal sito (generati, da non modificare a mano) |
| `telemetria.csv` | Batteria, temperatura, pressione e umidità inviate dalla stazione a ogni risveglio (scaricato dal Raspberry) |
| `canto.wav` | Canto dimostrativo per il visualizzatore |
| `ricerca.html`, `apri_3d.html` | Rimandano alle nuove pagine, così i vecchi link funzionano ancora |
| `raspberry/` | Gateway LoRa della stazione base e tabelle delle specie e della stazione: vedi [raspberry/LEGGIMI.md](raspberry/LEGGIMI.md) |
| `docs/ISTRUZIONI.md` | [Istruzioni operative](docs/ISTRUZIONI.md): uso quotidiano, configurazione, foto, dominio |
| `docs/PROTOCOLLO_LORA.md` | [Protocollo BS1](docs/PROTOCOLLO_LORA.md) tra stazione in campo e base: formato dei messaggi, orari, nomi dei file, configurazione Meshtastic |

## Crediti

- Il visualizzatore 3D è basato su [Bird Song Visualization in 3D](https://github.com/venomez-viper/Bird-Song-Visualization-in-3D-) di venomez-viper, adattato per birdsongtech.
- Ispirazione che ha ampliato il progetto: [Visuals from bird songs](https://www.lucioarese.net/portfolio_page/visual-birds/) di Lucio Arese.
- Foto delle specie: autori vari, Wikimedia Commons, licenze indicate sotto ogni foto.
- Elenco delle specie: Battisti C., Cento M., Fraticelli F., Hueting S., Muratore S. (2021), checklist dei vertebrati della ZPS Palude di Torre Flavia.
- [three.js](https://threejs.org) (licenza MIT), [Leaflet](https://leafletjs.com) (BSD-2), mappe © contributori di OpenStreetMap.
- Area protetta gestita dalla Città Metropolitana di Roma Capitale, che ringraziamo.
