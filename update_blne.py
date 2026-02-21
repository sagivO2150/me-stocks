#!/usr/bin/env python3
"""Update BLNE data in the results JSON with anti-chasing filter applied"""
import json
from datetime import datetime

# Load the results file
with open('output CSVs/insider_conviction_all_stocks_results.json', 'r') as f:
    data = json.load(f)

# BLNE new data with anti-chasing: Only Nov 25 trade (Sept 8 was blocked)
blne_updated = {
    'ticker': 'BLNE',
    'company_name': 'Black Stone Minerals LP',
    'total_trades': 1,  # Only 1 trade now (Sept blocked)
    'winning_trades': 1,
    'losing_trades': 0,
    'win_rate': 100.0,
    'target_rate': 0.0,
    'total_profit': 158.19,
    'total_invested': 2000,
    'roi': 7.91,
    'avg_return': 7.91,
    'median_return': 7.91,
    'max_return': 7.91,
    'min_return': 7.91,
    'avg_days_held': 6.0,
    'trades': [
        {
            'entry_date': '2025-11-25',
            'entry_price': 1.77,
            'exit_date': '2025-12-01',
            'exit_price': 1.91,
            'target_price': 2.77,
            'days_held': 6,
            'return_pct': 7.91,
            'position_size': 2000,
            'profit_loss': 158.19,
            'sell_reason': 'atr_floor_phase_B',
            'target_reached': 'no',
            'peak_gain': 15.82,
            'buy_type': 'absorption_buy'
        }
    ]
}

# Update BLNE in all_results
updated = False
for i, stock in enumerate(data['all_results']):
    if stock['ticker'] == 'BLNE':
        data['all_results'][i] = blne_updated
        updated = True
        print(f"✅ Updated BLNE in all_results")
        break

if not updated:
    data['all_results'].append(blne_updated)
    print(f"✅ Added BLNE to all_results")

# Update timestamp
data['analysis_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Save
with open('output CSVs/insider_conviction_all_stocks_results.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"💾 Saved updated results")
print()
print(f"📊 BLNE now shows:")
print(f"   Total trades: 1 (Sept 8 blocked by anti-chasing filter)")
print(f"   Nov 25 entry: $1.77 → $1.91 = +7.91%")
print(f"   ROI: +7.91%")
