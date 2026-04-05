#!/bin/bash
# Script to run GEX update and push to GitHub
# Runs at 3:30 PM and 9:30 PM German time (9:30 AM and 3:30 PM US ET)
# Monday-Friday only

LOG_FILE="/Users/cooljl31/Documents/Bookmap cloud notes/gex_update.log"
SCRIPT_DIR="/Users/cooljl31/Documents/Bookmap cloud notes"
PYTHON="/Users/cooljl31/.asdf/installs/python/3.13.5/bin/python"

echo "=== GEX Update Run: $(date) ===" >> "$LOG_FILE"

cd "$SCRIPT_DIR" || exit 1

$PYTHON gex_to_bookmap.py >> "$LOG_FILE" 2>&1

echo "=== Completed: $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
