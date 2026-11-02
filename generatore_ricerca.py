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
        cur.execute("SELECT timestamp, nodo, specie, conf, batteria, temperatura, pressione, gps_lat, gps_lon, altitudine_mslm, audio FROM rilevamenti_bioacustici ORDER BY timestamp DESC")
        righe = cur.fetchall()
    except Exception as e:
        print("Errore query:", e)
        conn.close()
        return
    conn.close()
    
    tabella_html = ""
    for r in righe:
        timestamp, nodo, specie, conf, batt, temp, press, lat, lon, alt, audio = r
        conf_perc = f"{int(conf * 100)}%" if conf else "N/D"
        
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
            <td>{temp} C / {press} hPa</td>
            <td>{alt}m s.l.m.</td>
            <td><a class="btn-listen" href="index.html?audio={audio_url_completo}&specie={urllib.parse.quote(specie)}&meta={urllib.parse.quote(nodo)}" target="_blank">VISUALIZZA 3D</a></td>
        </tr>
        """
        
    if os.path.exists("ricerca.html"):
        with open("ricerca.html", "r", encoding="utf-8") as f:
            base = f.read()
        if "<!--TABELLA_DATI-->" in base:
            parts = base.split("<!--TABELLA_DATI-->")
            nuova_pagina = parts[0] + "<!--TABELLA_DATI-->" + tabella_html + parts[1]
            with open("ricerca.html", "w", encoding="utf-8") as f:
                f.write(nuova_pagina)
            print("Dashboard generata correttamente.")

if __name__ == "__main__":
    genera()
