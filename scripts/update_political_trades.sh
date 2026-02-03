#!/bin/bash
# Update Political Trades Data
# This script fetches latest data and updates the database
# Can be run manually or scheduled with cron

echo "=================================="
echo "🏛️  Political Trades Update"
echo "=================================="
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

# Step 0: Run stealth scraper for House data
echo "🕵️  Step 0: Stealth scrape for House data..."
if [ -f "$SCRIPT_DIR/house_stealth_fetcher.py" ]; then
    $VENV_PYTHON "$SCRIPT_DIR/house_stealth_fetcher.py"
    if [ $? -eq 0 ]; then
        echo "   ✅ Stealth scraper completed"
    else
        echo "   ⚠️ Stealth scraper failed (will try fallback methods)"
    fi
else
    echo "   ⚠️ Stealth scraper not found, skipping..."
fi
echo ""

# Step 1: Fetch latest data from GitHub mirrors (will use stealth cache if available)
echo "📥 Step 1: Fetching latest data..."
$VENV_PYTHON "$SCRIPT_DIR/fetch_political_trades_enriched.py"

if [ $? -ne 0 ]; then
    echo "❌ Failed to fetch data"
    exit 1
fi

echo ""

# Step 2: Import to database
echo "📊 Step 2: Updating database..."
$VENV_PYTHON "$SCRIPT_DIR/import_to_db.py"

if [ $? -ne 0 ]; then
    echo "❌ Failed to update database"
    exit 1
fi

echo ""
echo "=================================="
echo "✅ Update completed successfully!"
echo "=================================="
echo ""
echo "📝 To schedule automatic updates:"
echo "   1. Edit crontab: crontab -e"
echo "   2. Add daily update at 6 AM:"
echo "      0 6 * * * $SCRIPT_DIR/update_political_trades.sh >> $PROJECT_ROOT/logs/update.log 2>&1"
echo ""
