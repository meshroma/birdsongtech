# Istruzioni operative

Guida per chi gestisce la stazione e il sito. La presentazione del progetto è nel [README](../README.md).

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

**Raspberry Pi**: `aggiorna_birdsong.bat` scarica il log da `pi@192.168.1.100:/home/pi/birdsong_log.csv` (modificabile in cima al file). Per non dover scrivere la password ogni volta, vedi [raspberry/LEGGIMI.md](../raspberry/LEGGIMI.md).

## Foto delle specie

Il player e la Home mostrano una foto di ogni specie, con autore e licenza (obbligatori per le licenze Creative Commons).
Le foto vengono da Wikimedia Commons, a partire dalla voce Wikipedia di ogni specie, e solo con licenze libere.

```
pip install pillow
python foto_specie.py
```

Poi apri `assets/specie/anteprima.html` per controllarle tutte. Per sostituire una foto o spostare il ritaglio, compila `assets/specie/scelte.csv` (istruzioni in cima a `foto_specie.py`) e rilancia lo script con il codice della specie, es. `python foto_specie.py ERIRUB`. Infine pubblica con `aggiorna_birdsong.bat`.

L'elenco delle specie (`raspberry/specie.csv`) contiene le 116 specie presenti regolarmente a Torre Flavia secondo la checklist di Battisti et al. (2021), *Natural History Sciences* 8: 3-28, con il loro stato di presenza.

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
