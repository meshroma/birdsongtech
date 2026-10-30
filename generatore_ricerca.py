import os
import sqlite3
import json

DB_NAME = "birdsong_history.db"
OUTPUT_HTML = "ricerca.html"
FRONTEND_3D_URL = "http://localhost:8080/index.html"

def estrai_dati_e_genera_ricerca():
    print("[*] Interrogazione database per il motore di ricerca...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Estraiamo tutti i dati utili per la ricerca avanzata
    cursor.execute('''
        SELECT timestamp, nodo, specie_ita, specie_sci, score_tinyml, audio_url, 
               batteria_perc, temperatura, pressione, gps_lat, gps_lon, altitudine_mslm 
        FROM rilevamenti_bioacustici ORDER BY timestamp DESC
    ''')
    rows = cursor.fetchall()
    conn.close()

    # Trasformiamo i record in una lista di dizionari per JavaScript
    rilevamenti_lista = []
    elenco_specie = set()
    elenco_nodi = set()

    for r in rows:
        # r è una tupla: r[0]=timestamp, r[1]=nodo, r[2]=specie_ita, ecc.
        timestamp = r[0]
        nodo = r[1]
        specie_ita = r[2]
        specie_sci = r[3]
        score = r[4]
        audio_url = r[5]
        batteria = r[6]
        temperatura = r[7]
        pressione = r[8]
        lat = r[9]
        lon = r[10]
        altitudine = r[11]

        elenco_specie.add(specie_ita)
        elenco_nodi.add(nodo)
        
        rilevamenti_lista.append({
            "timestamp": timestamp,
            "nodo": nodo,
            "specie_ita": specie_ita,
            "specie_sci": specie_sci,
            "score": round(score * 100, 1),
            "audio_url": audio_url,
            "batteria": batteria if batteria is not None else "--",
            "temperatura": temperatura if temperatura is not None else "--",
            "pressione": pressione if pressione is not None else "--",
            "lat": lat if lat is not None else 0,
            "lon": lon if lon is not None else 0,
            "altitudine": altitudine if altitudine is not None else 0
        })

    # Generazione dei tag select dinamici per i filtri
    opzioni_specie = "".join([f'<option value="{s}">{s}</option>' for s in sorted(elenco_specie)])
    opzioni_nodi = "".join([f'<option value="{n}">{n}</option>' for n in sorted(elenco_nodi)])

    # Template HTML
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>🔎 Motore di Ricerca Bioacustica - Torre Flavia</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #121212; color: #e0e0e0; padding: 30px; }}
        h1 {{ color: #00bcd4; border-bottom: 2px solid #2d2d2d; padding-bottom: 10px; }}
        .filtri-container {{ background: #1e1e1e; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; gap: 15px; flex-wrap: wrap; align-items: center; }}
        label {{ font-weight: bold; color: #aaa; }}
        select, input {{ background: #2d2d2d; color: #fff; border: 1px solid #444; padding: 8px; border-radius: 4px; font-size: 1em; }}
        table {{ width: 100%; border-collapse: collapse; background: #1e1e1e; margin-top: 10px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #007c8d; color: white; }}
        tr:hover {{ background: #252525; }}
        .btn-3d {{ background: #00bcd4; color: black; padding: 6px 12px; text-decoration: none; font-weight: bold; border-radius: 4px; display: inline-block; }}
        .btn-3d:hover {{ background: #00e5ff; }}
        .counter {{ font-size: 1.1em; color: #8bc34a; font-weight: bold; margin-bottom: 10px; }}
    </style>
</head>
<body>

    <h1>🔎 Ricerca Avanzata Rilevamenti Bioacustici</h1>
    
    <div class="filtri-container">
        <div>
            <label for="filtroSpecie">Filtra per Specie:</label>
            <select id="filtroSpecie" onchange="filtraDati()">
                <option value="">-- Tutte le Specie --</option>
                {opzioni_specie}
            </select>
        </div>
        <div>
            <label for="filtroNodo">Filtra per Nodo:</label>
            <select id="filtroNodo" onchange="filtraDati()">
                <option value="">-- Tutti i Nodi --</option>
                {opzioni_nodi}
            </select>
        </div>
        <div>
            <label for="filtroScore">Confidenza TinyML Minima:</label>
            <input type="number" id="filtroScore" min="0" max="100" value="0" oninput="filtraDati()"> %
        </div>
    </div>

    <div class="counter" id="risultatiCounter">Rilevamenti trovati: 0</div>

    <table>
        <thead>
            <tr>
                <th>Data e Ora</th>
                <th>Nodo & Quota</th>
                <th>Specie Identificata</th>
                <th>Confidenza TinyML</th>
                <th>Meteo di Campo</th>
                <th>Azione</th>
            </tr>
        </thead>
        <tbody id="tabellaRisultati">
            <!-- I dati verranno iniettati dinamicamente da JS -->
        </tbody>
    </table>

    <script>
        const database = {json.dumps(rilevamenti_lista)};
        const frontendUrl = "{FRONTEND_3D_URL}";

        function filtraDati() {{
            const specieScelta = document.getElementById("filtroSpecie").value;
            const nodoScelto = document.getElementById("filtroNodo").value;
            const scoreMinimo = parseFloat(document.getElementById("filtroScore").value) || 0;

            const tbody = document.getElementById("tabellaRisultati");
            tbody.innerHTML = "";

            let contatore = 0;

            database.forEach(r => {{
                if (specieScelta && r.specie_ita !== specieScelta) return;
                if (nodoScelto && r.nodo !== nodoScelto) return;
                if (r.score < scoreMinimo) return;

                contatore++;

                const link3d = frontendUrl + "?audio=" + r.audio_url + "&specie=" + r.specie_ita + "&meta=" + r.nodo + " (" + r.temperatura + "°C - " + r.altitudine + "m)";

                const row = "<tr>" +
                    "<td>" + r.timestamp + "</td>" +
                    "<td><strong>" + r.nodo + "</strong><br><small>⛰️ " + r.altitudine + " m s.l.m.</small></td>" +
                    "<td>" + r.specie_ita + "<br><small style='color:#aaa;'><em>" + r.specie_sci + "</em></small></td>" +
                    "<td style='color:#8bc34a; font-weight:bold;'>" + r.score + "%</td>" +
                    "<td style='color:#ffa726; font-family:monospace;'>🌡️ " + r.temperatura + "°C<br>🌀 " + r.pressione + " hPa</td>" +
                    "<td><a href='" + link3d + "' target='_blank' class='btn-3d'>Analisi Spaziale 3D 🌐</a></td>" +
                "</tr>";
                
                tbody.innerHTML += row;
            }});

            document.getElementById("risultatiCounter").innerText = "Rilevamenti trovati: " + contatore;
        }}

        filtraDati();
    </script>
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"🟢 Motore di ricerca generato con successo in: {OUTPUT_HTML}")

if __name__ == "__main__":
    estrai_dati_e_genera_ricerca()
