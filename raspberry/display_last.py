import os
import csv
import time

CSV_FILENAME = "/home/pi/log sistema di ascolto Birdsong Palude Torre Flavia.csv"

def leggi_ultima_riga():
    if not os.path.exists(CSV_FILENAME):
        return "In attesa di dati...", "Nessun nodo", "Nessun messaggio"
    
    try:
        with open(CSV_FILENAME, mode='r', newline='', encoding='utf-8') as file:
            reader = list(csv.reader(file))
            if len(reader) <= 1:  # C'è solo l'intestazione
                return "In attesa di dati...", "Nessun nodo", "Nessun messaggio"
            
            # Prende l'ultima riga reale del file
            ultima_riga = reader[-1]
            
            # Estrae le colonne singole in modo sicuro evitando errori se la riga è incompleta
            data_ora = ultima_riga[0] if len(ultima_riga) > 0 else "---"
            nodo = ultima_riga[1] if len(ultima_riga) > 1 else "---"
            msg = ultima_riga[2] if len(ultima_riga) > 2 else "---"
            
            # Raccorcia l'ID del nodo se è troppo lungo per lo schermo (es. toglie i caratteri inutili)
            if len(nodo) > 15:
                nodo = nodo[:15] + "..."
                
            return data_ora, nodo, msg
    except Exception as e:
        return f"Errore: {e}", "---", "---"

ultimo_stato = ""
while True:
    data_ora, nodo, msg = leggi_ultima_riga()
    stato_attuale = f"{data_ora}{nodo}{msg}"
    
    if stato_attuale != ultimo_stato:
        os.system('clear')  # Pulisce lo schermo LCD
        print("\n" + "="*20)
        print(" 📢 BIRDSONG IA")
        print("  TORRE FLAVIA")
        print("="*20 + "\n")
        print(f" 📅 DATA/ORA:\n {data_ora}\n")
        print(f" 📡 NODO MITTENTE:\n {nodo}\n")
        print(f" 🐦 EVENTO UDIRE:\n {msg}")
        print("\n" + "="*20)
        ultimo_stato = stato_attuale
        
    time.sleep(2)
