# -*- coding: utf-8 -*-
"""
birdsongtech - foto delle specie per il sito.

Per ogni specie di raspberry/specie.csv scarica da Wikimedia Commons la foto principale della voce
Wikipedia (licenze libere: CC BY, CC BY-SA, CC0, pubblico dominio), la ritaglia in formato 4:3,
la porta a 800x600 e la salva in assets/specie/<CODICE>.jpg.
Autore e licenza finiscono in assets/specie/crediti.json: il sito li mostra sotto ogni foto
(obbligatorio per le licenze CC BY e CC BY-SA).

Uso (sul PC, serve internet):
  pip install pillow
  python foto_specie.py            scarica solo le foto mancanti
  python foto_specie.py --tutte    riscarica tutto (es. dopo aver cambiato assets/specie/scelte.csv)
  python foto_specie.py ERIRUB     solo alcune specie

Per scegliere una foto diversa o spostare il ritaglio, compila assets/specie/scelte.csv:
  codice,file_commons,ritaglio
  ERIRUB,File:Erithacus rubecula with cocked head.jpg,alto
(ritaglio: alto, centro, basso; meta-alta / meta-bassa per i fotomontaggi di due foto una sopra l'altra).
Poi rilancia lo script con quei codici.
Alla fine apri assets/specie/anteprima.html per controllare tutte le foto in una pagina.
"""
import csv
import html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

CARTELLA = os.path.dirname(os.path.abspath(__file__))
TAB_SPECIE = os.path.join(CARTELLA, "raspberry", "specie.csv")
CARTELLA_FOTO = os.path.join(CARTELLA, "assets", "specie")
CREDITI = os.path.join(CARTELLA_FOTO, "crediti.json")
SCELTE = os.path.join(CARTELLA_FOTO, "scelte.csv")
LARGHEZZA, ALTEZZA = 800, 600
# Wikimedia chiede un User-Agent che identifichi il progetto e un contatto
UA = "birdsongtech/1.0 (https://www.birdsongtech.it; birdsongtech@gmail.com)"
# licenze libere che permettono la ripubblicazione indicando autore e licenza.
# Esclusa la GFDL: richiederebbe di pubblicare il testo integrale della licenza.
LICENZE_OK = ("cc by", "cc-by", "cc0", "public domain", "pd", "cc sa", "cc-sa", "fal", "free art")
FORMATI_OK = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def scarica(url, dati=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        contenuto = r.read()
    return contenuto if dati else json.loads(contenuto.decode("utf-8"))


def pulisci_html(testo):
    testo = re.sub(r"<[^>]+>", "", testo or "")
    return re.sub(r"\s+", " ", html.unescape(testo)).strip()


def file_principale(nome_sci):
    """Nome del file Commons della foto principale della voce Wikipedia (prima italiana, poi inglese)."""
    titolo = urllib.parse.quote(nome_sci.replace(" ", "_"))
    for lingua in ("it", "en"):
        try:
            d = scarica(f"https://{lingua}.wikipedia.org/api/rest_v1/page/summary/{titolo}")
        except Exception:
            continue
        src = (d.get("originalimage") or {}).get("source")
        if src:
            src = src.split("?")[0].split("#")[0]          # Wikipedia aggiunge ?utm_source=... agli URL
            parti = src.rstrip("/").split("/")
            # miniatura (.../thumb/a/ab/Nome.jpg/3840px-Nome.jpg): il nome vero e' il penultimo pezzo
            nome = urllib.parse.unquote(parti[-2] if "/thumb/" in src and len(parti) > 1 else parti[-1])
            return "File:" + nome.replace("_", " ")
    return None


def candidati_commons(nome_sci, quanti=15):
    """Altre foto della specie su Commons (ricerca per nome scientifico), da provare se la principale non va."""
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "list": "search", "srnamespace": 6,
        "srsearch": f'"{nome_sci}" filetype:bitmap', "srlimit": quanti,
    })
    d = scarica(f"https://commons.wikimedia.org/w/api.php?{q}")
    escludi = ("egg", "uovo", "uova", "nest", "nido", "map", "mappa", "range", "distribution", "skull", "museum")
    return [r["title"] for r in d.get("query", {}).get("search", [])
            if r["title"].lower().endswith(FORMATI_OK) and not any(e in r["title"].lower() for e in escludi)]


def adatta(titolo):
    """Controlla formato e licenza di un file Commons; restituisce le info o solleva ValueError."""
    if not titolo.lower().endswith(FORMATI_OK):
        raise ValueError(f"non e' una fotografia ({titolo})")
    info = info_file(titolo)
    if not info or not info["url"]:
        raise ValueError(f"file non trovato su Commons ({titolo})")
    if not info["licenza"].lower().startswith(LICENZE_OK):
        raise ValueError(f"licenza non adatta: {info['licenza']}")
    return info


def info_file(titolo_file):
    """URL della miniatura e dati di licenza da Commons."""
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": 1600, "titles": titolo_file,
    })
    d = scarica(f"https://commons.wikimedia.org/w/api.php?{q}")
    pagina = next(iter(d.get("query", {}).get("pages", {}).values()), {})
    ii = (pagina.get("imageinfo") or [None])[0]
    if not ii:
        return None
    meta = ii.get("extmetadata", {})
    val = lambda k: pulisci_html((meta.get(k) or {}).get("value", ""))
    return {
        "url": ii.get("thumburl") or ii.get("url"),
        "pagina": ii.get("descriptionurl"),
        "autore": val("Artist") or val("Credit") or "autore sconosciuto",
        "licenza": val("LicenseShortName"),
        "url_licenza": val("LicenseUrl"),
    }


def ritaglia(dati_immagine, posizione="centro"):
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(dati_immagine))).convert("RGB")
    w, h = im.size
    # fotomontaggi con due foto una sopra l'altra: tengo solo la meta' indicata, poi ritaglio centrato
    if posizione in ("meta-alta", "meta-bassa"):
        im = im.crop((0, 0, w, h // 2)) if posizione == "meta-alta" else im.crop((0, h - h // 2, w, h))
        w, h = im.size
        posizione = "centro"
    rapporto = LARGHEZZA / ALTEZZA
    if w / h > rapporto:                      # troppo larga: taglio ai lati (centrato)
        nw = int(h * rapporto)
        x = (w - nw) // 2
        im = im.crop((x, 0, x + nw, h))
    else:                                     # troppo alta: taglio sopra/sotto secondo "posizione"
        nh = int(w / rapporto)
        y = {"alto": 0, "basso": h - nh}.get(posizione, (h - nh) // 2)
        im = im.crop((0, y, w, y + nh))
    im = im.resize((LARGHEZZA, ALTEZZA), Image.LANCZOS)
    uscita = io.BytesIO()
    im.save(uscita, "JPEG", quality=82, optimize=True, progressive=True)
    return uscita.getvalue()


def leggi_csv(percorso, chiave):
    if not os.path.exists(percorso):
        return {}
    with open(percorso, newline="", encoding="utf-8-sig") as f:
        return {r[chiave].strip().upper(): r for r in csv.DictReader(f) if r.get(chiave)}


def scrivi_anteprima(specie, crediti):
    celle = []
    for cod, s in sorted(specie.items(), key=lambda x: x[1]["nome_ita"]):
        c = crediti.get(cod)
        img = f'<img src="{cod}.jpg" alt="">' if c else '<div class="manca">nessuna foto</div>'
        cred = html.escape(f"{c['autore']} · {c['licenza']}") if c else ""
        celle.append(f'<figure>{img}<figcaption><b>{html.escape(s["nome_ita"])}</b> <i>{html.escape(s["nome_sci"])}</i>'
                     f'<br><code>{cod}</code> {cred}</figcaption></figure>')
    pagina = f"""<!DOCTYPE html><meta charset="utf-8"><title>Anteprima foto specie</title>
<style>body{{background:#1c2124;color:#eef0ee;font:14px system-ui;margin:20px}}
main{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}}
figure{{margin:0}}img,.manca{{width:100%;aspect-ratio:4/3;border-radius:8px;object-fit:cover;background:#2d3439}}
.manca{{display:grid;place-items:center;color:#f87e2e}}figcaption{{margin-top:6px;color:#8f989f}}b{{color:#eef0ee}}</style>
<h1>Foto delle specie ({len(crediti)} su {len(specie)})</h1>
<p>Per cambiare una foto o il ritaglio usa scelte.csv (istruzioni in cima a foto_specie.py).</p>
<main>{''.join(celle)}</main>"""
    with open(os.path.join(CARTELLA_FOTO, "anteprima.html"), "w", encoding="utf-8") as f:
        f.write(pagina)


def main():
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("[X] Manca la libreria Pillow. Esegui:  pip install pillow")
        return 1
    os.makedirs(CARTELLA_FOTO, exist_ok=True)
    specie = leggi_csv(TAB_SPECIE, "codice")
    scelte = leggi_csv(SCELTE, "codice")
    crediti = json.load(open(CREDITI, encoding="utf-8")) if os.path.exists(CREDITI) else {}
    argomenti = [a.upper() for a in sys.argv[1:] if not a.startswith("--")]
    tutte = "--tutte" in sys.argv
    da_fare = [c for c in specie if (c in argomenti) or (not argomenti and (tutte or c not in crediti))]
    print(f"Specie: {len(specie)} · foto gia' presenti: {len(crediti)} · da scaricare: {len(da_fare)}")

    problemi = []
    for n, cod in enumerate(sorted(da_fare), 1):
        s = specie[cod]
        scelta = scelte.get(cod, {})
        try:
            titolo = (scelta.get("file_commons") or "").strip() or file_principale(s["nome_sci"])
            titolo = (titolo or "").split("?")[0]
            info, motivo = None, "nessuna foto nella voce Wikipedia"
            if titolo:
                try:
                    info = adatta(titolo)
                except ValueError as e:
                    motivo = str(e)
            if info is None and not scelta.get("file_commons"):
                # la foto principale non va bene: cerco un'alternativa su Commons
                for alt in candidati_commons(s["nome_sci"]):
                    try:
                        info, titolo = adatta(alt), alt
                        print(f"      foto principale scartata ({motivo}), uso {alt}")
                        break
                    except Exception:
                        continue
            if info is None:
                raise ValueError(motivo)
            jpg = ritaglia(scarica(info["url"], dati=True), (scelta.get("ritaglio") or "centro").strip().lower())
            with open(os.path.join(CARTELLA_FOTO, f"{cod}.jpg"), "wb") as f:
                f.write(jpg)
            crediti[cod] = {"file": titolo, "autore": info["autore"][:120], "licenza": info["licenza"],
                            "url_licenza": info["url_licenza"], "pagina": info["pagina"]}
            print(f"  [{n}/{len(da_fare)}] {s['nome_ita']}: ok ({info['licenza']}, {info['autore'][:40]})")
        except Exception as e:
            problemi.append((cod, s["nome_ita"], str(e)))
            print(f"  [{n}/{len(da_fare)}] {s['nome_ita']}: [!] {e}")
        time.sleep(0.5)                       # gentilezza verso i server di Wikimedia
        with open(CREDITI, "w", encoding="utf-8") as f:
            json.dump(crediti, f, ensure_ascii=False, indent=1, sort_keys=True)

    scrivi_anteprima(specie, crediti)
    print(f"\n[OK] Foto disponibili: {len(crediti)} su {len(specie)}. Controllale in assets/specie/anteprima.html")
    if problemi:
        print("[!] Da sistemare a mano (scegli un file in scelte.csv):")
        for cod, nome, e in problemi:
            print(f"     {cod} {nome}: {e}")
    print("Poi lancia aggiorna_birdsong.bat per pubblicarle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
