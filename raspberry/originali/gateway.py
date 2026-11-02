import os
import csv
import time
import requests
import meshtastic
import meshtastic.serial_interface
from pubsub import pub

# --- CONFIGURAZIONE TELEGRAM ---



# --- CONFIGURAZIONE FILE LOG ---
CSV_FILENAME = "log sistema di ascolto Birdsong Palude Torre Flavia.csv"

# Inizializza il file CSV con l'intestazione se non esiste
if not os.path.exists(CSV_FILENAME):
    with open(CSV_FILENAME, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Data e Ora", "ID Nodo Mittente", "Messaggio Ricevuto", "Stato Bioacustico"])

def invia_telegram(testo):
    """Invia un messaggio al gruppo di lavoro Telegram"""
    url = f"https://telegram.org{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": testo, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"Errore Telegram: {response.text}")
    except Exception as e:
        print(f"Impossibile inviare messaggio Telegram: {e}")

def on_receive(packet, interface):
    if 'decoded' in packet and packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
        message = packet['decoded']['text']
        sender = packet['fromId']
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        is_bioacoustic = "SÌ" if "ID:" in message else "NO"
        
        print(f"[{timestamp}] Ricevuto da {sender}: {message}")
        
        # 1. Salvataggio su file CSV
        try:
            with open(CSV_FILENAME, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, sender, message, is_bioacoustic])
        except Exception as e:
            print(f"Errore scrittura CSV: {e}")
            
        # 2. Gestione Notifica ed Invio su Telegram
        if is_bioacoustic == "SÌ":
            testo_notifica = (
                f"🚨 *Rilevamento Bioacustico - Torre Flavia*\n\n"
                f"📅 *Data/Ora:* {timestamp}\n"
                f"📡 *Nodo Mittente:* `{sender}`\n"
                f"🐦 *Dettaglio Evento:* `{message}`"
            )
            invia_telegram(testo_notifica)

# Connessione alla Heltec tramite la porta USB
print("Connessione al nodo Meshtastic su /dev/ttyUSB0...")
interface = meshtastic.serial_interface.SerialInterface(devPath='/dev/ttyUSB0')

# Sottoscrizione ai messaggi in arrivo
pub.subscribe(on_receive, "meshtastic.receive")

print("Gateway in ascolto e logging attivo. Premi Ctrl+C per uscire.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nChiusura gateway.")
    interface.close()

