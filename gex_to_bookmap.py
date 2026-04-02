import requests
import csv
import os
import subprocess
import sys
from datetime import date

# =================================================================
# KONFIGURATION - BITTE ANPASSEN
# =================================================================

# 1. GEXBOT API EINSTELLUNGEN
# Trage hier deinen Classic API Key ein
GEXBOT_API_KEY = "B3d2aRvXopj7"
GEXBOT_BASE_URL = "https://api.gexbot.com" # Classic API URL
AGGREGATION_PERIOD = "full"  # Options: full, zero, or one

# Liste der Assets, die du tracken willst (GEXbot Ticker-Namen)
# BEISPIEL: ["SPY", "QQQ", "SPX", "NDX"]
ASSETS_TO_TRACK = ["SPY", "QQQ"]

# 2. LOKALE GIT REPOSITORY EINSTELLUNGEN
# WICHTIG: Dies muss der absolute Pfad zu deinem lokalen Git-Ordner sein,
# den du mit github.com/cooljl31/gex_levels verbunden hast.
# Beispiel (Windows): "C:/Users/cooljl31/Documents/gex_levels"
# Beispiel (Linux/Mac): "/home/cooljl31/gex_levels"
LOCAL_GIT_REPO_DIR = "/Users/cooljl31/Documents/Bookmap cloud notes"

# Wie die Datei im Repo heißen soll
CSV_FILENAME = "gex_levels.csv"

# 3. GITHUB INFOS FÜR DEN BOOKMAP-LINK (Bereits ausgefüllt)
GITHUB_USERNAME = "cooljl31"
GITHUB_REPO_NAME = "gex_levels"
# Prüfe, ob dein Branch 'main' oder 'master' heißt und passe es ggf. an.
GITHUB_BRANCH = "main"

# 4. BOOKMAP CSV VISUALISIERUNG (Farben: Vordergrund,Hintergrund)
COLOR_CALL_WALL = "#FFFFFF,#008000"  # Weiß auf Grün
COLOR_PUT_WALL  = "#FFFFFF,#8B0000"  # Weiß auf Rot
COLOR_ZERO_GEX  = "#FFFFFF,#9370DB"  # Weiß auf Lila
COLOR_MAX_GEX   = "#000000,#FFFF00"  # Schwarz auf Gelb

# Vollständiger Pfad zur CSV-Datei
FINAL_CSV_PATH = os.path.join(LOCAL_GIT_REPO_DIR, CSV_FILENAME)

# =================================================================

def fetch_gex_data(asset_ticker):
    """Holt die wichtigsten GEX-Level für einen Ticker von der API."""
    url = f"{GEXBOT_BASE_URL}/{asset_ticker}/classic/{AGGREGATION_PERIOD}/majors"
    headers = {
        "User-Agent": "BookmapGEX/1.0",
        "Accept": "application/json"
    }
    params = {
        "key": GEXBOT_API_KEY
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Daten für {asset_ticker}: {e}")
        return None

def generate_local_csv(assets_data_list):
    """Erstellt die Bookmap CSV-Datei lokal im Git-Ordner."""

    # CSV-Spaltenüberschriften
    fieldnames = [
        "Symbol", "Price Level", "Note", "Foreground Color",
        "Background Color", "Text Alignment", "Diameter",
        "Draw Note Price Horizontal Line"
    ]

    try:
        with open(FINAL_CSV_PATH, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Add automap command at the beginning (helps Bookmap match instruments)
            writer.writerow({
                "Symbol": "#automap RITHMIC",
                "Price Level": "",
                "Note": "",
                "Foreground Color": "",
                "Background Color": "",
                "Text Alignment": "",
                "Diameter": "",
                "Draw Note Price Horizontal Line": ""
            })

            # Iteriere über alle Assets und füge Daten hinzu
            for asset_ticker, gex_json in assets_data_list:
                if not gex_json: continue

                # Extrahiere Big Four (GEXbot Classic API Struktur)
                # mpos_oi = Most Positive GEX (Call Wall), mneg_oi = Most Negative GEX (Put Wall)
                levels = [
                    {"price": gex_json.get('mpos_oi'), "note": "CALL WALL", "color": COLOR_CALL_WALL},
                    {"price": gex_json.get('mneg_oi'),  "note": "PUT WALL",  "color": COLOR_PUT_WALL},
                    {"price": gex_json.get('zero_gamma'),"note": "ZERO GAMMA","color": COLOR_ZERO_GEX},
                    {"price": gex_json.get('spot'),    "note": "SPOT PRICE",    "color": COLOR_MAX_GEX}
                ]

                bookmap_symbol = asset_ticker

                # Füge die validen Levels hinzu
                for lvl in levels:
                    if lvl['price'] is not None and lvl['price'] != 0:  # Skip zero values
                        fg_color, bg_color = lvl['color'].split(',')
                        writer.writerow({
                            "Symbol": bookmap_symbol,
                            "Price Level": lvl['price'],
                            "Note": lvl['note'],
                            "Foreground Color": fg_color,
                            "Background Color": bg_color,
                            "Text Alignment": "center",
                            "Draw Note Price Horizontal Line": "TRUE"
                        })
        print(f"Lokale CSV-Datei erstellt: {FINAL_CSV_PATH}")
        return True
    except IOError as e:
        print(f"Fehler beim Schreiben der CSV-Datei: {e}")
        return False

def run_git_command(command_list):
    """Führt einen Git-Befehl im konfigurierten Repository-Ordner aus."""
    try:
        # Führe den Befehl im spezifischen Arbeitsverzeichnis (cwd) aus
        result = subprocess.run(
            command_list,
            cwd=LOCAL_GIT_REPO_DIR,
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Fehler beim Ausführen von Git-Befehl {' '.join(command_list)}:")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        # Wir brechen ab, wenn Git fehlschlägt.
        sys.exit(1)

def push_to_github():
    """Führt die Git-Sequenz add, commit, push aus."""
    print("Starte Git-Automatisierung über SSH...")

    # 1. git add
    run_git_command(["git", "add", CSV_FILENAME])

    # 2. Prüfen, ob es Änderungen gibt
    status = run_git_command(["git", "status", "--porcelain", CSV_FILENAME])

    if not status.strip():
        print("Keine Änderungen an der GEX-Datei festgestellt. Überspringe Commit/Push.")
        return

    # 3. git commit
    today_str = date.today().strftime("%Y-%m-%d")
    commit_message = f"Daily GEX Levels Update via SSH [{today_str}]"
    run_git_command(["git", "commit", "-m", commit_message])

    # 4. git push
    run_git_command(["git", "push"])

    print("ERFOLG: GEX-Level wurden per Git SSH auf GitHub aktualisiert.")

def generate_raw_github_url():
    """Erstellt den Direktdownload-Link (Raw) für Bookmap."""
    return f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/{GITHUB_BRANCH}/{CSV_FILENAME}"

# --- HAUPTPROGRAMM ---

if __name__ == "__main__":
    print(f"--- Starte GEXbot zu Git SSH Automatisierung für {date.today()} ---")

    # Überprüfen, ob der Git-Ordner existiert
    if not os.path.exists(LOCAL_GIT_REPO_DIR) or not os.path.isdir(os.path.join(LOCAL_GIT_REPO_DIR, ".git")):
        print(f"FEHLER: Der Pfad '{LOCAL_GIT_REPO_DIR}' ist kein gültiges Git-Repository.")
        sys.exit(1)

    assets_results = []
    for asset_ticker in ASSETS_TO_TRACK:
        print(f"Verarbeite Asset: {asset_ticker}...")
        gex_json = fetch_gex_data(asset_ticker)
        assets_results.append((asset_ticker, gex_json))

    if assets_results:
        # 1. CSV-Datei lokal im Git-Repo generieren
        if generate_local_csv(assets_results):
            # 2. Git add, commit, push ausführen
            push_to_github()

            # 3. Den direkten Link für Bookmap anzeigen
            raw_url = generate_raw_github_url()
            print("\n" + "="*60)
            print("WICHTIG FÜR BOOKMAP:")
            print("Nutze diesen Link in deinen Bookmap 'Cloud Notes' Einstellungen:")
            print("\n" + raw_url)
            print("="*60 + "\n")

    print("--- Fertig ---")
