#!/usr/bin/env python3
"""Debug FTAI trades to see why pyramid entries aren't being created."""

import json
from datetime import datetime

# Load insider trades
with open('output CSVs/merged_insider_trades.json', 'r') as f:
    data = json.load(f)

ftai_trades = data.get('FTAI', [])
print(f"Total FTAI insider trades: {len(ftai_trades)}")
print()

# Look for the May 30, 2024 trade
print("FTAI insider trades around May 2024:")
print("=" * 80)
for trade in ftai_trades:
    date = trade.get('trade_date', '')
    if '2024-05' in date or '2024-06' in date:
        print(f"Date: {date}")
        print(f"  Name: {trade.get('insider_name')}")
        print(f"  Title: {trade.get('insider_title')}")
        print(f"  Value: ${trade.get('transaction_value', 0):,.0f}")
        print(f"  Type: {trade.get('transaction_type')}")
        
        # Check pyramid conditions
        is_csuite = any(role in trade.get('insider_title', '').upper() for role in ['CEO', 'CFO', 'COO', 'PRESIDENT', 'CHIEF'])
        is_large_buy = trade.get('transaction_value', 0) >= 500000
        
        print(f"  C-Suite: {is_csuite}")
        print(f"  Large Buy (>=$500K): {is_large_buy}")
        print(f"  Should Pyramid: {is_csuite and is_large_buy}")
        print()

# Load backtest results to see what actually happened
print("\nFTAI backtest results:")
print("=" * 80)
with open('output CSVs/backtest_latest_results.csv', 'r') as f:
    lines = f.readlines()
    
for line in lines[1:]:  # Skip header
    if line.startswith('FTAI,'):
        parts = line.strip().split(',')
        print(f"Entry Date: {parts[2]}")
        print(f"Entry Price: ${parts[4]}")
        print(f"Position Size: ${parts[9]}")
        print(f"Reputation: {parts[17]}")
        print()
