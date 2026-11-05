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
from datetime import datetime, timedelta

# ---------------------------------------------------------------- configurazione
CARTELLA = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(CARTELLA, "birdsong_history.db")
CSV_LOG = os.path.join(CARTELLA, "birdsong_log.csv")
CSV_TELEMETRIA = os.path.join(CARTELLA, "telemetria.csv")      # telemetria dei risvegli, dal Raspberry
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
# Rilevamenti dimostrativi: restano visibili sul sito anche senza audio.
# Quando arrivano i primi canti veri, svuota l'elenco:  DIMOSTRATIVI = set()
DIMOSTRATIVI = {"2026-10-30 10:21:00", "2026-10-30 11:15:30", "2026-10-30 14:02:15"}

# Posizione della postazione usata quando una riga non ha coordinate GPS
STAZIONE_DEFAULT = {"lat": 41.95970, "lon": 12.05215}

# ---- verifiche degli esperti (docs/VERIFICHE.md)
CARTELLA_VERIFICHE = os.path.join(CARTELLA, "verifiche")   # qui salvi i file restituiti dai revisori
CARTELLA_LOTTI = os.path.join(CARTELLA, "lotti")           # qui pubblica.py --lotto crea i file da spedire
SITO = "https://meshroma.github.io/birdsongtech/"          # indirizzo diretto del sito (link nei lotti)

# ---- copia di sicurezza sulla scheda SD del Raspberry (supporto fisico diverso dal PC)
BACKUP_PI = True                               # False = nessuna copia
BACKUP_PI_HOST = "pi@192.168.1.100"
BACKUP_PI_CARTELLA = "/home/pi/birdsongtech_backup"
# cosa copiare: audio (solo i file nuovi) + database, CSV, documenti, presentazione, verifiche
BACKUP_CARTELLE = ["audio", "docs", "presentazione", "verifiche", "lotti"]
BACKUP_FILE = ["birdsong_history.db", "birdsong_log.csv", "telemetria.csv"]

FORMATO_TS = "%Y-%m-%d %H:%M:%S"
DURATA_MAX = 16  # secondi: durata massima dei .wav registrati dalla XIAO
SOGLIA_VALIDI = 0.80  # statistiche: un canto e' "valido" da questa affidabilita' in su

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
        "umidita": "REAL",       # umidita' relativa % (scheda ambientale)
        "modello": "TEXT",       # versione del modello di riconoscimento sulla XIAO
        "campione": "INTEGER",   # 1 = campione di controllo casuale sotto la soglia di salvataggio
    }
    for nome, tipo in nuove.items():
        if nome not in colonne:
            cur.execute(f"ALTER TABLE rilevamenti_bioacustici ADD COLUMN {nome} {tipo}")
    # audio_url = indirizzo pubblico su archive.org. I vecchi valori "audio/..." di prova non puntano a file reali.
    cur.execute("UPDATE rilevamenti_bioacustici SET audio_url=NULL WHERE audio_url NOT LIKE 'http%'")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON rilevamenti_bioacustici(timestamp)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_nodo ON rilevamenti_bioacustici(nodo)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_specie ON rilevamenti_bioacustici(specie_ita)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS telemetria (
            timestamp TEXT NOT NULL,
            nodo TEXT NOT NULL,
            batteria_perc INTEGER,
            batteria_mv INTEGER,
            temperatura REAL,
            pressione REAL,
            umidita REAL,
            UNIQUE(timestamp, nodo)
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS verifiche (
            id_rilevamento TEXT NOT NULL,     -- come chiave_record(): 20261105-064512-TORRE-FLAVIA-01-ERIRUB
            revisore TEXT NOT NULL,           -- nome pubblico, oppure "revisore anonimo #xxxx" senza consenso
            ente TEXT,
            citato INTEGER,                   -- 1 = ha dato il consenso a comparire sul sito
            esito TEXT NOT NULL,              -- ok | errato | dubbio
            specie_corretta TEXT,
            note TEXT,
            file TEXT,
            importato TEXT,
            UNIQUE(id_rilevamento, revisore)
        )""")
    col_tel = {r[1] for r in cur.execute("PRAGMA table_info(telemetria)")}
    for nome, tipo in {"ascolto_oggi_min": "INTEGER", "ascolto_ieri_min": "INTEGER", "modello": "TEXT"}.items():
        if nome not in col_tel:
            cur.execute(f"ALTER TABLE telemetria ADD COLUMN {nome} {tipo}")
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
                 temperatura, pressione, umidita, gps_lat, gps_lon, altitudine_mslm, file_audio, modello, campione)
                VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ts, nodo, specie, row.get("specie_sci", ""), numero(row.get("score_tinyml")) or 0.0,
                 numero(row.get("batteria_perc"), int), numero(row.get("temperatura")),
                 numero(row.get("pressione")), numero(row.get("umidita")), numero(row.get("gps_lat")),
                 numero(row.get("gps_lon")), numero(row.get("altitudine_mslm")), row.get("file_audio") or None,
                 row.get("modello") or None, 1 if row.get("campione") == "1" else None))
            nuovi += 1
            print(f"    + {ts}  {nodo}  {specie}")
    conn.commit()
    print(f"[OK] Log: {nuovi} rilevamenti nuovi" + (f", {scartati} righe scartate" if scartati else ""))
    return nuovi


def importa_telemetria(conn):
    """Telemetria dei risvegli (batteria, temperatura, pressione, umidita') da telemetria.csv."""
    if not os.path.exists(CSV_TELEMETRIA):
        return 0
    cur = conn.cursor()
    nuovi = 0
    with open(CSV_TELEMETRIA, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            ts, nodo = (row.get("timestamp") or "").strip(), (row.get("nodo") or "").strip()
            try:
                datetime.strptime(ts, FORMATO_TS)
            except ValueError:
                continue
            cur.execute("""INSERT OR IGNORE INTO telemetria
                (timestamp, nodo, batteria_perc, batteria_mv, temperatura, pressione, umidita,
                 ascolto_oggi_min, ascolto_ieri_min, modello)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ts, nodo, numero(row.get("batteria_perc"), int), numero(row.get("batteria_mv"), int),
                 numero(row.get("temperatura")), numero(row.get("pressione")), numero(row.get("umidita")),
                 numero(row.get("ascolto_oggi_min"), int), numero(row.get("ascolto_ieri_min"), int),
                 (row.get("modello") or "").strip() or None))
            nuovi += cur.rowcount
    conn.commit()
    print(f"[OK] Telemetria: {nuovi} misure nuove")
    return nuovi


# ---------------------------------------------------------------- audio
_CODICI = None


def codice_specie(sci, nome=""):
    """Codice di 6 lettere della specie (da raspberry/specie.csv), oppure il nome ripulito."""
    global _CODICI
    if _CODICI is None:
        _CODICI = {}
        if os.path.exists(TAB_SPECIE):
            with open(TAB_SPECIE, newline="", encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    _CODICI[r["nome_sci"].strip().lower()] = r["codice"].strip().upper()
    return _CODICI.get((sci or "").strip().lower()) or re.sub(r"[^A-Za-z0-9]+", "", (nome or sci or "X")).upper()[:10]


def chiave_record(ts, nodo, sci="", specie=""):
    """Identificativo stabile del rilevamento, usato nei link e nelle verifiche.
    Comprende la specie, perche' piu' specie possono essere riconosciute nello stesso istante e nello stesso file."""
    dt = datetime.strptime(ts, FORMATO_TS)
    nodo_pulito = re.sub(r"[^A-Za-z0-9]+", "-", nodo).strip("-")
    return f"{dt:%Y%m%d-%H%M%S}-{nodo_pulito}-{codice_specie(sci, specie)}"


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
    per_nome = {}
    for r in righe:
        if r[3]:
            per_nome.setdefault(r[3].lower(), []).append(r)

    associati, orfani = 0, []
    for nome in sorted(wav):
        gruppo = per_nome.get(nome.lower())
        if not gruppo:  # nessun nome esplicito nel log: cerco il timestamp nel nome del file
            candidati = [r for r in righe if any(v in nome for v in varianti_timestamp(r[1]))]
            if len({r[2] for r in candidati}) > 1:  # stesso istante su piu' nodi: uso il nodo nel nome del file
                candidati = [r for r in candidati if r[2].lower() in nome.lower()] or candidati
            gruppo = candidati
        if not gruppo:
            orfani.append(nome)
            continue
        # un file puo' contenere piu' specie: tutti i rilevamenti del gruppo puntano allo stesso .wav
        ts = min(r[1] for r in gruppo)
        dt = datetime.strptime(ts, FORMATO_TS)
        rel = f"audio/{dt:%Y}/{dt:%m}/{os.path.splitext(nome)[0]}.wav"
        dest = os.path.join(CARTELLA, *rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        sorgente = os.path.join(CARTELLA_IMPORT, nome)
        durata = durata_wav(sorgente)
        if durata is not None and durata > DURATA_MAX + 0.5:
            print(f"    [!] {nome} dura {durata:.1f} s (previsti al massimo {DURATA_MAX} s): nel 3D si vedranno gli ultimi {DURATA_MAX} s")
        shutil.copy2(sorgente, dest)
        os.makedirs(CARTELLA_IMPORTATI, exist_ok=True)
        shutil.move(sorgente, os.path.join(CARTELLA_IMPORTATI, nome))
        for r in gruppo:
            cur.execute("UPDATE rilevamenti_bioacustici SET audio_locale=? WHERE id=?", (rel, r[0]))
        associati += 1
        print(f"    ♪ {nome}  ->  {rel}" + (f"  ({len(gruppo)} specie)" if len(gruppo) > 1 else ""))
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
        "contact": "info@birdsongtech.it",
    }
    return md


def carica_su_archive(conn):
    """Carica su archive.org i .wav dell'archivio locale non ancora pubblicati."""
    if MODO_LOCALE or not ARCHIVE_ATTIVO:
        return 0
    cur = conn.cursor()
    cur.execute("""SELECT MIN(id), MIN(timestamp), audio_locale FROM rilevamenti_bioacustici
                   WHERE audio_locale IS NOT NULL AND audio_url IS NULL GROUP BY audio_locale ORDER BY MIN(timestamp)""")
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
        cur.execute("UPDATE rilevamenti_bioacustici SET audio_url=? WHERE audio_locale=?", (url, locale))
        conn.commit()
        caricati += 1
        print(f"    ↑ {nome}  ->  archive.org/details/{item}")
    print(f"[OK] Internet Archive: {caricati} di {len(da_caricare)} file caricati"
          + ("" if caricati == len(da_caricare) else " (gli altri verranno ritentati al prossimo avvio)"))
    print("     Nota: archive.org puo' impiegare qualche minuto prima di rendere ascoltabili i file nuovi.")
    return caricati


# ---------------------------------------------------------------- schede delle specie
TAB_SPECIE = os.path.join(CARTELLA, "raspberry", "specie.csv")
CREDITI_FOTO = os.path.join(CARTELLA, "assets", "specie", "crediti.json")


def testo_presenza(codici):
    """'M reg, W, S, B' -> 'sedentaria, nidificante, svernante, di passo regolare'"""
    parole = []
    for c in [x.strip() for x in (codici or "").split(",") if x.strip()]:
        dubbio = c.endswith("?")
        irr = c.endswith(" irr")
        base = c.rstrip("?").replace(" irr", "").strip()
        nome = {"S": "sedentaria", "B": "nidificante", "W": "svernante",
                "M reg": "di passo regolare", "M": "di passo"}.get(base)
        if not nome:
            continue
        if irr:
            nome += " (irregolare)"
        if dubbio:
            nome += " (da confermare)"
        parole.append(nome)
    ordine = ["sedentaria", "nidificante", "svernante", "di passo"]
    parole.sort(key=lambda t: next((i for i, o in enumerate(ordine) if t.startswith(o)), 9))
    return ", ".join(parole)


def schede_specie():
    """Dati per specie (chiave: nome scientifico minuscolo): foto, crediti, presenza a Torre Flavia."""
    if not os.path.exists(TAB_SPECIE):
        return {}
    crediti = {}
    if os.path.exists(CREDITI_FOTO):
        with open(CREDITI_FOTO, encoding="utf-8") as f:
            crediti = json.load(f)
    schede = {}
    with open(TAB_SPECIE, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            cod = r["codice"].strip().upper()
            foto = f"assets/specie/{cod}.jpg"
            c = crediti.get(cod)
            schede[r["nome_sci"].strip().lower()] = {
                "codice": cod,
                "nome": r["nome_ita"].strip(),
                "presenza": testo_presenza(r.get("presenza")),
                "foto": foto if c and os.path.exists(os.path.join(CARTELLA, *foto.split("/"))) else None,
                "credito": {k: c.get(k) for k in ("autore", "licenza", "url_licenza", "pagina")} if c else None,
            }
    return schede


# ---------------------------------------------------------------- statistiche giornaliere
def punto_rugiada(t, u):
    """Punto di rugiada in °C (formula di Magnus) da temperatura °C e umidita' relativa %."""
    import math
    if t is None or not u or u <= 0:
        return None
    a, b = 17.62, 243.12
    g = math.log(min(u, 100) / 100) + a * t / (b + t)
    return b * g / (a - g)


def esporta_statistiche(conn):
    """data/statistiche.js: per ogni giorno canti validi, meteo, punto di rugiada e batteria."""
    giorni = {}

    def giorno(d):
        return giorni.setdefault(d, {"canti": 0, "t": [], "u": [], "p": [], "r": [], "b": []})

    cur = conn.cursor()
    misure = list(cur.execute("SELECT timestamp, batteria_perc, temperatura, pressione, umidita FROM telemetria"))
    misure += list(cur.execute("""SELECT timestamp, batteria_perc, temperatura, pressione, umidita
                                  FROM rilevamenti_bioacustici"""))
    for ts, bat, t, p, u in misure:
        g = giorno(ts[:10])
        if t is not None: g["t"].append(t)
        if u is not None: g["u"].append(u)
        if p is not None: g["p"].append(p)
        if bat is not None: g["b"].append((ts, bat))
        r = punto_rugiada(t, u)
        if r is not None: g["r"].append(r)
    # minuti di ascolto: il massimo fra i valori "oggi" del giorno e il totale "ieri" mandato il giorno dopo
    ascolto = {}
    for ts, oggi, ieri in cur.execute("SELECT timestamp, ascolto_oggi_min, ascolto_ieri_min FROM telemetria"):
        d = ts[:10]
        if oggi is not None:
            ascolto[d] = max(ascolto.get(d, 0), oggi)
        if ieri is not None:
            prima = (datetime.strptime(d, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            ascolto[prima] = max(ascolto.get(prima, 0), ieri)
    for d in ascolto:
        giorno(d)
    for ts, score, campione in cur.execute("SELECT timestamp, score_tinyml, campione FROM rilevamenti_bioacustici"):
        if (score or 0) >= SOGLIA_VALIDI - 1e-9 and not campione:   # i campioni di controllo non contano
            giorno(ts[:10])["canti"] += 1

    media = lambda v: round(sum(v) / len(v), 1) if v else None
    uscita = {}
    for d, g in sorted(giorni.items()):
        b = [x[1] for x in sorted(g["b"])]
        uscita[d] = {
            "canti": g["canti"],
            "t_min": min(g["t"]) if g["t"] else None, "t_med": media(g["t"]), "t_max": max(g["t"]) if g["t"] else None,
            "u_min": min(g["u"]) if g["u"] else None, "u_med": media(g["u"]), "u_max": max(g["u"]) if g["u"] else None,
            "p_med": media(g["p"]),
            "r_med": media(g["r"]),
            "b_min": min(b) if b else None, "b_max": max(b) if b else None, "b_ult": b[-1] if b else None,
            "ascolto_min": min(ascolto[d], 1440) if d in ascolto else None,
            "canti_ora": round(g["canti"] / (ascolto[d] / 60), 2) if ascolto.get(d) else None,
        }
    pacchetto = {"aggiornato": datetime.now().strftime(FORMATO_TS), "soglia": SOGLIA_VALIDI, "giorni": uscita}
    testo = json.dumps(pacchetto, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(CARTELLA_DATI, "statistiche.js"), "w", encoding="utf-8") as f:
        f.write("window.BIRDSONG_STAT = " + testo + ";\n")
    print(f"[OK] Statistiche: {len(uscita)} giorni")



# ---------------------------------------------------------------- verifiche degli esperti
COLONNE_LOTTO = ["id", "data", "ora", "specie", "nome_scientifico", "affidabilita", "motivo", "altre_specie_nel_file",
                 "ascolta_audio", "ascolta_3d",
                 "verifica", "specie_corretta", "note", "revisore", "ente", "citami"]


def _norm(t):
    import unicodedata
    t = unicodedata.normalize("NFD", str(t or "")).encode("ascii", "ignore").decode()
    return t.strip().lower()


def esito_da_testo(t):
    """Accetta le risposte in tutti i modi ragionevoli: ✔ si ok corretto v 1 / ✘ no errato sbagliato x 0 / ? dubbio."""
    raw = str(t or "").strip()
    if raw in ("✔", "✓", "☑"):
        return "ok"
    if raw in ("✘", "✗", "×"):
        return "errato"
    n = _norm(raw)
    if n in ("si", "s", "ok", "corretto", "corretta", "giusto", "giusta", "v", "1", "y", "yes", "true", "vero"):
        return "ok"
    if n in ("no", "n", "errato", "errata", "sbagliato", "sbagliata", "x", "0", "false", "falso"):
        return "errato"
    if n in ("?", "dubbio", "non so", "nonso", "incerto", "incerta", "forse"):
        return "dubbio"
    return None


def _righe_file(percorso):
    """Righe di un file di verifica: CSV (separato da ; o ,) oppure .xlsx salvato da Excel."""
    if percorso.lower().endswith(".xlsx"):
        try:
            from openpyxl import load_workbook
        except ImportError:
            print(f"    [!] {os.path.basename(percorso)}: per i file .xlsx serve 'pip install openpyxl' (oppure salvalo come CSV)")
            return []
        ws = load_workbook(percorso, read_only=True, data_only=True).active
        righe = list(ws.iter_rows(values_only=True))
        if not righe:
            return []
        testa = [str(c or "").strip() for c in righe[0]]
        return [dict(zip(testa, ["" if v is None else str(v) for v in r])) for r in righe[1:]]
    with open(percorso, newline="", encoding="utf-8-sig", errors="replace") as f:
        testo = f.read()
    sep = ";" if testo.split("\n", 1)[0].count(";") >= testo.split("\n", 1)[0].count(",") else ","
    return list(csv.DictReader(testo.splitlines(), delimiter=sep))


def importa_verifiche(conn):
    """Legge i file restituiti dai revisori (cartella verifiche/) e li salva nel database.
    Rileggere lo stesso file non crea doppioni: la verifica di un revisore su un canto si aggiorna."""
    if not os.path.isdir(CARTELLA_VERIFICHE):
        os.makedirs(CARTELLA_VERIFICHE, exist_ok=True)
        return 0
    import hashlib
    cur = conn.cursor()
    esistenti = {chiave_record(ts, nodo, sci, sp) for ts, nodo, sp, sci in
                 cur.execute("SELECT timestamp, nodo, specie_ita, specie_sci FROM rilevamenti_bioacustici")}
    nuove = 0
    for nome in sorted(os.listdir(CARTELLA_VERIFICHE)):
        if not nome.lower().endswith((".csv", ".xlsx")) or nome.startswith("~$"):
            continue
        percorso = os.path.join(CARTELLA_VERIFICHE, nome)
        lette = scartate = 0
        for r in _righe_file(percorso):
            r = {_norm(k): (v or "").strip() for k, v in r.items() if k}
            esito = esito_da_testo(r.get("verifica"))
            idr = r.get("id", "")
            if not esito:
                continue                                   # riga non compilata: si salta senza avvisi
            if idr not in esistenti:
                scartate += 1
                continue
            nome_rev = r.get("revisore") or f"revisore del file {nome}"
            citato = _norm(r.get("citami")) in ("si", "s", "yes", "y", "1", "x", "ok", "✔")
            if not citato:   # senza consenso il nome non entra nel database (che e' pubblico su GitHub)
                nome_rev = "revisore anonimo #" + hashlib.sha1(_norm(nome_rev).encode()).hexdigest()[:4]
            cur.execute("""INSERT INTO verifiche (id_rilevamento, revisore, ente, citato, esito, specie_corretta, note, file, importato)
                           VALUES (?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(id_rilevamento, revisore) DO UPDATE SET
                           ente=excluded.ente, citato=excluded.citato, esito=excluded.esito,
                           specie_corretta=excluded.specie_corretta, note=excluded.note, file=excluded.file""",
                        (idr, nome_rev, (r.get("ente") or None) if citato else None, 1 if citato else 0, esito,
                         r.get("specie_corretta") or None, r.get("note") or None, nome if citato else None,
                         datetime.now().strftime(FORMATO_TS)))
            lette += 1
        if lette or scartate:
            print(f"    {nome}: {lette} verifiche" + (f", {scartate} righe con id sconosciuto" if scartate else ""))
        nuove += lette
    conn.commit()
    print(f"[OK] Verifiche: {nuove} righe lette da verifiche/")
    return nuove


def stato_verifiche(conn):
    """id_rilevamento -> {stato, ok, errato, dubbio, revisori, specie_corretta}.
    stato: confermato (maggioranza ok), errato (maggioranza errato), controverso (pari), dubbio (solo '?')."""
    voti = {}
    for idr, rev, ente, citato, esito, corr in conn.execute(
            "SELECT id_rilevamento, revisore, ente, citato, esito, specie_corretta FROM verifiche"):
        v = voti.setdefault(idr, {"ok": 0, "errato": 0, "dubbio": 0, "revisori": [], "specie_corretta": []})
        v[esito] += 1
        if citato:
            v["revisori"].append(rev + (f" ({ente})" if ente else ""))
        if corr:
            v["specie_corretta"].append(corr)
    for v in voti.values():
        v["stato"] = ("confermato" if v["ok"] > v["errato"] else "errato" if v["errato"] > v["ok"]
                      else "controverso" if v["ok"] else "dubbio")
        v["specie_corretta"] = max(set(v["specie_corretta"]), key=v["specie_corretta"].count) if v["specie_corretta"] else None
    return voti


def elenco_revisori(conn):
    """Revisori che hanno dato il consenso, con il numero di canti verificati; piu' il numero degli anonimi."""
    citati = [{"nome": n, "ente": e, "canti": c} for n, e, c in conn.execute(
        """SELECT revisore, MAX(ente), COUNT(*) FROM verifiche WHERE citato=1 GROUP BY revisore ORDER BY COUNT(*) DESC, revisore""")]
    anonimi = conn.execute("SELECT COUNT(DISTINCT revisore) FROM verifiche WHERE citato=0").fetchone()[0]
    return {"citati": citati, "anonimi": anonimi}


def crea_lotto(conn, quanti):
    """Crea lotti/lotto_AAAAMMGG_hhmm.csv con i canti piu' utili da verificare (con audio pubblicato).
    Priorita': campioni di controllo, specie fuori checklist, specie rare, fascia 80-90%, poi gli altri.
    Esclude i canti gia' verificati da almeno 2 revisori."""
    import random
    checklist = schede_specie()
    voti = stato_verifiche(conn)
    righe = list(conn.execute("""SELECT timestamp, nodo, specie_ita, specie_sci, score_tinyml, audio_url, campione
                                 FROM rilevamenti_bioacustici WHERE audio_url LIKE 'http%'"""))
    per_file = {}
    for r in righe:
        per_file.setdefault(r[5], []).append(r[2])
    conta = {}
    for r in righe:
        conta[r[2]] = conta.get(r[2], 0) + 1
    candidati = []
    for ts, nodo, sp, sci, score, url, camp in righe:
        idr = chiave_record(ts, nodo, sci, sp)
        gia = voti.get(idr, {})
        if gia.get("ok", 0) + gia.get("errato", 0) >= 2:
            continue
        if camp:
            prio, motivo = 0, "campione di controllo"
        elif (sci or "").strip().lower() not in checklist:
            prio, motivo = 1, "fuori checklist"
        elif conta[sp] <= 3:
            prio, motivo = 2, "specie rara nell'archivio"
        elif (score or 0) < 0.90:
            prio, motivo = 3, "affidabilita' 80-90%"
        else:
            prio, motivo = 4, "controllo a campione"
        if gia:
            prio += 0.5                                     # gia' verificato da un revisore: dopo gli altri
        altre = ", ".join(sorted(set(x for x in per_file.get(url, []) if x != sp)))
        candidati.append((prio, random.random(), idr, ts, sp, sci, score, url, motivo, altre))
    if not candidati:
        print("[!] Nessun canto con audio pubblicato da verificare.")
        return None
    candidati.sort()
    scelti = sorted(candidati[:quanti], key=lambda c: c[3])
    base = f"lotto_{datetime.now():%Y%m%d_%H%M}"
    cartella = os.path.join(CARTELLA_LOTTI, base)
    os.makedirs(cartella, exist_ok=True)
    nome = os.path.join(cartella, base + ".csv")
    with open(nome, "w", newline="", encoding="utf-8-sig") as f:   # ; e BOM: si apre bene con Excel in italiano
        w = csv.writer(f, delimiter=";")
        w.writerow(COLONNE_LOTTO)
        for _, _, idr, ts, sp, sci, score, url, motivo, altre in scelti:
            w.writerow([idr, ts[:10], ts[11:], sp, sci, f"{round((score or 0) * 100)}%", motivo, altre, url,
                        f"{SITO}player.html?id={idr}", "", "", "", "", "", ""])
    n_tab, n_wav = selezioni_raven(conn, cartella, {c[7] for c in scelti})
    with open(os.path.join(cartella, "LEGGIMI.txt"), "w", encoding="utf-8") as f:
        f.write(TESTO_LEGGIMI_LOTTO)
    zip_nome = shutil.make_archive(os.path.join(CARTELLA_LOTTI, base), "zip", cartella)
    print(f"[OK] Lotto creato: {zip_nome}")
    print(f"     {len(scelti)} canti, {n_tab} tabelle di selezione Raven" + (f", {n_wav} file audio inclusi" if n_wav else ", audio da scaricare dai link"))
    print("     Allega il file .zip alla risposta: il testo da usare e' in docs/VERIFICHE.md")
    return zip_nome


FINESTRA_MODELLO = 3.0      # secondi analizzati dal modello per ogni rilevamento (riquadro nelle tabelle Raven)
LIMITE_ZIP_MB = 20          # oltre questa dimensione i .wav non vengono messi nel lotto (limite degli allegati email)
TESTO_LEGGIMI_LOTTO = """birdsongtech - lotto di canti da verificare
Monumento Naturale Palude di Torre Flavia

Contenuto:
- lotto_....csv            i canti da verificare: si apre con Excel o LibreOffice
- selezioni_raven/         una tabella di selezione per ogni file audio, nel formato di Raven
                           (K. Lisa Yang Center for Conservation Bioacoustics, Cornell Lab of Ornithology)
- audio/                   i file .wav, se ci stavano nell'allegato (altrimenti si scaricano dai link del CSV)

Con Raven: aprire il file .wav e poi la tabella con lo stesso nome (File > Open Selection Table).
I riquadri mostrano dove il modello ha riconosciuto ogni specie (finestra di 3 secondi).

Per ogni riga del CSV scrivere in "verifica": si / no / ?   (istruzioni complete nella email)
Grazie!
"""


def selezioni_raven(conn, cartella, url_scelti):
    """Per ogni file audio del lotto scrive <nome>.Table.1.selections.txt (formato Raven, separato da tabulazioni)
    con tutti i rilevamenti del file; se lo spazio basta copia anche i .wav dall'archivio locale."""
    righe = list(conn.execute("""SELECT timestamp, nodo, specie_ita, specie_sci, score_tinyml, audio_url, audio_locale, file_audio
                                 FROM rilevamenti_bioacustici WHERE audio_url IS NOT NULL ORDER BY timestamp"""))
    per_url = {}
    for r in righe:
        if r[5] in url_scelti:
            per_url.setdefault(r[5], []).append(r)
    dir_sel = os.path.join(cartella, "selezioni_raven")
    os.makedirs(dir_sel, exist_ok=True)
    wav_da_copiare = []
    for url, gruppo in per_url.items():
        nome_wav = gruppo[0][7] or os.path.basename(url)
        base = os.path.splitext(nome_wav)[0]
        m = re.search(r"(\d{8})_(\d{6})", nome_wav)
        inizio = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S") if m else datetime.strptime(gruppo[0][0], FORMATO_TS)
        with open(os.path.join(dir_sel, f"{base}.Table.1.selections.txt"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["Selection", "View", "Channel", "Begin Time (s)", "End Time (s)", "Low Freq (Hz)", "High Freq (Hz)",
                        "Specie", "Nome scientifico", "Affidabilita (%)", "ID"])
            for k, (ts, nodo, sp, sci, score, _, _, _) in enumerate(gruppo, start=1):
                t0 = max(0.0, (datetime.strptime(ts, FORMATO_TS) - inizio).total_seconds())
                t1 = min(t0 + FINESTRA_MODELLO, DURATA_MAX)
                w.writerow([k, "Spectrogram 1", 1, f"{t0:.3f}", f"{t1:.3f}", 0, 16000, sp, sci,
                            round((score or 0) * 100), chiave_record(ts, nodo, sci, sp)])
        locale = gruppo[0][6]
        if locale and os.path.exists(os.path.join(CARTELLA, *locale.split("/"))):
            wav_da_copiare.append((os.path.join(CARTELLA, *locale.split("/")), nome_wav))
    n_wav = 0
    totale = sum(os.path.getsize(p) for p, _ in wav_da_copiare)
    if wav_da_copiare and totale <= LIMITE_ZIP_MB * 1024 * 1024:
        os.makedirs(os.path.join(cartella, "audio"), exist_ok=True)
        for p, nome_wav in wav_da_copiare:
            shutil.copy2(p, os.path.join(cartella, "audio", nome_wav))
            n_wav += 1
    elif wav_da_copiare:
        print(f"     [i] audio non inclusi: {totale / 1048576:.0f} MB superano il limite di {LIMITE_ZIP_MB} MB "
              f"(riduci QUANTI in crea_lotto.bat oppure il revisore li scarica dai link)")
    return len(per_url), n_wav


# ---------------------------------------------------------------- export per il sito
def esporta_dati(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp, nodo, specie_ita, specie_sci, score_tinyml, audio_url, audio_locale, batteria_perc,
               temperatura, pressione, gps_lat, gps_lon, altitudine_mslm, modello, campione, file_audio
        FROM rilevamenti_bioacustici ORDER BY timestamp DESC""")
    rilevamenti, nodi, in_attesa = [], {}, 0
    voti = stato_verifiche(conn)
    for (ts, nodo, specie, sci, score, url, locale, bat, temp, pres, lat, lon, alt, modello, campione, file_wav) in cur.fetchall():
        if MODO_LOCALE:  # prova sul PC: file della cartella audio/
            audio = locale if locale and os.path.exists(os.path.join(CARTELLA, *locale.split("/"))) else None
        else:            # sito pubblico: solo i file gia' su archive.org
            audio = url
        if not audio and ts not in DIMOSTRATIVI:   # i canti veri compaiono solo con l'audio gia' pubblicato
            in_attesa += 1
            continue
        data, ora = ts.split(" ")
        rilevamenti.append({
            "id": chiave_record(ts, nodo, sci, specie), "data": data, "ora": ora, "nodo": nodo,
            "file": file_wav or locale or url,
            "specie": specie, "sci": sci, "score": round(score, 3), "audio": audio,
            "batteria": bat, "temperatura": temp, "pressione": pres,
            "lat": lat, "lon": lon, "quota": alt,
            "modello": modello, "campione": bool(campione),
        })
        v = voti.get(rilevamenti[-1]["id"])
        if v:
            rilevamenti[-1]["verifica"] = {"stato": v["stato"], "ok": v["ok"], "errato": v["errato"], "dubbio": v["dubbio"],
                                           "revisori": v["revisori"], "specie_corretta": v["specie_corretta"]}
        n = nodi.setdefault(nodo, {"nodo": nodo, "rilevamenti": 0, "ultimo": ts, "ultima_specie": specie,
                                   "batteria": bat, "lat": None, "lon": None, "quota": alt})
        n["rilevamenti"] += 1
        if n["lat"] is None and lat is not None and lon is not None:
            n["lat"], n["lon"] = lat, lon

    # piu' specie nello stesso file audio: ogni rilevamento elenca le altre
    gruppi = {}
    for r in rilevamenti:
        if r["file"]:
            gruppi.setdefault((r["nodo"], r["file"]), []).append(r)
    for r in rilevamenti:
        altri = [x for x in gruppi.get((r["nodo"], r["file"]), []) if x is not r]
        if altri:
            r["stesso_file"] = [{"id": x["id"], "specie": x["specie"], "ora": x["ora"]} for x in sorted(altri, key=lambda x: x["ora"])]

    for n in nodi.values():
        if n["lat"] is None:
            n["lat"], n["lon"] = STAZIONE_DEFAULT["lat"], STAZIONE_DEFAULT["lon"]

    pacchetto = {
        "aggiornato": datetime.now().strftime(FORMATO_TS),
        "stazione": STAZIONE_DEFAULT,
        "nodi": sorted(nodi.values(), key=lambda n: n["nodo"]),
        "specie": schede_specie(),
        "revisori": elenco_revisori(conn),
        "rilevamenti": rilevamenti,
    }
    os.makedirs(CARTELLA_DATI, exist_ok=True)
    testo = json.dumps(pacchetto, ensure_ascii=False, indent=1)
    with open(os.path.join(CARTELLA_DATI, "rilevamenti.json"), "w", encoding="utf-8") as f:
        f.write(testo)
    # versione .js: permette di aprire il sito anche con doppio clic, senza server
    with open(os.path.join(CARTELLA_DATI, "rilevamenti.js"), "w", encoding="utf-8") as f:
        f.write("window.BIRDSONG = " + testo + ";\n")
    print(f"[OK] Sito: {len(rilevamenti)} canti pubblicati"
          + (f", {in_attesa} in attesa del file audio (compariranno dopo lo scarico dalla XIAO)" if in_attesa else "")
          + ("  [MODO LOCALE: non fare il push di questi dati]" if MODO_LOCALE else ""))


# ---------------------------------------------------------------- copia di sicurezza sul Raspberry
def _ssh(argomenti, timeout=60):
    import subprocess
    opz = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=6"]   # niente richiesta di password: senza chiave SSH si salta
    try:
        r = subprocess.run(argomenti[:1] + opz + argomenti[1:], capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def backup_raspberry():
    """Copia sulla scheda SD del Raspberry i file che esistono solo sul PC.
    Gli audio si copiano una volta sola (solo quelli nuovi); database, CSV e documenti si riscrivono ogni volta.
    Richiede l'accesso SSH con chiave (raspberry/LEGGIMI.md): senza, la copia viene saltata con un avviso."""
    if not BACKUP_PI or MODO_LOCALE:
        return 0
    dest = BACKUP_PI_CARTELLA.rstrip("/")
    codice, uscita, errore = _ssh(["ssh", BACKUP_PI_HOST,
        f"mkdir -p {dest} && cd {dest} && find . -type f -printf '%P\\t%s\\t%T@\\n'; echo ---; df -k {dest} | tail -1"])
    if codice != 0:
        print("[!] Copia sul Raspberry saltata: Pi non raggiungibile o accesso SSH senza chiave "
              "(vedi raspberry/LEGGIMI.md, 'Scaricare il log senza password').")
        return 0
    elenco, _, spazio = uscita.partition("---")
    remoti = {}
    for riga in elenco.strip().splitlines():
        campi = riga.split("\t")
        if len(campi) >= 3:
            try:
                remoti[campi[0]] = (int(campi[1]), float(campi[2]))
            except ValueError:
                pass

    da_copiare = []      # (percorso locale, percorso relativo con /)
    for c in BACKUP_CARTELLE:
        radice = os.path.join(CARTELLA, c)
        for su, _, files in os.walk(radice):
            for f in files:
                if f.startswith("~$"):
                    continue
                p = os.path.join(su, f)
                rel = os.path.relpath(p, CARTELLA).replace(os.sep, "/")
                r = remoti.get(rel)
                if r and r[0] == os.path.getsize(p) and (c == "audio" or abs(r[1] - os.path.getmtime(p)) < 2):
                    continue                                 # gia' presente e invariato (gli audio non cambiano mai)
                da_copiare.append((p, rel))
    for f in BACKUP_FILE:
        p = os.path.join(CARTELLA, f)
        if os.path.exists(p):
            da_copiare.append((p, f))
    if not da_copiare:
        print("[OK] Copia sul Raspberry: niente di nuovo")
        return 0

    # crea le cartelle remote e copia a gruppi (un scp per cartella, al massimo 40 file per volta)
    cartelle = sorted({os.path.dirname(rel) for _, rel in da_copiare if os.path.dirname(rel)})
    if cartelle:
        _ssh(["ssh", BACKUP_PI_HOST, "mkdir -p " + " ".join(f"'{dest}/{c}'" for c in cartelle)])
    gruppi = {}
    for p, rel in da_copiare:
        gruppi.setdefault(os.path.dirname(rel), []).append(p)
    copiati = falliti = 0
    for cart, files in gruppi.items():
        for i in range(0, len(files), 40):
            pezzo = files[i:i + 40]
            destinazione = f"{BACKUP_PI_HOST}:{dest}/{cart}/" if cart else f"{BACKUP_PI_HOST}:{dest}/"
            codice, _, errore = _ssh(["scp", "-q", "-p"] + pezzo + [destinazione], timeout=600)
            if codice == 0:
                copiati += len(pezzo)
            else:
                falliti += len(pezzo)
                print(f"    [!] copia non riuscita in {cart or '/'}: {errore.strip()[:120]}")
    libero = ""
    campi = spazio.split()
    if len(campi) >= 4 and campi[3].isdigit():
        gb = int(campi[3]) / 1048576
        libero = f", spazio libero sulla SD {gb:.1f} GB"
        if gb < 2:
            libero += "  [!] POCO SPAZIO: valuta una scheda piu' grande o un disco USB"
    print(f"[OK] Copia sul Raspberry: {copiati} file copiati in {BACKUP_PI_HOST}:{dest}"
          + (f", {falliti} non riusciti (riprovo al prossimo avvio)" if falliti else "") + libero)
    return copiati


if __name__ == "__main__":
    conn = apri_database()
    if "--lotto" in sys.argv:          # python pubblica.py --lotto 20   -> crea un file da spedire a un revisore
        i = sys.argv.index("--lotto")
        quanti = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 and sys.argv[i + 1].isdigit() else 20
        try:
            importa_verifiche(conn)
            crea_lotto(conn, quanti)
        finally:
            conn.close()
        sys.exit(0)
    try:
        importa_log(conn)
        importa_telemetria(conn)
        importa_audio(conn)
        importa_verifiche(conn)
        carica_su_archive(conn)
        esporta_dati(conn)
        esporta_statistiche(conn)
    finally:
        conn.close()
    backup_raspberry()
