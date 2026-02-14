#!/usr/bin/env python3
import json
import yfinance as yf
from datetime import datetime, timedelta

# Load THS trades
with open('output CSVs/merged_insider_trades.json', 'r') as f:
    data = json.load(f)
ths = next((s for s in data['data'] if s['ticker'] == 'THS'), None)

print('THS Insider Trades:')
for t in ths['trades']:
    print(f"  {t['trade_date']}: {t['insider_name']} - {t['value']}")

# Check backtest date range
print('\nBacktest period: 2022-03-16 to 2026-02-13')
print('THS trades in that range:')
in_range = [t for t in ths['trades'] 
            if '2022-03-16' <= t['trade_date'] <= '2026-02-13']
print(f"  {len(in_range)} trades")
for t in in_range:
    print(f"    {t['trade_date']}")

# Check if stock data loads
print('\nChecking if THS data loads in backtest:')
ticker = yf.Ticker('THS')
df = ticker.history(start='2022-03-16', end='2026-02-14')
print(f"  Rows: {len(df)}")
if len(df) > 0:
    print(f"  First: {df.index[0].strftime('%Y-%m-%d')}")
    print(f"  Last: {df.index[-1].strftime('%Y-%m-%d')}")
