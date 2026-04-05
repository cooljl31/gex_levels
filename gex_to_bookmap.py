import requests
import csv
import os
import subprocess
import sys
from datetime import date, datetime

# =================================================================
# KONFIGURATION - BITTE ANPASSEN
# =================================================================

# Futures contract month codes
MONTH_CODES = {
    1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
    7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z'
}

def get_futures_contract(symbol):
    """Generate current futures contract name for Bookmap."""
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    # Quarterly contracts: March (H), June (M), September (U), December (Z)
    quarterly_months = [3, 6, 9, 12]

    # Find next quarterly month
    next_quarter = None
    for m in quarterly_months:
        if m >= current_month:
            next_quarter = m
            break

    if next_quarter is None:
        next_quarter = quarterly_months[0]
        current_year += 1

    month_code = MONTH_CODES[next_quarter]
    year_code = str(current_year)[-1]  # Just last digit

    return f"{symbol}{month_code}{year_code}.CME@BMD"

# Cross-asset mapping: ETF -> Futures target
# SPY levels will also appear on ES chart, QQQ levels on NQ chart
ETF_TO_FUTURES_MAP = {
    "SPY": "ES_SPX",
    "QQQ": "NQ_NDX",
}

def calculate_multiplier(assets_data_list, etf_ticker, futures_ticker):
    """Calculate price multiplier between ETF and Futures using live spot prices."""
    etf_spot = None
    futures_spot = None
    for ticker, _, gex_json in assets_data_list:
        if gex_json is None:
            continue
        if ticker == etf_ticker:
            etf_spot = gex_json.get('spot')
        if ticker == futures_ticker:
            futures_spot = gex_json.get('spot')
    if etf_spot and futures_spot and etf_spot != 0:
        multiplier = futures_spot / etf_spot
        print(f"  Multiplier {etf_ticker}->{futures_ticker}: {multiplier:.4f} ({etf_spot} -> {futures_spot})")
        return multiplier
    return None

# 1. GEXBOT API EINSTELLUNGEN
# API key is loaded from environment variable (never hardcoded here)
# Set GEXBOT_API_KEY in your environment or in the launchd plist
GEXBOT_API_KEY = os.environ.get("GEXBOT_API_KEY", "")
if not GEXBOT_API_KEY:
    # Fallback: read from local .env file (not tracked by git)
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(_env_path):
        with open(_env_path) as _f:
            for _line in _f:
                if _line.startswith("GEXBOT_API_KEY="):
                    GEXBOT_API_KEY = _line.strip().split("=", 1)[1]
                    break
GEXBOT_BASE_URL = "https://api.gexbot.com" # Classic API URL

# Aggregation periods to fetch (full, zero, one)
AGGREGATION_PERIODS = ["zero"]
# AGGREGATION_PERIODS = ["full", "zero", "one"]

# Max Priors: which lookback periods to show in Bookmap
# Options: "current", "one", "five", "ten", "fifteen", "thirty"
MAXCHANGE_PRIORS = ["current", "one", "five", "ten", "fifteen", "thirty"]
MAXCHANGE_PRIOR_LABELS = {
    "current": "now",
    "one":     "1m",
    "five":    "5m",
    "ten":     "10m",
    "fifteen": "15m",
    "thirty":  "30m",
}

# Liste der Assets, die du tracken willst (GEXbot Ticker-Namen)
# BEISPIEL: ["SPY", "QQQ", "SPX", "NDX"]
# You can also use "ALL_STOCKS", "ALL_INDEXES", "ALL_FUTURES" to fetch all available
ASSETS_TO_TRACK = [
    # Major ETFs
    "SPY", "QQQ", "IWM", "DIA",
    # Major Indexes
    "SPX", "NDX", "RUT", "VIX",
    # Futures
    "ES_SPX", "NQ_NDX",
    # Popular Stocks
    "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL",
    "AMD", "AVGO", "PLTR", "MSTR", "COIN"
]

# Map GEXbot symbols to Bookmap instrument names
# Bookmap format: SYMBOL.EXCHANGE@DATAPROVIDER
# Futures use current quarterly contract (auto-detected)
def get_symbol_mapping():
    """Generate symbol mapping with current futures contracts."""
    return {
        "ES_SPX": get_futures_contract("ES"),   # S&P 500 futures
        "NQ_NDX": get_futures_contract("NQ"),   # Nasdaq futures
        "RTY": get_futures_contract("RTY"),      # Russell 2000 futures
        "YM": get_futures_contract("YM"),        # Dow futures
        "SPY": "SPY.NYSE@BMD",
        "QQQ": "QQQ.NASDAQ@BMD",
        "IWM": "IWM.NYSE@BMD",
        "DIA": "DIA.NYSE@BMD",
        "SPX": "SPX.IND@BMD",
        "NDX": "NDX.IND@BMD",
        "RUT": "RUT.IND@BMD",
        "VIX": "VIX.IND@BMD",
        "NVDA": "NVDA.NASDAQ@BMD",
        "TSLA": "TSLA.NASDAQ@BMD",
        "AAPL": "AAPL.NASDAQ@BMD",
        "MSFT": "MSFT.NASDAQ@BMD",
        "AMZN": "AMZN.NASDAQ@BMD",
        "META": "META.NASDAQ@BMD",
        "GOOGL": "GOOGL.NASDAQ@BMD",
        "AMD": "AMD.NASDAQ@BMD",
        "AVGO": "AVGO.NASDAQ@BMD",
        "PLTR": "PLTR.NYSE@BMD",
        "MSTR": "MSTR.NASDAQ@BMD",
        "COIN": "COIN.NASDAQ@BMD",
    }

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
COLOR_CALL_WALL        = "#FFFFFF,#008000"  # Weiß auf Grün
COLOR_PUT_WALL         = "#FFFFFF,#8B0000"  # Weiß auf Rot
COLOR_ZERO_GEX         = "#FFFFFF,#9370DB"  # Weiß auf Lila
COLOR_MAX_GEX          = "#000000,#FFFF00"  # Schwarz auf Gelb
COLOR_MAXCHANGE_BUILD  = "#000000,#00BFFF"  # Schwarz auf Blau  (GEX-Aufbau)
COLOR_MAXCHANGE_CUT    = "#FFFFFF,#FF6600"  # Weiß auf Orange   (GEX-Abbau)

# Vollständiger Pfad zur CSV-Datei
FINAL_CSV_PATH = os.path.join(LOCAL_GIT_REPO_DIR, CSV_FILENAME)

# =================================================================

def fetch_gex_data(asset_ticker, aggregation_period):
    """Holt die wichtigsten GEX-Level für einen Ticker von der API."""
    url = f"{GEXBOT_BASE_URL}/{asset_ticker}/classic/{aggregation_period}/majors"
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
        print(f"Fehler beim Abrufen der Daten für {asset_ticker} ({aggregation_period}): {e}")
        return None

def fetch_maxchange_data(asset_ticker, aggregation_period):
    """Fetches the GEX Max Change (Max Priors) data for a ticker."""
    url = f"{GEXBOT_BASE_URL}/{asset_ticker}/classic/{aggregation_period}/maxchange"
    headers = {"User-Agent": "BookmapGEX/1.0", "Accept": "application/json"}
    params = {"key": GEXBOT_API_KEY}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen von MaxChange für {asset_ticker}: {e}")
        return None


def generate_local_csv(assets_data_list, maxchange_data=None):
    """Erstellt die Bookmap CSV-Datei lokal im Git-Ordner."""

    # CSV-Spaltenüberschriften
    fieldnames = [
        "Symbol", "Price Level", "Note", "Foreground Color",
        "Background Color", "Text Alignment", "Diameter",
        "Draw Note Price Horizontal Line"
    ]

    # Get current symbol mapping with dynamic futures contracts
    symbol_mapping = get_symbol_mapping()

    # Pre-calculate live ETF->Futures multipliers
    multipliers = {}
    for etf_ticker, futures_ticker in ETF_TO_FUTURES_MAP.items():
        m = calculate_multiplier(assets_data_list, etf_ticker, futures_ticker)
        if m:
            multipliers[etf_ticker] = (futures_ticker, m)

    try:
        with open(FINAL_CSV_PATH, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Iteriere über alle Assets und füge Daten hinzu
            for asset_ticker, aggregation, gex_json in assets_data_list:
                if not gex_json: continue

                # Extrahiere Big Four (GEXbot Classic API Struktur)
                # mpos_oi = Most Positive GEX (Call Wall), mneg_oi = Most Negative GEX (Put Wall)
                zero_gamma_price = gex_json.get('zero_gamma')
                net_gex_value = gex_json.get('net_gex_oi')

                levels = [
                    {"price": gex_json.get('mpos_oi'), "note": "CALL", "color": COLOR_CALL_WALL, "draw_line": True, "show_price": True},
                    {"price": gex_json.get('mneg_oi'),  "note": "PUT",  "color": COLOR_PUT_WALL, "draw_line": True, "show_price": True},
                    {"price": zero_gamma_price, "note": "ZERO GAMMA", "color": COLOR_ZERO_GEX, "draw_line": True, "show_price": False},
                    {"price": gex_json.get('spot'),    "note": "SPOT",    "color": COLOR_MAX_GEX, "draw_line": True, "show_price": True}
                ]

                # Add NET GEX as separate label at zero gamma price (no line)
                if zero_gamma_price is not None and zero_gamma_price != 0 and net_gex_value is not None:
                    levels.append({
                        "price": zero_gamma_price,
                        "note": "NET GEX",
                        "value": net_gex_value,
                        "color": "#000000,#FFA500",  # Black on Orange
                        "draw_line": False,
                        "show_price": False
                    })

                # Map to Bookmap instrument name
                bookmap_symbol = symbol_mapping.get(asset_ticker, asset_ticker)

                # Write normal levels for this asset
                for lvl in levels:
                    if lvl['price'] is not None and lvl['price'] != 0:  # Skip zero values
                        fg_color, bg_color = lvl['color'].split(',')
                        # Check if we should add price to note text
                        if 'value' in lvl:
                            # NET GEX shows its value, not the price
                            note_text = f"{lvl['note']} {lvl['value']:.1f}"
                        elif lvl.get('show_price', True):
                            note_text = f"{lvl['note']} {lvl['price']:.1f}"
                        else:
                            note_text = lvl['note']
                        draw_line = "TRUE" if lvl.get('draw_line', True) else "FALSE"
                        writer.writerow({
                            "Symbol": bookmap_symbol,
                            "Price Level": lvl['price'],
                            "Note": note_text,
                            "Foreground Color": fg_color,
                            "Background Color": bg_color,
                            "Text Alignment": "center",
                            "Diameter": "1",
                            "Draw Note Price Horizontal Line": draw_line
                        })

                # --- Cross-asset: write ETF levels on Futures chart ---
                if asset_ticker in multipliers:
                    futures_ticker, mult = multipliers[asset_ticker]
                    futures_symbol = symbol_mapping.get(futures_ticker, futures_ticker)
                    for lvl in levels:
                        raw_price = lvl.get('value', lvl['price'])  # NET GEX has no cross-asset meaning, skip
                        if 'value' in lvl:
                            continue  # Skip NET GEX for cross-asset
                        if lvl['price'] is None or lvl['price'] == 0:
                            continue
                        converted_price = round(lvl['price'] * mult, 2)
                        fg_color, bg_color = lvl['color'].split(',')
                        if lvl.get('show_price', True):
                            note_text = f"{lvl['note']} ({asset_ticker}) {converted_price:.1f}"
                        else:
                            note_text = f"{lvl['note']} ({asset_ticker})"
                        draw_line = "TRUE" if lvl.get('draw_line', True) else "FALSE"
                        writer.writerow({
                            "Symbol": futures_symbol,
                            "Price Level": converted_price,
                            "Note": note_text,
                            "Foreground Color": fg_color,
                            "Background Color": bg_color,
                            "Text Alignment": "center",
                            "Diameter": "1",
                            "Draw Note Price Horizontal Line": draw_line
                        })
                # --- Max Priors (GEX Max Change) ---
                if maxchange_data and asset_ticker in maxchange_data:
                    mc = maxchange_data[asset_ticker]
                    for prior_key in MAXCHANGE_PRIORS:
                        prior_data = mc.get(prior_key)
                        if not prior_data or len(prior_data) < 2:
                            continue
                        strike, gex_value = prior_data[0], prior_data[1]
                        if not strike or strike == 0:
                            continue
                        label = MAXCHANGE_PRIOR_LABELS.get(prior_key, prior_key)
                        direction = "+" if gex_value >= 0 else ""
                        note_text = f"-- GEX {label} {direction}{gex_value:.0f} --"
                        color = COLOR_MAXCHANGE_BUILD if gex_value >= 0 else COLOR_MAXCHANGE_CUT
                        fg_color, bg_color = color.split(',')
                        writer.writerow({
                            "Symbol": bookmap_symbol,
                            "Price Level": strike,
                            "Note": note_text,
                            "Foreground Color": fg_color,
                            "Background Color": bg_color,
                            "Text Alignment": "center",
                            "Diameter": "1",
                            "Draw Note Price Horizontal Line": "FALSE"
                        })
                        # Cross-asset: also write on Futures chart
                        if asset_ticker in multipliers:
                            futures_ticker_mc, mult_mc = multipliers[asset_ticker]
                            futures_sym_mc = symbol_mapping.get(futures_ticker_mc, futures_ticker_mc)
                            converted_strike = round(strike * mult_mc, 2)
                            note_cross = f"-- GEX {label} ({asset_ticker}) {direction}{gex_value:.0f} --"
                            writer.writerow({
                                "Symbol": futures_sym_mc,
                                "Price Level": converted_strike,
                                "Note": note_cross,
                                "Foreground Color": fg_color,
                                "Background Color": bg_color,
                                "Text Alignment": "center",
                                "Diameter": "1",
                                "Draw Note Price Horizontal Line": "FALSE"
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
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_message = f"GEX Levels Update via SSH [{today_str}]"
    run_git_command(["git", "commit", "-m", commit_message])

    # 4. git push
    run_git_command(["git", "push"])

    print("ERFOLG: GEX-Level wurden per Git SSH auf GitHub aktualisiert.")

def generate_raw_github_url():
    """Erstellt den Direktdownload-Link (Raw) für Bookmap."""
    return f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO_NAME}/{GITHUB_BRANCH}/{CSV_FILENAME}"

# --- HAUPTPROGRAMM ---

if __name__ == "__main__":
    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"--- GEX Update gestartet: {run_timestamp} ---")
    print(f"{'='*60}")

    # Überprüfen, ob der Git-Ordner existiert
    if not os.path.exists(LOCAL_GIT_REPO_DIR) or not os.path.isdir(os.path.join(LOCAL_GIT_REPO_DIR, ".git")):
        print(f"FEHLER: Der Pfad '{LOCAL_GIT_REPO_DIR}' ist kein gültiges Git-Repository.")
        sys.exit(1)

    assets_results = []
    maxchange_results = {}
    for asset_ticker in ASSETS_TO_TRACK:
        print(f"Verarbeite Asset: {asset_ticker}...")
        for aggregation_period in AGGREGATION_PERIODS:
            gex_json = fetch_gex_data(asset_ticker, aggregation_period)
            assets_results.append((asset_ticker, aggregation_period, gex_json))
            mc_json = fetch_maxchange_data(asset_ticker, aggregation_period)
            if mc_json and not mc_json.get('error'):
                maxchange_results[asset_ticker] = mc_json

    if assets_results:
        # 1. CSV-Datei lokal im Git-Repo generieren
        if generate_local_csv(assets_results, maxchange_data=maxchange_results):
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
