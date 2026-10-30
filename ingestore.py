import os
import sqlite3
import csv
from datetime import datetime

# Configurazione percorsi
DB_NAME = "birdsong_history.db"
CSV_PI_PATH = "birdsong_log.csv"
FRONTEND_3D_URL = "http://localhost:8080/index.html" 

def inizializza_database():
    """Crea il database SQLite espanso con telemetria, posizione GPS e quota mslm."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rilevamenti_bioacustici (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            nodo TEXT NOT NULL,
            specie_ita TEXT NOT NULL,
            specie_sci TEXT NOT NULL,
            score_tinyml REAL NOT NULL,
            audio_url TEXT,
            batteria_perc INTEGER,
            temperatura REAL,
            pressione REAL,
            gps_lat REAL,
            gps_lon REAL,
            altitudine_mslm REAL
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON rilevamenti_bioacustici(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodo ON rilevamenti_bioacustici(nodo)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_specie ON rilevamenti_bioacustici(specie_ita)')
    
    conn.commit()
    conn.close()

def merge_logs_e_audio():
    """Legge il CSV del Raspberry Pi incorporando telemetria e quota di campo."""
    if not os.path.exists(CSV_PI_PATH):
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    with open(CSV_PI_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            timestamp = row.get('timestamp')
            nodo = row.get('nodo')
            specie_ita = row.get('specie_ita')
            specie_sci = row.get('specie_sci')
            score = float(row.get('score_tinyml', 0.0))
            audio_url = f"audio/{timestamp.replace(' ', '_').replace(':', '-')}.wav"
            
            bat = row.get('batteria_perc')
            batteria_perc = int(bat) if bat else None
            temp = row.get('temperatura')
            temperatura = float(temp) if temp else None
            pres = row.get('pressione')
            pressione = float(pres) if pres else None
            lat = row.get('gps_lat')
            gps_lat = float(lat) if lat else None
            lon = row.get('gps_lon')
            gps_lon = float(lon) if lon else None
            alt = row.get('altitudine_mslm')
            altitudine_mslm = float(alt) if alt else None

            cursor.execute('''
                SELECT id FROM rilevamenti_bioacustici 
                WHERE timestamp = ? AND nodo = ? AND specie_ita = ?
            ''', (timestamp, nodo, specie_ita))
            
            if cursor.fetchone() is None:
                cursor.execute('''
                    INSERT INTO rilevamenti_bioacustici 
                    (timestamp, nodo, specie_ita, specie_sci, score_tinyml, audio_url, batteria_perc, temperatura, pressione, gps_lat, gps_lon, altitudine_mslm)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, nodo, specie_ita, specie_sci, score, audio_url, batteria_perc, temperatura, pressione, gps_lat, gps_lon, altitudine_mslm))
                print(f" ➕ Inserito con quota: {specie_ita} ({timestamp} | {altitudine_mslm}m s.l.m.)")
                
    conn.commit()
    conn.close()

def genera_archivio_jamstack():
    """Genera le pagine HTML inserendo la quota s.l.m. e lo stile grafico coordinato."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT timestamp, nodo, specie_ita, specie_sci, score_tinyml, audio_url, 
               batteria_perc, temperatura, pressione, gps_lat, gps_lon, altitudine_mslm 
        FROM rilevamenti_bioacustici ORDER BY timestamp DESC
    ''')
    rilevamenti = cursor.fetchall()
    conn.close()
    
    rilevamenti_per_giorno = {}
    for r in rilevamenti:
        dt = datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")
        data_str = dt.strftime("%Y-%m-%d")
        if data_str not in rilevamenti_per_giorno:
            rilevamenti_per_giorno[data_str] = []
        rilevamenti_per_giorno[data_str].append(r)
        
    for data_str, dati in rilevamenti_per_giorno.items():
        dt = datetime.strptime(data_str, "%Y-%m-%d")
        anno, mese, giorno = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")
        
        target_dir = os.path.join("archivio", anno, mese)
        os.makedirs(target_dir, exist_ok=True)
        filepath = os.path.join(target_dir, f"{giorno}.html")
        
        # Percorso relativo per risalire l'albero delle cartelle fino alla root degli assets
        path_to_assets = "../../../assets"
        path_to_home = "../../../"

        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Archivio Ambientale - {giorno}/{mese}/{anno}</title>
    <!-- LINK ALLA FAVICON IN ASSETS -->
    <link rel="icon" type="image/x-icon" href="{path_to_assets}/favicon.ico">
    
    <style>
        body {{ 
            font-family: 'Segoe UI', sans-serif; 
            /* INSERIMENTO SFONDO AMBIENTALE COORDINATO */
            background: linear-gradient(rgba(18, 18, 18, 0.85), rgba(18, 18, 18, 0.95)), url('{path_to_assets}/background.jpg') no-repeat center center fixed;
            background-size: cover;
            color: #e0e0e0; 
            padding: 30px; 
        }}
        
        /* HEADER COORDINATO CON LOGO */
        .main-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            border-bottom: 2px solid #2d2d2d;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }}
        .project-logo {{
            width: 55px;
            height: 55px;
            object-fit: contain;
        }}
        h1 {{ color: #4CAF50; margin: 0; font-size: 2.2em; }}
        
        table {{ width: 100%; border-collapse: collapse; background: rgba(30, 30, 30, 0.9); margin-top: 10px; border-radius: 6px; overflow: hidden; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #2e7d32; color: white; }}
        tr:hover {{ background: rgba(45, 45, 45, 0.8); }}
        .btn-3d {{ background: #00bcd4; color: black; padding: 6px 12px; text-decoration: none; font-weight: bold; border-radius: 4px; display: inline-block; }}
        .btn-3d:hover {{ background: #00e5ff; }}
        .badge {{ background: #444; padding: 4px 8px; border-radius: 12px; font-size: 0.85em; font-family: monospace; }}
        .bat-ok {{ color: #8bc34a; }}
        .telemetria {{ color: #ffa726; font-family: monospace; }}
    </style>
</head>
<body>

    <!-- HEADER STRUTTURATO CON LOGO -->
    <div class="main-header">
        <img src="{path_to_assets}/logo.png" alt="Birdsong AI Logo" class="project-logo" onerror="this.style.display='none';">
        <h1>📝 Rilevamenti & Telemetria del {giorno}/{mese}/{anno}</h1>
    </div>
    
    <p>Riserva Naturale di Torre Flavia — Rete Stazioni Sensorie Meshtastic</p>

    <table>
        <thead>
            <tr>
                <th>Orario</th>
                <th>Nodo (GPS & Quota)</th>
                <th>Specie / Sci</th>
                <th>Confidenza</th>
                <th>Stato Diagnostico</th>
                <th>Meteo Locale</th>
                <th>Analisi Spaziale</th>
            </tr>
        </thead>
        <tbody>
"""
        for r in dati:
            timestamp, nodo, specie_ita, specie_sci, score, audio_url, batteria, temperatura, pressione, lat, lon, altitudine = r
            ts_ora = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
            conf_str = f"{score * 100:.1f}%"
            
            bat = f"<span class='bat-ok'>🔋 {batteria}%</span>" if batteria is not None else "n/d"
            temp = f"{temperatura}°C" if temperatura is not None else "--"
            pres = f"{pressione} hPa" if pressione is not None else "--"
            
            quota_str = f" | ⛰️ {altitudine} m s.l.m." if altitudine is not None else ""
            gps = f"<a href='https://google.com{lat},{lon}' target='_blank' style='color:#00bcd4;text-decoration:none;'>📍 {lat}, {lon}</a>{quota_str}" if lat and lon else f"No GPS {quota_str}"
            
            link_3d = f"{FRONTEND_3D_URL}?audio={audio_url}&specie={specie_ita}&meta={nodo} ({temp} - {pres}{quota_str})"
            
            html_content += f"""            <tr>
                <td>{ts_ora}</td>
                <td><strong>{nodo}</strong><br><small>{gps}</small></td>
                <td>{specie_ita}<br><small style="color:#aaa;"><em>{specie_sci}</em></small></td>
                <td style="color:#8bc34a; font-weight:bold;">{conf_str}</td>
                <td><span class="badge">{bat}</span></td>
                <td class="telemetria">🌡️ {temp}<br>🌀 {pres}</td>
                <td><a href="{link_3d}" target="_blank" class="btn-3d">Avvia Player 3D 🌐</a></td>
            </tr>\n"""
            
        html_content += f"""        </tbody>
    </table>
    <br><a href="{path_to_home}" style="color: #aaa; text-decoration: none;">← Torna all'Indice Generale</a>
</body>
</html>"""
        
        with open(filepath, "w", encoding="utf-8") as html_file:
            html_file.write(html_content)

    print("🟢 Archivio Jamstack con alloggiamenti grafici storici aggiornato.")

if __name__ == "__main__":
    inizializza_database()
    merge_logs_e_audio()
    genera_archivio_jamstack()
