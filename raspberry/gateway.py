# -*- coding: utf-8 -*-
"""
birdsongtech - gateway LoRa della stazione base (Raspberry Pi 3 + Heltec V3 su USB).

Riceve dalla stazione in campo i messaggi del protocollo BS1 (vedi docs/PROTOCOLLO_LORA.md):
  - "BS1 H ..."  risveglio della stazione  -> risponde con l'ora esatta ("BS1 T ...")
                  e registra la telemetria (batteria, temperatura, pressione, umidita') in telemetria.csv
  - "BS1 D ..."  rilevamenti               -> li scrive in birdsong_log.csv e conferma ("BS1 A ...")
Tutti i messaggi di testo, anche quelli non BS1, finiscono nel log grezzo letto dal display LCD.

Avvio manuale:   ~/mesh_env/bin/python gateway.py
Avvio automatico: servizio systemd birdsong.service (vedi raspberry/LEGGIMI.md)
"""
import csv
import os
import threading
import time
from datetime import datetime

# ---------------------------------------------------------------- configurazione
CARTELLA = os.path.dirname(os.path.abspath(__file__))
PORTA = "/dev/ttyUSB0"                      # porta USB della Heltec V3 (None = ricerca automatica)
CANALE = 0                                  # indice del canale birdsongtech (primario)
LOG_RILEVAMENTI = os.path.join(CARTELLA, "birdsong_log.csv")   # quello che scarica aggiorna_birdsong.bat
LOG_GREZZO = os.path.join(CARTELLA, "log sistema di ascolto Birdsong Palude Torre Flavia.csv")
LOG_TELEMETRIA = os.path.join(CARTELLA, "telemetria.csv")                # anche questo lo scarica aggiorna_birdsong.bat
TAB_SPECIE = os.path.join(CARTELLA, "specie.csv")
TAB_STAZIONI = os.path.join(CARTELLA, "stazioni.csv")
ATTESA_CONFERMA = 8                         # secondi: raccoglie piu' messaggi D in un'unica conferma
MITTENTI_AUTORIZZATI = []                   # es. ["!a1b2c3d4"]; vuoto = tutti quelli del canale privato

COLONNE = ["timestamp", "nodo", "specie_ita", "specie_sci", "score_tinyml", "batteria_perc",
           "temperatura", "pressione", "umidita", "gps_lat", "gps_lon", "altitudine_mslm", "file_audio",
           "modello", "campione"]
COLONNE_TELEMETRIA = ["timestamp", "nodo", "batteria_perc", "batteria_mv", "temperatura", "pressione", "umidita",
                      "ascolto_oggi_min", "ascolto_ieri_min", "modello"]


def dieci(v):
    """'124' -> '12.4' (valori trasmessi moltiplicati per 10); vuoto se manca."""
    v = (v or "").strip()
    return f"{int(v) / 10:.1f}" if v.lstrip("-").isdigit() else ""


def intero(v):
    v = (v or "").strip()
    return v if v.lstrip("-").isdigit() else ""


def scrivi_csv(percorso, colonne, righe):
    """Aggiunge righe a un CSV; se il file ha un'intestazione vecchia (colonne in meno) lo riscrive."""
    esistenti, intestazione = [], None
    if os.path.exists(percorso):
        with open(percorso, newline="", encoding="utf-8") as f:
            lettore = csv.DictReader(f)
            intestazione = lettore.fieldnames
            if intestazione != colonne:
                esistenti = list(lettore)
    if intestazione is not None and intestazione != colonne:
        with open(percorso, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=colonne, extrasaction="ignore")
            w.writeheader()
            w.writerows(esistenti)
        intestazione = colonne
    with open(percorso, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonne, extrasaction="ignore")
        if intestazione is None:
            w.writeheader()
        w.writerows(righe)


def registra(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


# ---------------------------------------------------------------- tabelle
def leggi_tabella(percorso, chiave):
    if not os.path.exists(percorso):
        registra(f"[!] tabella mancante: {percorso}")
        return {}
    with open(percorso, newline="", encoding="utf-8-sig") as f:
        return {r[chiave].strip().upper(): r for r in csv.DictReader(f) if r.get(chiave)}


# ---------------------------------------------------------------- protocollo BS1
class Ricevitore:
    """Logica del protocollo, separata dalla radio (cosi' si puo' provare senza hardware)."""

    def __init__(self, invia):
        self.invia = invia                    # funzione(testo) che trasmette sul canale
        self.specie = leggi_tabella(TAB_SPECIE, "codice")
        self.stazioni = leggi_tabella(TAB_STAZIONI, "sigla")
        self.gia_scritti = self._carica_esistenti()
        self.modello = self._ultimo_modello()  # sigla/nodo -> versione del modello di riconoscimento
        self.da_confermare = {}               # sigla stazione -> set di numeri di sequenza
        self.timer = None
        self.lock = threading.Lock()

    def _carica_esistenti(self):
        visti = set()
        if os.path.exists(LOG_RILEVAMENTI):
            with open(LOG_RILEVAMENTI, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    visti.add((r.get("timestamp"), r.get("nodo"), r.get("specie_ita")))
        return visti

    def _ultimo_modello(self):
        """Ultima versione del modello comunicata da ogni stazione (sopravvive ai riavvii del gateway)."""
        ultimo = {}
        if os.path.exists(LOG_TELEMETRIA):
            with open(LOG_TELEMETRIA, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if (r.get("modello") or "").strip():
                        ultimo[r.get("nodo")] = r["modello"].strip()
        return ultimo

    # ---- ingresso
    def gestisci(self, testo, mittente=""):
        testo = (testo or "").strip()
        if not testo.startswith("BS1 "):
            return False
        if MITTENTI_AUTORIZZATI and mittente not in MITTENTI_AUTORIZZATI:
            registra(f"[!] BS1 da mittente non autorizzato {mittente}: ignorato")
            return True
        parti = testo.split(" ", 4)
        tipo = parti[1] if len(parti) > 1 else ""
        try:
            if tipo == "H":
                self._ciao(parti)
            elif tipo == "D":
                self._dati(parti)
            elif tipo in ("A", "T"):
                pass                          # nostre risposte rimbalzate: niente da fare
            else:
                registra(f"[!] tipo BS1 sconosciuto: {testo}")
        except (ValueError, IndexError) as e:
            registra(f"[!] messaggio BS1 non valido ({e}): {testo}")
        return True

    def _ciao(self, parti):
        # BS1 H <stazione> <batteria%> <mV> <in_coda> [<t×10> <p×10> <umid%> <ascolto_oggi_min> <ascolto_ieri_min> <modello>]
        # un valore mancante in mezzo si scrive "-"
        sigla = parti[2].upper()
        campi = (" ".join(parti[3:]).split() + [""] * 9)[:9]
        bat, mv, coda, t10, p10, umid, asc_oggi, asc_ieri, modello = campi
        modello = "" if modello == "-" else modello
        registra(f"Risveglio di {sigla}: batteria {bat}% ({mv} mV), in coda {coda or 0}"
                 + (f", ascolto oggi {asc_oggi} min" if intero(asc_oggi) else "") + (f", modello {modello}" if modello else ""))
        self.invia(f"BS1 T {sigla} {int(time.time())}")
        stazione = self.stazioni.get(sigla, {})
        nodo = stazione.get("nodo") or sigla
        if modello:
            self.modello[nodo] = modello
        scrivi_csv(LOG_TELEMETRIA, COLONNE_TELEMETRIA, [{
            "timestamp": f"{datetime.now():%Y-%m-%d %H:%M:%S}", "nodo": nodo,
            "batteria_perc": intero(bat), "batteria_mv": intero(mv),
            "temperatura": dieci(t10), "pressione": dieci(p10), "umidita": intero(umid),
            "ascolto_oggi_min": intero(asc_oggi), "ascolto_ieri_min": intero(asc_ieri), "modello": modello,
        }])

    def _dati(self, parti):
        # BS1 D <stazione> <seq> <batteria%> <rec>;<rec>;...
        sigla, seq = parti[2].upper(), int(parti[3])
        resto = parti[4].split(" ", 1)
        batteria = int(resto[0]) if resto[0].lstrip("-").isdigit() else None
        record = resto[1] if len(resto) > 1 else ""
        stazione = self.stazioni.get(sigla, {})
        nuovi = []
        for rec in filter(None, record.split(";")):
            campi = (rec.split(",") + [""] * 7)[:7]
            ts_compatto, codice, conf, temp10, pres10, umid, flag = [c.strip() for c in campi]
            dt = datetime.strptime(ts_compatto, "%Y%m%d%H%M%S")
            sp = self.specie.get(codice.upper())
            if sp is None:
                registra(f"[!] codice specie sconosciuto {codice}: aggiungilo a specie.csv")
            riga = {
                "timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "nodo": stazione.get("nodo") or sigla,
                "specie_ita": sp["nome_ita"] if sp else codice.upper(),
                "specie_sci": sp["nome_sci"] if sp else "",
                "score_tinyml": f"{int(conf) / 100:.2f}" if conf else "",
                "batteria_perc": "" if batteria is None else batteria,
                "temperatura": dieci(temp10),
                "pressione": dieci(pres10),
                "umidita": intero(umid),
                "gps_lat": stazione.get("lat", ""),
                "gps_lon": stazione.get("lon", ""),
                "altitudine_mslm": stazione.get("quota", ""),
                "file_audio": f"{sigla}_{dt:%Y%m%d}_{dt:%H%M%S}.wav",
                "modello": self.modello.get(stazione.get("nodo") or sigla, ""),
                "campione": "1" if flag.lower() == "c" else "",
            }
            chiave = (riga["timestamp"], riga["nodo"], riga["specie_ita"])
            if chiave in self.gia_scritti:
                continue                       # ritrasmissione di un messaggio gia' ricevuto
            self.gia_scritti.add(chiave)
            nuovi.append(riga)
        if nuovi:
            self._scrivi(nuovi)
            registra(f"{sigla} #{seq}: {len(nuovi)} rilevamenti nuovi")
        else:
            registra(f"{sigla} #{seq}: nessun rilevamento nuovo (ritrasmissione)")
        with self.lock:
            self.da_confermare.setdefault(sigla, set()).add(seq)
            if self.timer:
                self.timer.cancel()
            self.timer = threading.Timer(ATTESA_CONFERMA, self.conferma)
            self.timer.daemon = True
            self.timer.start()

    def _scrivi(self, righe):
        scrivi_csv(LOG_RILEVAMENTI, COLONNE, righe)

    # ---- uscita
    def conferma(self):
        with self.lock:
            attese, self.da_confermare, self.timer = self.da_confermare, {}, None
        for sigla, seqs in attese.items():
            # BS1 A <stazione> <ora_unix> <seq>,<seq>,...   (anche l'ora, per tenere allineato l'orologio)
            elenco = ",".join(str(s) for s in sorted(seqs))
            self.invia(f"BS1 A {sigla} {int(time.time())} {elenco}")


# ---------------------------------------------------------------- log grezzo
def scrivi_grezzo(mittente, testo):
    nuovo = not os.path.exists(LOG_GREZZO)
    with open(LOG_GREZZO, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuovo:
            w.writerow(["Data e Ora", "ID Nodo Mittente", "Messaggio Ricevuto", "Stato Bioacustico"])
        w.writerow([f"{datetime.now():%Y-%m-%d %H:%M:%S}", mittente, testo,
                    "SÌ" if testo.startswith("BS1 D") else "NO"])


# ---------------------------------------------------------------- avvio
def main():
    import meshtastic.serial_interface
    from pubsub import pub

    radio = {"if": None}

    def invia(testo):
        registra(f"-> {testo}")
        radio["if"].sendText(testo, channelIndex=CANALE)

    ricevitore = Ricevitore(invia)

    def on_receive(packet, interface):
        dec = packet.get("decoded", {})
        if dec.get("portnum") != "TEXT_MESSAGE_APP":
            return
        testo, mittente = dec.get("text", ""), packet.get("fromId", "")
        registra(f"<- {mittente}: {testo}")
        try:
            scrivi_grezzo(mittente, testo)
        except OSError as e:
            registra(f"[!] log grezzo: {e}")
        if packet.get("channel", 0) == CANALE:
            ricevitore.gestisci(testo, mittente)

    def on_lost(interface=None):
        registra("[!] Collegamento con la Heltec perso: esco, systemd mi riavvia")
        os._exit(1)

    pub.subscribe(on_receive, "meshtastic.receive")
    pub.subscribe(on_lost, "meshtastic.connection.lost")
    registra(f"Connessione alla Heltec su {PORTA or 'porta automatica'}...")
    radio["if"] = meshtastic.serial_interface.SerialInterface(devPath=PORTA)
    registra(f"Gateway in ascolto. Rilevamenti in: {LOG_RILEVAMENTI}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        registra("Chiusura gateway.")
        radio["if"].close()


if __name__ == "__main__":
    main()
