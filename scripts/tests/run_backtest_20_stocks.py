#!/usr/bin/env python3
"""
Run card counting backtest on first 20 stocks and generate PDF
"""
import json
import sys
sys.path.append('/Users/sagiv.oron/Documents/scripts_playground/stocks/scripts/tests')
from backtest_card_counting_strategy import backtest_card_counting_strategy
import csv

# Load full data
json_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/top_monthly_insider_trades.json'
with open(json_path, 'r') as f:
    data = json.load(f)

# Keep only first 20 stocks
data['data'] = data['data'][:20]
data['total_tickers'] = 20
data['total_trades'] = sum(s['total_purchases'] for s in data['data'])

# Save to temp file
temp_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/top_20_insider_trades.json'
with open(temp_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f'✅ Created JSON with 20 stocks')
print(f'📊 Total tickers: {data["total_tickers"]}')
print(f'📈 Total trades: {data["total_trades"]}\n')

# Run backtest
results = backtest_card_counting_strategy(
    json_file=temp_path,
    initial_position_size=1000,
    base_adjustment=0.10
)

# Save results
if results:
    output_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_card_counting_results.csv'
    
    all_fields = set()
    for result in results:
        all_fields.update(result.keys())
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sorted(all_fields))
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n✅ Results saved to: {output_file}")
    print(f"📊 Total trades executed: {len(results)}")
