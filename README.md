# birdsongtech

Monitoraggio bioacustico automatico degli uccelli nel **Monumento Naturale Palude di Torre Flavia** (Ladispoli, Roma), con un archivio pubblico dove chiunque può cercare, ascoltare e vedere in 3D i canti registrati.

- Sito: https://meshroma.github.io/birdsongtech/ (in futuro **www.birdsongtech.it**)
- Contatti: birdsongtech@gmail.com

## Come funziona

1. **Ascolto**: un microfono collegato a una scheda XIAO ESP32-S3 Sense registra di continuo.
2. **Riconoscimento**: il modello AI a bordo salva il `.wav` quando riconosce una specie con una confidenza sopra la soglia impostata (85-90%).
3. **Trasmissione**: due volte al giorno una Heltec V4, che gestisce anche la ricarica dal pannello solare, invia il log dei riconoscimenti via LoRa (Meshtastic, canale privato), poi torna a dormire.
4. **Raccolta**: alla base una Heltec V3 riceve il log e lo passa via seriale a un Raspberry Pi 3.
5. **Scarico**: in riserva si scaricano i `.wav` dalla XIAO via Bluetooth o Wi-Fi e se ne libera la memoria.
6. **Pubblicazione**: sul PC di casa `aggiorna_birdsong.bat` fa tutto il resto.

## Dove sta cosa

| Cosa | Dove |
|---|---|
| Pagine del sito, logo, sfondo, librerie | GitHub (GitHub Pages) |
| Elenco dei rilevamenti (`data/`), database, log | GitHub |
| File audio `.wav` | **Internet Archive** (archive.org), un item al mese: `birdsongtech-torreflavia-AAAA-MM` |
| Copia locale degli audio | sul PC, cartella `audio/` (esclusa da git) |

## File del progetto

| File | A cosa serve |
|---|---|
| `index.html` | Home: ultimo canto, come funziona, mappa delle stazioni, specie |
| `archivio.html` | Ricerca per specie, date, stazione e affidabilità |
| `player.html` | Visualizzatore 3D del canto (`player.html?id=...`, `?demo=1` per il canto di prova) |
| `pubblica.py` | Log CSV → database → audio su archive.org → dati del sito |
| `aggiorna_birdsong.bat` | Il comando unico da lanciare con doppio clic |
| `prova_sito_locale.bat` | Apre il sito sul PC con gli audio locali, senza pubblicare nulla |
| `assets/` | Logo, favicon, sfondo, stile e script comuni, librerie (three.js) |
| `data/rilevamenti.js` / `.json` | Dati letti dal sito (generati, da non modificare a mano) |
| `canto.wav` | Canto dimostrativo per il visualizzatore |
| `ricerca.html`, `apri_3d.html` | Rimandano alle nuove pagine, così i vecchi link funzionano ancora |
| `raspberry/` | Gateway LoRa della stazione base e tabelle di specie e stazioni: vedi [raspberry/LEGGIMI.md](raspberry/LEGGIMI.md) |
| `docs/PROTOCOLLO_LORA.md` | [Protocollo BS1](docs/PROTOCOLLO_LORA.md) tra stazione in campo e base: formato dei messaggi, orari, nomi dei file, configurazione Meshtastic |

## Uso quotidiano

1. Se ci sono nuovi `.wav` scaricati dalla XIAO, copiali nella cartella `da_importare\`.
2. Doppio clic su **`aggiorna_birdsong.bat`**.

Lo script:
- scarica il log dal Raspberry, se configurato;
- aggiunge i rilevamenti nuovi al database;
- associa ogni `.wav` al suo rilevamento;
- carica i `.wav` su Internet Archive;
- rigenera i dati del sito;
- fa commit e push su GitHub.

I rilevamenti arrivati via LoRa ma ancora senza audio compaiono nell'archivio come **"Audio in arrivo"**. Diventano ascoltabili dopo lo scarico in riserva e il successivo aggiornamento.

### Nomi dei file audio

`pubblica.py` associa un `.wav` al rilevamento in uno di questi due modi:
- se il CSV ha una colonna **`file_audio`** con il nome esatto del file (consigliato), usa quella;
- altrimenti cerca il **timestamp** nel nome del file. Formati accettati: `20261030_102100`, `20261030-102100`, `2026-10-30_10-21-00`, `2026-10-30T10-21-00`, `20261030102100`. Se due stazioni registrano nello stesso istante, mettete anche il nome del nodo nel file (es. `TORRE_FLAVIA_02_20261030_140215.wav`).

I file che non corrispondono a nessun rilevamento restano in `da_importare\` e lo script li elenca.

## Configurazione (una volta sola)

**Python** 3.9 o superiore.

**Internet Archive**
1. Crea un account gratuito su https://archive.org
2. Apri il prompt dei comandi ed esegui:
   ```
   pip install internetarchive
   ia configure
   ```
   inserendo email e password di archive.org.
3. In `pubblica.py` puoi cambiare:
   - `LICENZA` (predefinita: CC BY-NC-SA 4.0);
   - `ARCHIVE_PREFISSO`;
   - `ARCHIVE_PROVA = True`, per fare prove in una collezione che archive.org cancella dopo 30 giorni.

Archive.org può impiegare qualche minuto a rendere ascoltabile un file appena caricato.

**Raspberry Pi**: `aggiorna_birdsong.bat` scarica il log da `pi@192.168.1.100:/home/pi/birdsong_log.csv` (modificabile in cima al file). Per non dover scrivere la password ogni volta, vedi [raspberry/LEGGIMI.md](raspberry/LEGGIMI.md).

## Dominio www.birdsongtech.it

Quando il dominio è registrato:
1. dal pannello del registrar crea un record **CNAME**: `www` → `meshroma.github.io`;
2. su GitHub vai in **Settings → Pages → Custom domain**, scrivi `www.birdsongtech.it`, salva (GitHub crea il file `CNAME`), poi attiva **Enforce HTTPS**;
3. facoltativo: dal registrar reindirizza `birdsongtech.it` (senza www) verso `www.birdsongtech.it`.

Non creare il file `CNAME` prima che il dominio esista: il sito su github.io smetterebbe di funzionare.

## Personalizzazioni grafiche

- Logo: `assets/logo.png` (completo) e `assets/logo-simbolo.png` (solo uccello, per le intestazioni).
- Sfondo: `assets/sfondo.svg` (paesaggio low-poly). Per usare una foto, salvala come `assets/sfondo.jpg` e in `assets/sito.css` sostituisci `url('sfondo.svg')` con `url('sfondo.jpg')`.
- Colori e caratteri: variabili in cima ad `assets/sito.css`.

## Crediti

- Il visualizzatore 3D è basato su [Bird Song Visualization in 3D](https://github.com/venomez-viper/Bird-Song-Visualization-in-3D-) di venomez-viper, adattato per birdsongtech.
- [three.js](https://threejs.org) (licenza MIT), [Leaflet](https://leafletjs.com) (BSD-2), mappe © OpenStreetMap e CARTO.
