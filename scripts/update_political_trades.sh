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

# Step 1: Fetch latest data from GitHub mirrors
echo "📥 Step 1: Fetching latest data..."
/opt/homebrew/bin/python3 "$SCRIPT_DIR/fetch_political_trades_enriched.py"

if [ $? -ne 0 ]; then
    echo "❌ Failed to fetch data"
    exit 1
fi

echo ""

# Step 2: Import to database
echo "📊 Step 2: Updating database..."
/opt/homebrew/bin/python3 "$SCRIPT_DIR/import_to_db.py"

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
