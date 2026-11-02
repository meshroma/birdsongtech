import urllib.parse
import sqlite3
import os

def genera_dashboard():
    # 1. Connessione al database SQLite locale
    conn = sqlite3.connect('birdsong_history.db')
    cursor = conn.cursor()
    
    # Estrazione delle rilevazioni storiche dal database
    try:
        cursor.execute("SELECT timestamp, nodo, specie_ita, confidenza, batteria_perc, temperatura, pressione, altitudine_mslm, audio_path FROM birdsong_history ORDER BY timestamp DESC")
        righe = cursor.fetchall()
    except sqlite3.OperationalError:
        righe = []
        
    conn.close()

       # 2. Generazione delle righe della tabella in formato HTML
    tabella_html = ""
    for r in righe:
        r = list(r) + [''] * (9 - len(r)) if len(r) < 9 else r[:9]
        timestamp, nodo, specie, conf, batt, temp, press, alt, audio = r
        conf_perc = f"{int(conf * 100)}%" if conf else "N/D"
        
        # SBLOCCO UNIVERSALE: Se l'audio non è già un link internet (http), 
        # Python costruisce l'indirizzo web assoluto ufficiale della tua repository GitHub Pages
        if audio and not audio.startswith("http"):
            audio_url_completo = f"https://github.io{audio}"
        else:
            audio_url_completo = audio

        tabella_html += f"""
        <tr>
            <td>{timestamp}</td>
            <td>{nodo}</td>
            <td><strong>{specie}</strong></td>
            <td>{conf_perc}</td>
            <td>{temp}°C / {press} hPa</td>
            <td>{alt}m s.l.m.</td>
            <td>
                <a class="btn-listen" href="index.html?audio={audio_url_completo}&specie={urllib.parse.quote(specie)}&meta={urllib.parse.quote(nodo)}" target="_blank" style="color: #33ff88; text-decoration: none; font-weight: bold;">
                    ➧ VISUALIZZA 3D
                </a>
            </td>
        </tr>
        """


    # 3. Struttura HTML (Divisa in due parti per inserire la tabella senza mandare in crash la f-string di Python)
    html_inizio = """<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🦅 Rete Bioacustica Torre Flavia - Dashboard</title>
    
    <!-- Libreria Cartografica Leaflet.js -->
    <link rel="stylesheet" href="https://unpkg.com" />
    
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #09090b; color: #e2e8f0; padding: 20px; }
        .container { width: 100%; max-width: 1200px; margin: 0 auto; }
        h1 { color: #f43f5e; margin-bottom: 20px; text-shadow: 0 0 10px rgba(244,63,94,0.2); }
        
        /* Contenitore della mappa OpenStreetMap */
        #map-container {
            width: 100%;
            margin: 0 auto 25px auto;
            padding: 20px;
            background: #141416;
            border-radius: 16px;
            border: 1px solid #27272a;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        #map {
            width: 100%;
            height: 400px;
            border-radius: 12px;
            background: #020203;
            z-index: 10;
        }
        .map-header {
            font-size: 1.3rem;
            color: #4ade80;
            margin-bottom: 12px;
            font-weight: bold;
            letter-spacing: 0.5px;
        }
        
        /* Tabella dati bioacustici */
        table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #141416; border-radius: 12px; overflow: hidden; border: 1px solid #27272a; }
        th, td { padding: 14px 15px; text-align: left; border-bottom: 1px solid #27272a; }
        th { background: #27272a; color: #38bdf8; font-weight: 600; letter-spacing: 0.5px; }
        tr:hover { background: #1f1f23; }
        .btn-listen { background: linear-gradient(135deg, #ff0055 0%, #9d4edd 100%); color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; box-shadow: 0 4px 12px rgba(255,0,85,0.2); transition: transform 0.15s; }
        .btn-listen:hover { transform: scale(1.03); box-shadow: 0 4px 15px rgba(255,0,85,0.4); }
    </style>
</head>
<body>

<div class="container">
    <h1>Rete Bioacustica Stazionaria - Torre Flavia</h1>
    
    <!-- Box della Mappa -->
    <div id="map-container">
        <div class="map-header">📍 Stato Nodi di Monitoraggio di Campo</div>
        <div id="map"></div>
    </div>

    <!-- Tabella Storico Rilevamenti -->
    <table>
        <thead>
            <tr>
                <th>Data e Ora</th>
                <th>Stazione</th>
                <th>Specie Rilevata</th>
                <th>Confidenza TinyML</th>
                <th>Meteo Locale</th>
                <th>Quota Altimetrica</th>
                <th>Spettrogramma 3D</th>
            </tr>
        </thead>
        <tbody>
"""

    html_fine = """        </tbody>
    </table>
</div>

<!-- Script Leaflet.js per la mappatura del nodo -->
<script src="https://unpkg.com"></script>
<script>
    document.addEventListener('DOMContentLoaded', () => {
        // Coordinate fisse fornite per il primo ricevitore stazionario
        const lat = 41.95970;
        const lon = 12.05215;

        // Centra la mappa sulla palude di Torre Flavia
        const map = L.map('map').setView([lat, lon], 14);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap'
        }).addTo(map);

        // Indicatore neon circolare sul ricevitore sul campo
        const marker = L.circleMarker([lat, lon], {
            radius: 11,
            fillColor: '#00f2fe',
            color: '#38bdf8',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.85
        }).addTo(map);

        marker.bindPopup(`
            <div style="font-family: sans-serif; color: #1e1e1e; min-width: 180px;">
                <h4 style="margin: 0 0 5px 0; color: #ff0055;">RICEVITORE FISSO #1</h4>
                <div style="font-size: 0.9em; border-top: 1px solid #e2e8f0; padding-top: 4px; margin-top: 4px;">
                    <b>Ubicazione:</b> Palude Riserva<br>
                    <b>Telemetria:</b> <span style="color: #22c55e; font-weight: bold;">ONLINE</span><br>
                    <b>Batteria Nodo:</b> 94% 🔋
                </div>
            </div>
        `);
    });
</script>
</body>
</html>
"""

    # Unione finale delle stringhe senza conflitti di f-string
    html_completo = html_inizio + tabella_html + html_fine

    # Scrittura del file di output ricerca.html nella cartella di progetto
    with open('ricerca.html', 'w', encoding='utf-8') as f:
        f.write(html_completo)
    print("🟢 Motore di ricerca e mappa aggiornati in: ricerca.html")

if __name__ == "__main__":
    genera_dashboard()
