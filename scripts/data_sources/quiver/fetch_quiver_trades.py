#!/usr/bin/env python3
"""
Fetch current Congressional trades from Quiver Quant
Extracts embedded JavaScript data from their page
"""

import requests
import json
import csv
import re
from pathlib import Path
from datetime import datetime

def fetch_quiver_trades():
    """Fetch current Congressional trades from Quiver Quant"""
    url = "https://www.quiverquant.com/congresstrading/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    print("⏳ Fetching Quiver Quant page...")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    html = response.text
    print(f"✅ Downloaded {len(html):,} characters")
    
    # The data appears inline in the HTML as a large JavaScript array
    # Look for pattern starting with [['ticker', followed by trade data
    # The curl output showed the data starts directly without variable assignment
    
    # Find the start of the trades array
    # Pattern: [['TICKER_SYMBOL', 'ASSET NAME', 'ST', 'Sale', '$1,001 - $15,000', ...
    start_pattern = r'\[\[\'[A-Z0-9\-]+\',\s*\'[^\']+\',\s*\'[A-Z]{2}\',\s*\'(Purchase|Sale|Exchange)'
    start_match = re.search(start_pattern, html)
    
    if not start_match:
        print("❌ Could not find start of trades array")
        debug_path = Path(__file__).parent.parent / "logs" / "quiver_debug.html"
        debug_path.parent.mkdir(exist_ok=True)
        debug_path.write_text(html)
        print(f"Saved HTML to {debug_path} for debugging")
        return []
    
    start_pos = start_match.start()
    print(f"✅ Found trades array at position {start_pos:,}")
    
    # Find the end - look for ]]; pattern (JavaScript array terminator)
    end_pattern = r'\]\];'
    end_match = re.search(end_pattern, html[start_pos:])
    
    if not end_match:
        print("❌ Could not find end of trades array (]];)")
        return []
    
    end_pos = start_pos + end_match.start() + 2  # Include the ]]
    trades_js = html[start_pos:end_pos]
    print(f"✅ Extracted trades data ({len(trades_js):,} characters)")
    
    # Clean up JavaScript to make it valid JSON
    # Replace single quotes with double quotes, but be careful with apostrophes in names
    # This is tricky - let's use a more robust approach
    
    # Save raw JS for inspection
    debug_path = Path(__file__).parent.parent / "logs" / "quiver_trades_raw.js"
    debug_path.parent.mkdir(exist_ok=True)
    debug_path.write_text(trades_js)
    print(f"📝 Saved raw JS to {debug_path}")
    
    # Use ast.literal_eval approach - convert to Python list
    # Replace JavaScript null with Python None
    trades_py = trades_js.replace('null', 'None').replace('true', 'True').replace('false', 'False')
    
    try:
        import ast
        trades = ast.literal_eval(trades_py)
        print(f"✅ Parsed {len(trades):,} trades using Python ast")
    except Exception as e:
        print(f"❌ Parse error: {e}")
        debug_path = Path(__file__).parent.parent / "logs" / "quiver_trades.py"
        debug_path.write_text(trades_py)
        print(f"Saved Python version to {debug_path}")
        return []
    
    return trades

def convert_to_csv(trades):
    """Convert Quiver trades to CSV format matching our database schema"""
    
    # Based on the data structure we saw:
    # [0] ticker, [1] name, [2] type, [3] transaction, [4] amount_range, 
    # [5] politician, [6] chamber, [7] party, [8] report_date, [9] trade_date,
    # [10] comment, [11] unique_id, [12] price_change, [13] politician_display,
    # [14] image_url, [15] politician_id
    
    csv_rows = []
    
    for trade in trades:
        try:
            # Extract fields
            ticker = trade[0] if trade[0] != '-' else ''
            asset_name = trade[1]
            asset_type = trade[2]  # ST = Stock, CS = Corporate Security, etc.
            transaction = trade[3]  # Purchase, Sale, Sale (Full), Exchange
            amount_range = trade[4]
            politician = trade[5]
            chamber = trade[6]  # Senate or House
            party = trade[7]  # R, D, Independent
            report_date = trade[8]
            trade_date = trade[9]
            comment = trade[10] if trade[10] != '-' else ''
            
            # Parse dates (format: '2026-01-15 00:00:00')
            try:
                report_dt = datetime.strptime(report_date, '%Y-%m-%d %H:%M:%S')
                trade_dt = datetime.strptime(trade_date, '%Y-%m-%d %H:%M:%S')
            except:
                continue  # Skip if date parsing fails
            
            # Parse amount range
            min_amount = 0
            max_amount = 0
            if amount_range:
                # Format: "$1,001 - $15,000" or "$50,001 - $100,000"
                range_match = re.search(r'\$([0-9,]+)\s*-\s*\$([0-9,]+)', amount_range)
                if range_match:
                    min_amount = int(range_match.group(1).replace(',', ''))
                    max_amount = int(range_match.group(2).replace(',', ''))
            
            # Map transaction type
            # Quiver uses: Purchase, Sale, Sale (Full), Exchange
            # We want: purchase, sale, exchange
            trade_type = transaction.lower().replace(' (full)', '').replace(' (partial)', '')
            
            # Map party
            party_full = {'R': 'Republican', 'D': 'Democratic', 'I': 'Independent'}.get(party, party)
            
            csv_rows.append({
                'ticker': ticker,
                'asset_name': asset_name,
                'asset_type': asset_type,
                'transaction': trade_type,
                'amount_range': amount_range,
                'min_amount': min_amount,
                'max_amount': max_amount,
                'politician': politician,
                'chamber': chamber,
                'party': party_full,
                'report_date': report_dt.strftime('%Y-%m-%d'),
                'trade_date': trade_dt.strftime('%Y-%m-%d'),
                'comment': comment
            })
            
        except Exception as e:
            print(f"⚠️ Error processing trade: {e}")
            continue
    
    return csv_rows

def save_to_csv(trades, output_path):
    """Save trades to CSV file"""
    
    if not trades:
        print("❌ No trades to save")
        return False
    
    fieldnames = [
        'ticker', 'asset_name', 'asset_type', 'transaction', 
        'amount_range', 'min_amount', 'max_amount',
        'politician', 'chamber', 'party', 
        'report_date', 'trade_date', 'comment'
    ]
    
    output_path = Path(output_path)
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trades)
    
    print(f"✅ Saved {len(trades):,} trades to {output_path}")
    
    # Print stats
    chambers = {}
    parties = {}
    trade_types = {}
    
    for trade in trades:
        chambers[trade['chamber']] = chambers.get(trade['chamber'], 0) + 1
        parties[trade['party']] = parties.get(trade['party'], 0) + 1
        trade_types[trade['transaction']] = trade_types.get(trade['transaction'], 0) + 1
    
    print("\n📊 Data Summary:")
    print(f"Total trades: {len(trades):,}")
    print(f"\nBy chamber: {chambers}")
    print(f"By party: {parties}")
    print(f"By type: {trade_types}")
    
    # Date range
    dates = sorted([trade['trade_date'] for trade in trades if trade['trade_date']])
    if dates:
        print(f"\nDate range: {dates[0]} to {dates[-1]}")
    
    return True

def main():
    print("🔥 Fetching Current Congressional Trades from Quiver Quant 🔥\n")
    
    # Fetch trades
    trades_raw = fetch_quiver_trades()
    
    if not trades_raw:
        print("\n❌ Failed to fetch trades")
        return 1
    
    # Convert to CSV format
    print(f"\n⏳ Converting {len(trades_raw):,} trades to CSV format...")
    trades_csv = convert_to_csv(trades_raw)
    
    if not trades_csv:
        print("❌ No valid trades after conversion")
        return 1
    
    print(f"✅ Successfully converted {len(trades_csv):,} trades")
    
    # Save to CSV
    output_path = Path(__file__).parent.parent / "output CSVs" / "quiver_trades_current.csv"
    success = save_to_csv(trades_csv, output_path)
    
    if success:
        print(f"\n✅ SUCCESS! Current political trades saved")
        print(f"📁 File: {output_path}")
        print(f"\n🚀 Next steps:")
        print(f"   1. Review the CSV: cat '{output_path}'")
        print(f"   2. Import to database: {Path(__file__).parent / 'import_to_db.py'} '{output_path}'")
        print(f"   3. Restart app: {Path(__file__).parent.parent / 'restart_webapp_stocks.sh'}")
        return 0
    else:
        return 1

if __name__ == "__main__":
    exit(main())
