import os
import sqlite3
import csv
from datetime import datetime

# Configurazione percorsi
DB_NAME = "birdsong_history.db"
CSV_PI_PATH = "birdsong_log.csv"

# Percorso assoluto del tuo frontend universale 3D (adattato dal tuo log)
FRONTEND_3D_URL = "http://localhost:8080/index.html" 

def inizializza_database():
    """Crea il database SQLite locale e la tabella bioacustica indicizzata."""
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
            audio_url TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON rilevamenti_bioacustici(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodo ON rilevamenti_bioacustici(nodo)')
    conn.commit()
    conn.close()

def merge_logs_e_audio():
    """Legge il CSV del Raspberry Pi e inserisce i dati nel DB."""
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
            
            # Simulazione URL audio (in produzione sarà l'URL del cloud o del server locale)
            audio_url = f"audio/{timestamp.replace(' ', '_').replace(':', '-')}.wav"

            cursor.execute('''
                SELECT id FROM rilevamenti_bioacustici 
                WHERE timestamp = ? AND nodo = ? AND specie_ita = ?
            ''', (timestamp, nodo, specie_ita))
            
            if cursor.fetchone() is None:
                cursor.execute('''
                    INSERT INTO rilevamenti_bioacustici (timestamp, nodo, specie_ita, specie_sci, score_tinyml, audio_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (timestamp, nodo, specie_ita, specie_sci, score, audio_url))
                print(f" ➕ Rilevamento inserito nel DB: {specie_ita} ({timestamp})")
                
    conn.commit()
    conn.close()

def genera_archivio_jamstack():
    """Estrae i dati dal DB e genera le pagine HTML statiche suddivise per Anno/Mese/Giorno."""
    print("[*] Generazione pagine dell'archivio Jamstack...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Recupera tutti i rilevamenti ordinati dal più recente
    cursor.execute("SELECT timestamp, nodo, specie_ita, specie_sci, score_tinyml, audio_url FROM rilevamenti_bioacustici ORDER BY timestamp DESC")
    rilevamenti = cursor.fetchall()
    
    # Raggruppiamo i rilevamenti per data (YYYY-MM-DD)
    rilevamenti_per_giorno = {}
    for r in rilevamenti:
        dt = datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")
        data_str = dt.strftime("%Y-%m-%d")
        if data_str not in rilevamenti_per_giorno:
            rilevamenti_per_giorno[data_str] = []
        rilevamenti_per_giorno[data_str].append(r)
        
    # 2. Genera i file HTML fisici nell'albero delle cartelle
    for data_str, dati in rilevamenti_per_giorno.items():
        dt = datetime.strptime(data_str, "%Y-%m-%d")
        anno = dt.strftime("%Y")
        mese = dt.strftime("%m")
        giorno = dt.strftime("%d")
        
        # Crea la struttura delle cartelle locale (es: archivio/2026/10/)
        target_dir = os.path.join("archivio", anno, mese)
        os.makedirs(target_dir, exist_ok=True)
        
        filepath = os.path.join(target_dir, f"{giorno}.html")
        
        # Generazione dell'HTML statico
        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Rilevamenti Bioacustici - {giorno}/{mese}/{anno}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #121212; color: #e0e0e0; padding: 30px; }}
        h1 {{ color: #4CAF50; border-bottom: 2px solid #2d2d2d; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: #1e1e1e; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #2e7d32; color: white; }}
        tr:hover {{ background: #252525; }}
        .btn-3d {{ background: #00bcd4; color: black; padding: 6px 12px; text-decoration: none; font-weight: bold; border-radius: 4px; display: inline-block; }}
        .btn-3d:hover {{ background: #00e5ff; }}
        .score {{ font-family: monospace; font-weight: bold; color: #8bc34a; }}
    </style>
</head>
<body>

    <h1>📝 Rilevamenti del {giorno}/{mese}/{anno}</h1>
    <p>Stazione Base: Torre Flavia Mesh Network</p>

    <table>
        <thead>
            <tr>
                <th>Orario</th>
                <th>Nodo di Campo</th>
                <th>Specie (Volatile)</th>
                <th>Nome Scientifico</th>
                <th>Confidenza TinyML</th>
                <th>Analisi Spaziale</th>
            </tr>
        </thead>
        <tbody>
"""
        for r in dati:
            ts_ora = datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
            nodo = r[1]
            specie_ita = r[2]
            specie_sci = r[3]
            score = f"{r[4]*100:.1f}%"
            audio_url = r[5]
            
            # COMPILAZIONE STRINGA URL PARSING PER IL MOTORE CIECO 3D
            # Il link punta a index.html passando i parametri necessari in GET
            link_3d = f"{FRONTEND_3D_URL}?audio={audio_url}&specie={specie_ita}&meta={nodo}"
            
            html_content += f"""            <tr>
                <td>{ts_ora}</td>
                <td><strong>{nodo}</strong></td>
                <td>{specie_ita}</td>
                <td><em>{specie_sci}</em></td>
                <td class="score">{score}</td>
                <td><a href="{link_3d}" target="_blank" class="btn-3d">Avvia Player 3D 🌐</a></td>
            </tr>\n"""
            
        html_content += """        </tbody>
    </table>
    
    <br><a href="../../../" style="color: #aaa; text-decoration: none;">← Torna alla Home dell'Archivio</a>
</body>
</html>"""
        
        with open(filepath, "w", encoding="utf-8") as html_file:
            html_file.write(html_content)
        print(f" 📄 Pagina statica generata: {filepath}")

    print("🟢 Archivio Jamstack aggiornato con successo.")

if __name__ == "__main__":
    inizializza_database()
    merge_logs_e_audio()
    genera_archivio_jamstack()
