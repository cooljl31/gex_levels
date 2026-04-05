# GEX to Bookmap Automation

## Current Setup

✅ **Automatic updates twice daily** at US market open and before close

### Schedule (German Time / CET/CEST):

- **3:30 PM (15:30)** - US market open (9:30 AM ET)
- **9:30 PM (21:30)** - Before US market close (3:30 PM ET)
- **Monday-Friday only**

### Files Created:

1. **gex_to_bookmap.py** - Main Python script that fetches GEX data and pushes to GitHub
2. **run_gex_update.sh** - Bash wrapper that checks market hours before running
3. **com.gexbot.bookmap.update.plist** - macOS LaunchAgent for scheduling

### Data Update Frequency

- **GEXbot API**: Updates every 1-5 minutes during market hours
- **Auto-update script**: Runs every 5 minutes (300 seconds)
- **Only runs**: Monday-Friday, 9:30 AM - 4:00 PM ET

### Current Tracked Symbols

- SPY
- QQQ

To add more symbols, edit `ASSETS_TO_TRACK` in gex_to_bookmap.py

## Managing the Scheduler

### Check if running:
```bash
launchctl list | grep gexbot
```

### View logs:
```bash
# Update logs
tail -f ~/Documents/Bookmap\ cloud\ notes/gex_update.log

# LaunchD logs
tail -f ~/Documents/Bookmap\ cloud\ notes/gex_launchd.log
```

### Stop automatic updates:
```bash
launchctl unload ~/Library/LaunchAgents/com.gexbot.bookmap.update.plist
```

### Start automatic updates:
```bash
launchctl load ~/Library/LaunchAgents/com.gexbot.bookmap.update.plist
```

### Restart after changes:
```bash
launchctl unload ~/Library/LaunchAgents/com.gexbot.bookmap.update.plist
launchctl load ~/Library/LaunchAgents/com.gexbot.bookmap.update.plist
```

### Run manually:
```bash
cd ~/Documents/Bookmap\ cloud\ notes
./run_gex_update.sh
```

## Bookmap Cloud Notes URL

Add this URL to your Bookmap Cloud Notes settings:

```
https://raw.githubusercontent.com/cooljl31/gex_levels/main/gex_levels.csv
```

## Timezone Configuration

⚠️ The market hours check assumes you're in ET (Eastern Time). If you're in a different timezone, edit `run_gex_update.sh` and adjust the market hours check accordingly.

For example, if you're in PST (Pacific Time):
- Change market hours from 9:30-16:00 to 6:30-13:00

## API Information

- **Endpoint**: `https://api.gexbot.com/{TICKER}/classic/{AGGREGATION}/majors`
- **Aggregation**: `full` (can also use `zero` or `one`)
- **Response fields**:
  - `mpos_oi`: Most Positive GEX (Call Wall)
  - `mneg_oi`: Most Negative GEX (Put Wall)
  - `zero_gamma`: Zero Gamma level
  - `spot`: Current spot price
  - `timestamp`: Unix timestamp of data

## Troubleshooting

### Script not running?
1. Check logs: `tail -f ~/Documents/Bookmap\ cloud\ notes/gex_update.log`
2. Verify scheduler is loaded: `launchctl list | grep gexbot`
3. Test manually: `./run_gex_update.sh`

### Data not updating in Bookmap?
1. Check GitHub repo for latest CSV: https://github.com/cooljl31/gex_levels
2. Verify Bookmap is using the raw GitHub URL
3. Bookmap may cache the file - wait a few minutes or restart Bookmap

### Permission errors?
```bash
chmod +x ~/Documents/Bookmap\ cloud\ notes/run_gex_update.sh
```
