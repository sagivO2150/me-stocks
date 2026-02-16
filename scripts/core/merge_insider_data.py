#!/usr/bin/env python3
"""
Merge full_history and top_monthly insider trades into one comprehensive dataset
"""

import json

# Load both files
with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/full_history_insider_trades.json', 'r') as f:
    full_history = json.load(f)

with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/top_monthly_insider_trades.json', 'r') as f:
    monthly = json.load(f)

# Create a dict of ticker -> stock data from full history
merged_data = {}
# full_history is now a list, not dict with 'data' key
history_stocks = full_history if isinstance(full_history, list) else full_history.get('data', [])
for stock in history_stocks:
    merged_data[stock['ticker']] = stock

# Add or merge monthly data
for stock in monthly['data']:
    ticker = stock['ticker']
    if ticker in merged_data:
        # Merge trades - add new trades from monthly that aren't in history
        existing_trades = merged_data[ticker]['trades']
        existing_trade_keys = set(
            (t['trade_date'], t['insider_name']) for t in existing_trades
        )
        
        for trade in stock['trades']:
            trade_key = (trade['trade_date'], trade['insider_name'])
            if trade_key not in existing_trade_keys:
                existing_trades.append(trade)
                print(f"  Added new trade for {ticker}: {trade['trade_date']} - {trade['insider_name']}")
    else:
        # New ticker not in history
        merged_data[ticker] = stock
        print(f"  Added new ticker: {ticker}")

# Convert back to list
final_data = {
    'data': list(merged_data.values()),
    'generated_at': '2026-02-14',
    'source': 'merged_full_history_and_monthly'
}

# Save merged file
output_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/merged_insider_trades.json'
with open(output_path, 'w') as f:
    json.dump(final_data, f, indent=2)

print(f"\n✅ Merged data saved to: {output_path}")
print(f"   Total tickers: {len(final_data['data'])}")
print(f"   From full history: {len(history_stocks)}")
print(f"   From monthly: {len(monthly['data'])}")
print(f"   From monthly: {len(monthly['data'])}")
