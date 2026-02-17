#!/usr/bin/env python3
"""Extract cache data for only the top 25 best and worst performers."""

import json
import pandas as pd

def main():
    print("Loading backtest results...")
    df = pd.read_csv('output CSVs/backtest_latest_results.csv')
    
    # Get top 25 best and worst
    top_25_best = df.nlargest(25, 'return_pct')['ticker'].unique()
    top_25_worst = df.nsmallest(25, 'return_pct')['ticker'].unique()
    
    # Combine into single list of unique tickers
    target_tickers = set(list(top_25_best) + list(top_25_worst))
    print(f"Target tickers: {len(target_tickers)} unique stocks")
    print(f"Tickers: {sorted(target_tickers)}")
    
    print("\nLoading full cache (this may take a moment)...")
    with open('output CSVs/yfinance_cache_full.json', 'r') as f:
        full_cache = json.load(f)
    
    print(f"Full cache has {len(full_cache['data'])} stocks")
    
    # Extract only the target tickers
    filtered_data = {}
    found = 0
    missing = []
    
    for ticker in target_tickers:
        if ticker in full_cache['data']:
            filtered_data[ticker] = full_cache['data'][ticker]
            found += 1
        else:
            missing.append(ticker)
    
    print(f"\nFound {found}/{len(target_tickers)} tickers in cache")
    if missing:
        print(f"Missing tickers: {missing}")
    
    # Create new cache with only top performers
    output = {
        'metadata': {
            'created': full_cache['metadata']['created'],
            'total_tickers': len(filtered_data),
            'source': 'extracted from top 25 best and worst performers',
            'date_range': 'entire_lifespan'
        },
        'data': filtered_data
    }
    
    # Save to new file - use allow_nan=False to convert NaN to null
    output_path = 'output CSVs/yfinance_cache_top_performers.json'
    print(f"\nSaving to {output_path}...")
    
    # Convert NaN values to None before saving
    import math
    def clean_nan(obj):
        if isinstance(obj, dict):
            return {k: clean_nan(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_nan(item) for item in obj]
        elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        else:
            return obj
    
    output_cleaned = clean_nan(output)
    
    with open(output_path, 'w') as f:
        json.dump(output_cleaned, f, indent=2)
    
    print(f"✅ Saved {len(filtered_data)} stocks to {output_path}")
    
    # Calculate file sizes
    import os
    original_size = os.path.getsize('output CSVs/yfinance_cache_full.json') / (1024**2)
    new_size = os.path.getsize(output_path) / (1024**2)
    print(f"\nFile size: {new_size:.1f} MB (vs {original_size:.1f} MB original)")
    print(f"Reduction: {(1 - new_size/original_size)*100:.1f}%")

if __name__ == '__main__':
    main()
