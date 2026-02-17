#!/usr/bin/env python3
"""
Merge all 4 batch JSON files into a single expanded_insider_trades.json file.
Combines data from batch_1, batch_2, batch_3, and batch_4 insider trades.
"""

import json
from pathlib import Path

def merge_batches():
    """Merge all batch JSON files into one expanded dataset."""
    
    base_path = Path(__file__).parent.parent.parent / "output CSVs"
    
    # Load all 4 batches
    batch_files = [
        base_path / "batch_1_insider_trades.json",
        base_path / "batch_2_insider_trades.json",
        base_path / "batch_3_insider_trades.json",
        base_path / "batch_4_insider_trades.json"
    ]
    
    print("=" * 80)
    print("MERGING ALL BATCH FILES")
    print("=" * 80)
    print()
    
    all_data = []
    total_tickers = 0
    total_purchases = 0
    total_value = 0
    
    for i, batch_file in enumerate(batch_files, 1):
        print(f"Loading batch {i}: {batch_file.name}")
        
        with open(batch_file, 'r') as f:
            batch = json.load(f)
        
        batch_data = batch.get('data', [])
        batch_meta = batch.get('metadata', {})
        
        all_data.extend(batch_data)
        
        tickers = batch_meta.get('total_tickers', len(batch_data))
        purchases = batch_meta.get('total_purchases', 0)
        value = batch_meta.get('total_value', 0)
        
        total_tickers += tickers
        total_purchases += purchases
        total_value += value
        
        print(f"  ✓ Loaded: {tickers} tickers, {purchases:,} purchases, ${value:,.0f}")
        print()
    
    # Create combined output
    output = {
        'data': all_data,
        'metadata': {
            'total_tickers': total_tickers,
            'total_purchases': total_purchases,
            'total_value': total_value,
            'source': 'SEC + OpenInsider (all 10,388 SEC companies checked)',
            'time_period': '4 years (fd=1461)',
            'batches_merged': 4
        }
    }
    
    # Save combined file
    output_file = base_path / "expanded_insider_trades.json"
    
    print("=" * 80)
    print(f"Writing combined file: {output_file.name}")
    print("=" * 80)
    print()
    print(f"Total Tickers:    {total_tickers:,}")
    print(f"Total Purchases:  {total_purchases:,}")
    print(f"Total Value:      ${total_value:,.0f}")
    print()
    
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ Successfully merged all batches!")
    print(f"   Output: {output_file}")
    print()
    
    # Verify no duplicates
    tickers = [item['ticker'] for item in all_data]
    unique_tickers = set(tickers)
    
    if len(tickers) != len(unique_tickers):
        print(f"⚠️  WARNING: Found {len(tickers) - len(unique_tickers)} duplicate tickers!")
    else:
        print(f"✓ Verified: All {len(unique_tickers):,} tickers are unique (no duplicates)")
    
    return output_file

if __name__ == '__main__':
    merge_batches()
