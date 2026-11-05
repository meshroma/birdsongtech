import os
import csv
import time
from datetime import datetime, timedelta

# Display LCD della stazione base: mostra a colpo d'occhio se la radio riceve.
# Legge il registro grezzo scritto da gateway.py (stesso file e stesso formato di prima).
# Cambia solo il testo stampato: driver, framebuffer e servizio restano invariati.
# Solo caratteri semplici: la console del display non mostra icone ed emoji.

CSV_FILENAME = "/home/pi/log sistema di ascolto Birdsong Palude Torre Flavia.csv"
RADIO_FILENAME = "/home/pi/radio.csv"     # qualita' del segnale, scritto da gateway.py
SOGLIA = 80              # un file e' "valido" da questa affidabilita' (%) in su
FINESTRA_MINUTI = 15     # i messaggi arrivati entro 15 minuti fanno parte della stessa ricezione
LINEA = "=" * 36


def leggi_righe():
    if not os.path.exists(CSV_FILENAME):
        return []
    try:
        with open(CSV_FILENAME, mode='r', newline='', encoding='utf-8') as file:
            righe = list(csv.reader(file))
        return [r for r in righe[1:] if len(r) >= 3]    # salta l'intestazione e le righe incomplete
    except Exception:
        return []


def segnale():
    """SNR, RSSI e salti dell'ultimo messaggio BS1 ricevuto (da radio.csv)."""
    if not os.path.exists(RADIO_FILENAME):
        return None
    try:
        with open(RADIO_FILENAME, mode='r', newline='', encoding='utf-8') as file:
            righe = [r for r in csv.DictReader(file) if r.get("tipo") in ("H", "D")]
    except Exception:
        return None
    if not righe:
        return None
    r = righe[-1]
    parti = []
    if r.get("snr"):
        try:
            parti.append(f"SNR {float(r['snr']):.1f} dB")
        except ValueError:
            pass
    if r.get("rssi"):
        parti.append(f"RSSI {r['rssi']}")
    if r.get("hop") != "":
        parti.append(f"HOP {r['hop']}")
    return "  ".join(parti)[:34] or None


def data_ora(testo):
    try:
        return datetime.strptime(testo, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def riepilogo():
    righe = leggi_righe()
    if not righe:
        return None
    bs1 = [r for r in righe if r[2].startswith("BS1 H") or r[2].startswith("BS1 D")]
    ultima = bs1[-1] if bs1 else righe[-1]
    quando = data_ora(ultima[0])

    # nodo: sigla della stazione (es. TF01) e identificativo radio
    parti = ultima[2].split()
    sigla = parti[2] if len(parti) > 2 and ultima[2].startswith("BS1") else ""
    nodo = f"{sigla} ({ultima[1]})" if sigla else ultima[1] or "---"
    if len(nodo) > 34:
        nodo = nodo[:31] + "..."

    # file validi nell'ultima ricezione: tutti i messaggi D arrivati a breve distanza dall'ultimo
    validi = None
    messaggi_d = [r for r in bs1 if r[2].startswith("BS1 D")]
    if messaggi_d:
        fine = data_ora(messaggi_d[-1][0])
        validi = 0
        for r in reversed(messaggi_d):
            t = data_ora(r[0])
            if fine and t and fine - t > timedelta(minutes=FINESTRA_MINUTI):
                break
            p = r[2].split(" ", 5)
            record = p[5] if len(p) > 5 else ""
            for rec in filter(None, record.split(";")):
                campi = rec.split(",")
                if len(campi) > 2 and campi[2].strip().isdigit() and int(campi[2]) >= SOGLIA:
                    validi += 1

    # batteria: dall'ultimo messaggio H (4o campo) o D (5o campo)
    batteria = None
    for r in reversed(bs1):
        p = r[2].split()
        campo = 3 if r[2].startswith("BS1 H") else 4
        if len(p) > campo and p[campo].isdigit():
            batteria = int(p[campo])
            break

    return {
        "quando": quando.strftime("%d/%m/%Y %H:%M") if quando else ultima[0],
        "nodo": nodo,
        "validi": validi,
        "batteria": batteria,
    }


def schermata():
    r = riepilogo()
    radio = segnale()
    righe = [LINEA, " birdsongtech Palude di Torre Flavia", LINEA, ""]
    if r is None:
        righe += [" ULTIMA RICEZIONE:", " In attesa di dati...", "",
                  " NODO MITTENTE:", " Nessun nodo",
                  f" FILE VALIDI ({SOGLIA}% O PIU'):", " ---", "",
                  " BATTERIA STAZIONE: ---"]
    else:
        if r["validi"] is None:
            validi = " Nessun canto ricevuto"
        else:
            validi = f" {r['validi']} nell'ultima ricezione"
        righe += [" ULTIMA RICEZIONE:", f" {r['quando']}", "",
                  " NODO MITTENTE:", f" {r['nodo']}",
                  f" FILE VALIDI ({SOGLIA}% O PIU'):", validi, "",
                  f" BATTERIA STAZIONE: {r['batteria']}%" if r["batteria"] is not None else " BATTERIA STAZIONE: ---"]
    righe += [" SEGNALE RADIO ULTIMO MESSAGGIO:", f" {radio}" if radio else " ---"]
    righe += [LINEA]
    return "\n".join(righe)


ultimo_stato = ""
while True:
    testo = schermata()
    if testo != ultimo_stato:
        os.system('clear')  # Pulisce lo schermo LCD
        print(testo)
        ultimo_stato = testo
    time.sleep(2)
