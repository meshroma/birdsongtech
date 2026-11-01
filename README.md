# 🦅 birdsongtech (work in progress)

Backend Jamstack e Dashboard 3D per il monitoraggio bioacustico automatizzato della fauna aviaria nella riserva Monumento Naturale Palude di Torre Flavia (Ladispoli, Roma).

## 🚀 Funzionalità del Progetto
* **Acquisizione in campo del canto degli uccelli e registrazione con analisi/riconoscimento specie tramite agente AI su XAIO ESP32S3. Invio giornaliero del log dei file riconosciuti tramite trasmissione con tecnologia Lo.Ra. con scheda Heltec V4 (protocollo Meshtastic) che gestisce anche la ricarica delle batterie tramite pannello solare.
* **Integrazione dati campo/base:** Parsing automatico dei log CSV ricevuti dal modulo Heltec V3 e collegato in seriale al Raspberry Pi3 nella postazione base.
* **Database Relazionale:** Storico strutturato e blindato su SQLite (`birdsong_history.db`).
* **Mappa Interattiva:** Visualizzazione geolocalizzata stazionaria dei nodi di ascolto nella riserva (Coordinate: 41.95970, 12.05215).
* **Spettrogramma 3D Neon:** Analizzatore di frequenza bioacustica tridimensionale con shader fluorescenti ed elaborazione FFT logaritmica.

## 🔗 Collegamenti Rapidi
* 📍 **Dashboard e Mappa Live**









