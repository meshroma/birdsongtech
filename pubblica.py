# -*- coding: utf-8 -*-
"""
birdsongtech - pubblicazione dell'archivio bioacustico di Torre Flavia.

Sequenza:
  1. legge il log CSV ricevuto via LoRa/Meshtastic (birdsong_log.csv) e
     inserisce le righe nuove nel database SQLite (birdsong_history.db);
  2. cerca i file .wav scaricati dalla XIAO nella cartella da_importare/,
     li associa ai rilevamenti e li copia nell'archivio locale audio/AAAA/MM/;
  3. carica su Internet Archive (archive.org) i .wav non ancora pubblicati;
  4. esporta i dati per il sito in data/rilevamenti.js e data/rilevamenti.json.

Gli audio NON vanno su GitHub (audio/ e' in .gitignore): il sito li legge da archive.org.

Uso:
  python pubblica.py            pubblicazione normale
  python pubblica.py --locale   prova sul PC: il sito usa gli audio della cartella audio/

Prima volta con Internet Archive:
  pip install internetarchive
  ia configure                  (inserisci email e password dell'account archive.org)
"""
import csv
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime

# ---------------------------------------------------------------- configurazione
CARTELLA = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(CARTELLA, "birdsong_history.db")
CSV_LOG = os.path.join(CARTELLA, "birdsong_log.csv")
CARTELLA_IMPORT = os.path.join(CARTELLA, "da_importare")       # qui copi i .wav scaricati dalla XIAO
CARTELLA_IMPORTATI = os.path.join(CARTELLA_IMPORT, "_importati")  # i .wav gia' pubblicati finiscono qui
CARTELLA_AUDIO = os.path.join(CARTELLA, "audio")                # audio pubblicati sul sito
CARTELLA_DATI = os.path.join(CARTELLA, "data")

# ---- Internet Archive
ARCHIVE_ATTIVO = True                       # False = nessun caricamento (gli audio restano solo sul PC)
ARCHIVE_PREFISSO = "birdsongtech-torreflavia"  # gli item saranno birdsongtech-torreflavia-2026-10, -2026-11, ...
ARCHIVE_PROVA = False                       # True = carica in "test_collection" (cancellata da archive.org dopo 30 giorni)
LICENZA = "https://creativecommons.org/licenses/by-nc-sa/4.0/"   # licenza delle registrazioni
MODO_LOCALE = "--locale" in sys.argv

# Posizione della postazione usata quando una riga non ha coordinate GPS
STAZIONE_DEFAULT = {"lat": 41.95970, "lon": 12.05215}

FORMATO_TS = "%Y-%m-%d %H:%M:%S"
DURATA_MAX = 16  # secondi: durata massima dei .wav registrati dalla XIAO

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------- database
def apri_database():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
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
        )""")
    colonne = {r[1] for r in cur.execute("PRAGMA table_info(rilevamenti_bioacustici)")}
    nuove = {
        "file_audio": "TEXT",    # nome del .wav sulla XIAO (facoltativo nel CSV)
        "audio_locale": "TEXT",  # percorso nell'archivio locale audio/AAAA/MM/...
    }
    for nome, tipo in nuove.items():
        if nome not in colonne:
            cur.execute(f"ALTER TABLE rilevamenti_bioacustici ADD COLUMN {nome} {tipo}")
    # audio_url = indirizzo pubblico su archive.org. I vecchi valori "audio/..." di prova non puntano a file reali.
    cur.execute("UPDATE rilevamenti_bioacustici SET audio_url=NULL WHERE audio_url NOT LIKE 'http%'")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON rilevamenti_bioacustici(timestamp)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_nodo ON rilevamenti_bioacustici(nodo)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_specie ON rilevamenti_bioacustici(specie_ita)")
    conn.commit()
    return conn


def numero(valore, tipo=float):
    if valore is None:
        return None
    valore = str(valore).strip().replace(",", ".")
    if valore == "":
        return None
    try:
        return tipo(float(valore))
    except ValueError:
        return None


def importa_log(conn):
    """Inserisce nel DB le righe del CSV non ancora presenti."""
    if not os.path.exists(CSV_LOG):
        print(f"[!] Log non trovato: {CSV_LOG}")
        return 0
    cur = conn.cursor()
    nuovi = scartati = 0
    with open(CSV_LOG, newline="", encoding="utf-8-sig") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):
            row = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
            ts, nodo, specie = row.get("timestamp"), row.get("nodo"), row.get("specie_ita")
            try:
                datetime.strptime(ts or "", FORMATO_TS)
            except ValueError:
                print(f"    [!] riga {n} ignorata: timestamp non valido ({ts!r})")
                scartati += 1
                continue
            if not nodo or not specie:
                print(f"    [!] riga {n} ignorata: manca nodo o specie")
                scartati += 1
                continue
            cur.execute("SELECT id FROM rilevamenti_bioacustici WHERE timestamp=? AND nodo=? AND specie_ita=?",
                        (ts, nodo, specie))
            if cur.fetchone():
                continue
            cur.execute("""
                INSERT INTO rilevamenti_bioacustici
                (timestamp, nodo, specie_ita, specie_sci, score_tinyml, audio_url, batteria_perc,
                 temperatura, pressione, gps_lat, gps_lon, altitudine_mslm, file_audio)
                VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)""",
                (ts, nodo, specie, row.get("specie_sci", ""), numero(row.get("score_tinyml")) or 0.0,
                 numero(row.get("batteria_perc"), int), numero(row.get("temperatura")),
                 numero(row.get("pressione")), numero(row.get("gps_lat")), numero(row.get("gps_lon")),
                 numero(row.get("altitudine_mslm")), row.get("file_audio") or None))
            nuovi += 1
            print(f"    + {ts}  {nodo}  {specie}")
    conn.commit()
    print(f"[OK] Log: {nuovi} rilevamenti nuovi" + (f", {scartati} righe scartate" if scartati else ""))
    return nuovi


# ---------------------------------------------------------------- audio
def chiave_record(ts, nodo):
    """Identificativo stabile del rilevamento, usato nei link e nei nomi dei file."""
    dt = datetime.strptime(ts, FORMATO_TS)
    nodo_pulito = re.sub(r"[^A-Za-z0-9]+", "-", nodo).strip("-")
    return f"{dt:%Y%m%d-%H%M%S}-{nodo_pulito}"


def varianti_timestamp(ts):
    """Modi in cui il timestamp puo' comparire nel nome del .wav registrato dalla XIAO."""
    dt = datetime.strptime(ts, FORMATO_TS)
    return [dt.strftime(f) for f in ("%Y%m%d_%H%M%S", "%Y%m%d-%H%M%S", "%Y-%m-%d_%H-%M-%S",
                                     "%Y-%m-%dT%H-%M-%S", "%Y%m%d%H%M%S")]


def durata_wav(percorso):
    try:
        import wave
        with wave.open(percorso, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return None


def importa_audio(conn):
    """Associa i .wav in da_importare/ ai rilevamenti e li copia in audio/AAAA/MM/."""
    os.makedirs(CARTELLA_IMPORT, exist_ok=True)
    wav = [f for f in os.listdir(CARTELLA_IMPORT)
           if f.lower().endswith(".wav") and os.path.isfile(os.path.join(CARTELLA_IMPORT, f))]
    if not wav:
        print("[OK] Audio: nessun file nuovo in da_importare/")
        return 0
    cur = conn.cursor()
    cur.execute("SELECT id, timestamp, nodo, file_audio FROM rilevamenti_bioacustici")
    righe = cur.fetchall()
    per_nome = {r[3].lower(): r for r in righe if r[3]}

    associati, orfani = 0, []
    for nome in sorted(wav):
        riga = per_nome.get(nome.lower())
        if riga is None:  # nessun nome esplicito nel log: cerco il timestamp nel nome del file
            candidati = [r for r in righe if any(v in nome for v in varianti_timestamp(r[1]))]
            if len(candidati) > 1:  # stesso istante su piu' nodi: uso il nodo nel nome del file
                candidati = [r for r in candidati if r[2].lower() in nome.lower()] or candidati[:1]
            riga = candidati[0] if candidati else None
        if riga is None:
            orfani.append(nome)
            continue
        rid, ts, nodo, _ = riga
        dt = datetime.strptime(ts, FORMATO_TS)
        rel = f"audio/{dt:%Y}/{dt:%m}/{chiave_record(ts, nodo)}.wav"
        dest = os.path.join(CARTELLA, *rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        sorgente = os.path.join(CARTELLA_IMPORT, nome)
        durata = durata_wav(sorgente)
        if durata is not None and durata > DURATA_MAX + 0.5:
            print(f"    [!] {nome} dura {durata:.1f} s (previsti al massimo {DURATA_MAX} s): nel 3D si vedranno gli ultimi {DURATA_MAX} s")
        shutil.copy2(sorgente, dest)
        os.makedirs(CARTELLA_IMPORTATI, exist_ok=True)
        shutil.move(sorgente, os.path.join(CARTELLA_IMPORTATI, nome))
        cur.execute("UPDATE rilevamenti_bioacustici SET audio_locale=? WHERE id=?", (rel, rid))
        associati += 1
        print(f"    ♪ {nome}  ->  {rel}")
    conn.commit()
    print(f"[OK] Audio: {associati} file aggiunti all'archivio locale")
    if orfani:
        print(f"[!] {len(orfani)} file senza rilevamento corrispondente (restano in da_importare/):")
        for o in orfani:
            print(f"      {o}")
    return associati


# ---------------------------------------------------------------- Internet Archive
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre"]


def metadati_item(anno, mese):
    md = {
        "mediatype": "audio",
        "collection": "test_collection" if ARCHIVE_PROVA else "opensource_audio",
        "title": f"birdsongtech - Canti di uccelli, Palude di Torre Flavia, {MESI[mese - 1]} {anno}",
        "creator": "birdsongtech",
        "description": ("Registrazioni bioacustiche della stazione di ascolto nel Monumento Naturale "
                        "Palude di Torre Flavia (Ladispoli, Roma). Ogni file e' stato riconosciuto "
                        "automaticamente da un modello TinyML su XIAO ESP32-S3. "
                        "Archivio consultabile su https://www.birdsongtech.it"),
        "subject": ["birdsong", "canto degli uccelli", "bioacustica", "Torre Flavia", "Ladispoli",
                    "field recording", "TinyML"],
        "date": f"{anno}-{mese:02d}",
        "language": "ita",
        "licenseurl": LICENZA,
        "contact": "birdsongtech@gmail.com",
    }
    return md


def carica_su_archive(conn):
    """Carica su archive.org i .wav dell'archivio locale non ancora pubblicati."""
    if MODO_LOCALE or not ARCHIVE_ATTIVO:
        return 0
    cur = conn.cursor()
    cur.execute("""SELECT id, timestamp, audio_locale FROM rilevamenti_bioacustici
                   WHERE audio_locale IS NOT NULL AND audio_url IS NULL ORDER BY timestamp""")
    da_caricare = cur.fetchall()
    if not da_caricare:
        print("[OK] Internet Archive: nessun file da caricare")
        return 0
    try:
        import internetarchive as ia
    except ImportError:
        print("[!] Internet Archive: libreria mancante. Esegui:  pip install internetarchive  e poi  ia configure")
        return 0
    sessione = ia.get_session()
    if not sessione.access_key:
        print("[!] Internet Archive: account non configurato. Esegui:  ia configure")
        return 0

    caricati = 0
    for rid, ts, locale in da_caricare:
        percorso = os.path.join(CARTELLA, *locale.split("/"))
        if not os.path.exists(percorso):
            print(f"    [!] file mancante: {locale}")
            continue
        dt = datetime.strptime(ts, FORMATO_TS)
        item = f"{ARCHIVE_PREFISSO}-{dt:%Y}-{dt:%m}"
        nome = os.path.basename(percorso)
        try:
            risposte = ia.upload(item, files={nome: percorso}, metadata=metadati_item(dt.year, dt.month),
                                 retries=3, retries_sleep=20, verbose=False)
            ok = all(r.status_code == 200 for r in risposte)
        except Exception as e:  # rete assente, credenziali errate, ...
            print(f"    [!] caricamento non riuscito per {nome}: {e}")
            ok = False
        if not ok:
            continue
        # /cors/ restituisce il file con l'intestazione CORS necessaria al player 3D
        url = f"https://archive.org/cors/{item}/{nome}"
        cur.execute("UPDATE rilevamenti_bioacustici SET audio_url=? WHERE id=?", (url, rid))
        conn.commit()
        caricati += 1
        print(f"    ↑ {nome}  ->  archive.org/details/{item}")
    print(f"[OK] Internet Archive: {caricati} di {len(da_caricare)} file caricati"
          + ("" if caricati == len(da_caricare) else " (gli altri verranno ritentati al prossimo avvio)"))
    print("     Nota: archive.org puo' impiegare qualche minuto prima di rendere ascoltabili i file nuovi.")
    return caricati


# ---------------------------------------------------------------- export per il sito
def esporta_dati(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp, nodo, specie_ita, specie_sci, score_tinyml, audio_url, audio_locale, batteria_perc,
               temperatura, pressione, gps_lat, gps_lon, altitudine_mslm
        FROM rilevamenti_bioacustici ORDER BY timestamp DESC""")
    rilevamenti, nodi = [], {}
    for (ts, nodo, specie, sci, score, url, locale, bat, temp, pres, lat, lon, alt) in cur.fetchall():
        if MODO_LOCALE:  # prova sul PC: file della cartella audio/
            audio = locale if locale and os.path.exists(os.path.join(CARTELLA, *locale.split("/"))) else None
        else:            # sito pubblico: solo i file gia' su archive.org
            audio = url
        data, ora = ts.split(" ")
        rilevamenti.append({
            "id": chiave_record(ts, nodo), "data": data, "ora": ora, "nodo": nodo,
            "specie": specie, "sci": sci, "score": round(score, 3), "audio": audio,
            "batteria": bat, "temperatura": temp, "pressione": pres,
            "lat": lat, "lon": lon, "quota": alt,
        })
        n = nodi.setdefault(nodo, {"nodo": nodo, "rilevamenti": 0, "ultimo": ts, "ultima_specie": specie,
                                   "batteria": bat, "lat": None, "lon": None, "quota": alt})
        n["rilevamenti"] += 1
        if n["lat"] is None and lat is not None and lon is not None:
            n["lat"], n["lon"] = lat, lon

    for n in nodi.values():
        if n["lat"] is None:
            n["lat"], n["lon"] = STAZIONE_DEFAULT["lat"], STAZIONE_DEFAULT["lon"]

    pacchetto = {
        "aggiornato": datetime.now().strftime(FORMATO_TS),
        "stazione": STAZIONE_DEFAULT,
        "nodi": sorted(nodi.values(), key=lambda n: n["nodo"]),
        "rilevamenti": rilevamenti,
    }
    os.makedirs(CARTELLA_DATI, exist_ok=True)
    testo = json.dumps(pacchetto, ensure_ascii=False, indent=1)
    with open(os.path.join(CARTELLA_DATI, "rilevamenti.json"), "w", encoding="utf-8") as f:
        f.write(testo)
    # versione .js: permette di aprire il sito anche con doppio clic, senza server
    with open(os.path.join(CARTELLA_DATI, "rilevamenti.js"), "w", encoding="utf-8") as f:
        f.write("window.BIRDSONG = " + testo + ";\n")
    con_audio = sum(1 for r in rilevamenti if r["audio"])
    print(f"[OK] Sito: {len(rilevamenti)} rilevamenti esportati ({con_audio} con audio), {len(nodi)} nodi"
          + ("  [MODO LOCALE: non fare il push di questi dati]" if MODO_LOCALE else ""))


if __name__ == "__main__":
    conn = apri_database()
    try:
        importa_log(conn)
        importa_audio(conn)
        carica_su_archive(conn)
        esporta_dati(conn)
    finally:
        conn.close()
