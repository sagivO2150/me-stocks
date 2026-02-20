#!/usr/bin/env python3
"""
Quick script to relax the volume filter from 100K to 10K.
Instead of re-running the entire filter (30 min), we just check the 
excluded stocks and add back the ones with volume 10K-100K.
"""

import json
import yfinance as yf

print("=" * 80)
print("RELAXING VOLUME FILTER: 100K → 10K")
print("=" * 80)
print()

# Load original database
with open('output CSVs/expanded_insider_trades.json', 'r') as f:
    original_data = json.load(f)

# Load current filtered database (100K threshold)
with open('output CSVs/expanded_insider_trades_filtered.json', 'r') as f:
    filtered_data = json.load(f)

original_stocks = {s['ticker']: s for s in original_data['data']}
filtered_stocks = {s['ticker']: s for s in filtered_data['data']}

print(f"Original: {len(original_stocks)} stocks")
print(f"Currently filtered: {len(filtered_stocks)} stocks")
print()

# Find excluded tickers
excluded_tickers = set(original_stocks.keys()) - set(filtered_stocks.keys())
print(f"Excluded: {len(excluded_tickers)} stocks")
print()

# Check which excluded stocks should be added back (volume 10K-100K)
print("Checking excluded stocks for volume 10K-100K...")
added_back = 0
still_excluded_pnk = 0
still_excluded_low_vol = 0

for i, ticker in enumerate(excluded_tickers):
    if (i + 1) % 50 == 0:
        print(f"  Progress: {i+1}/{len(excluded_tickers)} ({added_back} added back)")
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        exchange = info.get('exchange', '')
        avg_volume = info.get('averageVolume', 0)
        
        # Still exclude PNK
        if exchange == 'PNK':
            still_excluded_pnk += 1
            continue
        
        # Add back if volume >= 10K
        if avg_volume >= 10000:
            filtered_stocks[ticker] = original_stocks[ticker]
            added_back += 1
        else:
            still_excluded_low_vol += 1
    except:
        still_excluded_low_vol += 1

print()
print("=" * 80)
print("RESULTS")
print("=" * 80)
print(f"Added back: {added_back} stocks (volume 10K-100K)")
print(f"Still excluded PNK: {still_excluded_pnk}")
print(f"Still excluded low volume: {still_excluded_low_vol}")
print(f"New filtered total: {len(filtered_stocks)}")
print()

# Save updated filtered database
updated_data = {
    'data': list(filtered_stocks.values()),
    'metadata': {
        'original_count': len(original_stocks),
        'filtered_count': len(filtered_stocks),
        'excluded_count': len(original_stocks) - len(filtered_stocks),
        'filter_criteria': 'OTC Pink (PNK) excluded + avg_volume >= 10,000',
        'filtered_date': filtered_data['metadata']['filtered_date'],
        'relaxed_date': '2026-02-20T' + __import__('datetime').datetime.now().strftime('%H:%M:%S')
    }
}

with open('output CSVs/expanded_insider_trades_filtered.json', 'w') as f:
    json.dump(updated_data, f, indent=2)

print("💾 Updated: output CSVs/expanded_insider_trades_filtered.json")
print("✅ Done!")
