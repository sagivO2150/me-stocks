#!/usr/bin/env python3
"""Get top 25 best and worst performers from backtest results."""

import pandas as pd

def main():
    # Load backtest results
    df = pd.read_csv('output CSVs/backtest_reputation_results.csv')
    
    print("=" * 80)
    print("TOP 25 BEST PERFORMERS")
    print("=" * 80)
    top_25 = df.nlargest(25, 'return_pct')
    for idx, row in top_25.iterrows():
        print(f"{row['ticker']:6} [{row['reputation_category']:9}] | ROI: {row['return_pct']:>7.2f}% | "
              f"${row['entry_price']:.2f} → ${row['exit_price']:.2f} | "
              f"{int(row['days_held'])} days | Peak: {row['peak_gain']:.1f}%")
    
    print("\n" + "=" * 80)
    print("TOP 25 WORST PERFORMERS")
    print("=" * 80)
    bottom_25 = df.nsmallest(25, 'return_pct')
    for idx, row in bottom_25.iterrows():
        print(f"{row['ticker']:6} [{row['reputation_category']:9}] | ROI: {row['return_pct']:>7.2f}% | "
              f"${row['entry_price']:.2f} → ${row['exit_price']:.2f} | "
              f"{int(row['days_held'])} days | Peak: {row['peak_gain']:.1f}%")
    
    # Save to JSON for webapp
    import json
    output = {
        'best_performers': top_25[['ticker', 'reputation_category', 'return_pct', 'entry_price', 
                                     'exit_price', 'days_held', 'peak_gain', 'exit_reason']].to_dict('records'),
        'worst_performers': bottom_25[['ticker', 'reputation_category', 'return_pct', 'entry_price', 
                                        'exit_price', 'days_held', 'peak_gain', 'exit_reason']].to_dict('records')
    }
    
    with open('output CSVs/top_performers.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("\n✅ Saved to: output CSVs/top_performers.json")

if __name__ == '__main__':
    main()
