# 🦅 birdsongtech (work in progress)

Backend Jamstack e Dashboard 3D per il monitoraggio bioacustico automatizzato della fauna aviaria nella riserva Monumento Naturale Palude di Torre Flavia (Ladispoli, Roma).

## 🚀 Funzionalità del Progetto
* **Acquisizione in campo del canto degli uccelli e registrazione con analisi/riconoscimento specie tramite agente AI. Invio giornaliero del log dei file riconosciuti tramite trasmissione con tecnologia Lo.Ra. con scheda Heltec V4 che gestisce anche la ricarica delle batterie tramite pannello solare.
* **Integrazione di Campo:** Parsing automatico dei log CSV ricevuti dal modulo Heltec V3 e collegato in seriale al Raspberry Pi 3 nella postazione base.
* **Database Relazionale:** Storico strutturato e blindato su SQLite (`birdsong_history.db`).
* **Mappa Interattiva:** Visualizzazione geolocalizzata stazionaria dei nodi di ascolto nella riserva (Coordinate: 41.95970, 12.05215).
* **Spettrogramma 3D Neon:** Analizzatore di frequenza bioacustica tridimensionale ad alta brillantezza con shader fluorescenti ed elaborazione FFT logaritmica.

## 🔗 Collegamenti Rapidi
* 📍 **Dashboard e Mappa Live**
https://meshroma.github.io/birdsongtech/ricerca.html
* 🦅 **Visualizzatore 3D (Esempio Pettirosso)**
https://meshroma.github.io/birdsongtech/index.html?audio=canto.wav&specie=Pettirosso


