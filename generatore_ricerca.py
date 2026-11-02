# -*- coding: utf-8 -*-
import sqlite3
import urllib.parse
import os

def genera():
    db_path = "birdsong_history.db"
    if not os.path.exists(db_path):
        print("Database non trovato.")
        return
        
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute("SELECT timestamp, nodo, specie_ita, score_tinyml, batteria_perc, temperatura, pressione, gps_lat, gps_lon, altitudine_mslm, audio_url FROM rilevamenti_bioacustici ORDER BY timestamp DESC")
        righe = cur.fetchall()
    except Exception as e:
        print("Errore query database:", e)
        conn.close()
        return
    conn.close()
    
    # 1. Rigeneriamo da zero la struttura HTML fissa per evitare corruzioni precedenti
    html_struttura = """<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Rete Bioacustica Stazionaria - Torre Flavia</title>
    <link rel="stylesheet" href="https://unpkg.com" />
    <style>
        body { background: #0b0f12; color: #e2e8f0; font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; padding: 20px; }
        .container { max-width: 1100px; margin: 0 auto; }
        h1 { color: #ff3366; font-size: 24px; text-transform: uppercase; letter-spacing: 1px; }
        .card { background: #141b22; border-radius: 8px; padding: 20px; margin-bottom: 20px; border: 1px solid #1f2937; }
        h3 { color: #33ff88; margin-top: 0; display: flex; align-items: center; gap: 8px; }
        #map { height: 400px; border-radius: 6px; background: #0b0f12; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th { background: #1e293b; color: #38bdf8; text-align: left; padding: 12px; font-size: 14px; border-bottom: 2px solid #334155; }
        td { padding: 12px; font-size: 14px; border-bottom: 1px solid #334155; }
        tr:hover { background: rgba(56, 189, 248, 0.04); }
        .btn-listen { color: #33ff88; text-decoration: none; font-weight: bold; display: inline-block; }
        .btn-listen:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Rete Bioacustica Stazionaria - Torre Flavia</h1>
        
        <div class="card">
            <h3>📍 Stato Nodi di Monitoraggio di Campo</h3>
            <div id="map"></div>
        </div>

        <div class="card">
            <h3>🦅 Log Rilevamenti Bioacustici in Tempo Reale</h3>
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
                    <!--TABELLA_REALE-->
                </tbody>
            </table>
        </div>
    </div>

    <script src="https://unpkg.com"></script>
    <script>
        const map = L.map('map').setView([41.95970, 12.05215], 14);
        L.tileLayer('https://{s}://{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        // Iniezione dinamica dei marker dal database
        <!--MARKERS_MAPPA-->
    </script>
</body>
</html>"""

    tabella_html = ""
    markers_javascript = ""
    nodi_mappati = set()

    for r in righe:
        timestamp, nodo, specie, conf, batt, temp, press, lat, lon, alt, audio = r
        conf_perc = f"{int(conf * 100)}%" if conf else "N/D"
        
        # Gestione URL assoluto per lo spettrogramma
        if audio and not audio.startswith("http"):
            audio_url_completo = f"https://github.io{audio}"
        else:
            audio_url_completo = audio
            
        # 1. Compilazione riga tabella HTML
        tabella_html += f"""
        <tr>
            <td>{timestamp}</td>
            <td>{nodo}</td>
            <td><strong>{specie}</strong></td>
            <td>{conf_perc}</td>
            <td>{temp} C / {press} hPa</td>
            <td>{alt}m s.l.m.</td>
            <td><a class="btn-listen" href="index.html?audio={audio_url_completo}&specie={urllib.parse.quote(specie)}&meta={urllib.parse.quote(nodo)}" target="_blank">VISUALIZZA 3D</a></td>
        </tr>"""
        
        # 2. Compilazione Marker Mappa JavaScript (evitando duplicati sullo stesso nodo)
        if nodo not in nodi_mappati and lat and lon:
            markers_javascript += f"""
        L.circleMarker([{lat}, {lon}], {{
            radius: 8, color: '#33ff88', fillColor: '#33ff88', fillOpacity: 0.6
        }}).addTo(map).bindPopup("<b>{nodo}</b><br>Ultimo avvistamento: {specie}<br>Meteo: {temp}C / {press}hPa");"""
            nodi_mappati.add(nodo)

    # Iniezione chirurgica dei blocchi nella struttura pulita
    output_html = html_struttura.replace("<!--TABELLA_REALE-->", tabella_html)
    output_html = output_html.replace("<!--MARKERS_MAPPA-->", markers_javascript)

    with open("ricerca.html", "w", encoding="utf-8") as f:
        f.write(output_html)
    print("Dashboard interamente rigenerata con successo.")

if __name__ == "__main__":
    genera()
