#!/usr/bin/env python3
"""
One-time script to filter out garbage stocks from the database.
Removes OTC Pink stocks and illiquid stocks (< 100K avg volume).

This creates a new filtered database file that the backtest can use.
Run this ONCE when the database is updated, not during every backtest.

USAGE:
  .venv/bin/python scripts/utils/filter_garbage_stocks.py
"""

import json
import yfinance as yf
from datetime import datetime


def main():
    print("=" * 80)
    print("FILTERING GARBAGE STOCKS FROM DATABASE")
    print("=" * 80)
    print()
    
    # Load the full database
    input_file = 'output CSVs/expanded_insider_trades.json'
    print(f"📂 Loading: {input_file}")
    
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    all_stocks = data.get('data', [])
    total_stocks = len(all_stocks)
    print(f"   ✓ Loaded {total_stocks} stocks")
    print()
    
    # Filter stocks
    filtered_stocks = []
    excluded_count = 0
    excluded_reasons = {
        'PNK': 0,
        'low_volume': 0,
        'api_error': 0
    }
    
    print("🔍 Filtering stocks...")
    print("   Excluding: OTC Pink (PNK) + stocks with < 10K avg daily volume")
    print()
    
    for i, stock in enumerate(all_stocks):
        ticker = stock.get('ticker', '')
        
        # Progress indicator
        if (i + 1) % 100 == 0:
            print(f"   Progress: {i+1}/{total_stocks} ({excluded_count} excluded so far)")
        
        try:
            # Fetch exchange and volume info
            yf_stock = yf.Ticker(ticker)
            info = yf_stock.info
            exchange = info.get('exchange', '')
            avg_volume = info.get('averageVolume', 0)
            
            # Filter criteria
            if exchange == 'PNK':
                excluded_count += 1
                excluded_reasons['PNK'] += 1
                continue
            
            if avg_volume < 10000:
                excluded_count += 1
                excluded_reasons['low_volume'] += 1
                continue
            
            # Stock passed filters
            filtered_stocks.append(stock)
            
        except Exception as e:
            # If we can't get info, exclude to be safe
            excluded_count += 1
            excluded_reasons['api_error'] += 1
            continue
    
    print()
    print("=" * 80)
    print("FILTERING RESULTS")
    print("=" * 80)
    print(f"Original stocks: {total_stocks}")
    print(f"Filtered stocks: {len(filtered_stocks)}")
    print(f"Excluded: {excluded_count}")
    print()
    print("Exclusion breakdown:")
    print(f"  - OTC Pink (PNK): {excluded_reasons['PNK']}")
    print(f"  - Low volume (< 100K): {excluded_reasons['low_volume']}")
    print(f"  - API errors: {excluded_reasons['api_error']}")
    print()
    
    # Save filtered database
    output_file = 'output CSVs/expanded_insider_trades_filtered.json'
    filtered_data = {
        'data': filtered_stocks,
        'metadata': {
            'original_count': total_stocks,
            'filtered_count': len(filtered_stocks),
            'excluded_count': excluded_count,
            'exclusion_reasons': excluded_reasons,
            'filter_criteria': 'OTC Pink (PNK) excluded + avg_volume >= 10,000',
            'filtered_date': datetime.now().isoformat()
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(filtered_data, f, indent=2)
    
    print(f"💾 Saved filtered database: {output_file}")
    print()
    print("✅ Done! Update the backtest script to use the filtered database.")


if __name__ == "__main__":
    main()
