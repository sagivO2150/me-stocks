#!/usr/bin/env python3
"""
Check why FTAI 2025-05-02 trade didn't get a buy signal
"""

import json
import pandas as pd
from datetime import datetime

# Load cache
print("Loading cache...")
with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/yfinance_cache_full.json', 'r') as f:
    cache = json.load(f)

# Convert FTAI data
ticker_data = cache['data']['FTAI']
df = pd.DataFrame({
    'Open': ticker_data['open'],
    'High': ticker_data['high'],
    'Low': ticker_data['low'],
    'Close': ticker_data['close'],
    'Volume': ticker_data['volume']
}, index=pd.to_datetime(ticker_data['dates']))

print(f"FTAI data: {len(df)} days from {df.index[0].date()} to {df.index[-1].date()}")
print()

# Check both trades
trades = [
    ('2023-03-15', 'Tuchman Martin', 1000000),
    ('2025-05-02', 'Multiple Insiders', 1008715)
]

for trade_date, insider, value in trades:
    print('='*80)
    print(f'Trade Date: {trade_date} | Insider: {insider} | Value: ${value/1000:.0f}K')
    print('='*80)
    
    entry_date = pd.Timestamp(trade_date)
    
    if entry_date not in df.index:
        print(f"❌ Date not in history!")
        print()
        continue
    
    entry_price = df.loc[entry_date, 'Close']
    print(f"Entry Price: ${entry_price:.2f}")
    
    # Check explosive catalyst (20%+ gain in previous 3-5 days)
    lookback = 5
    if len(df.loc[:entry_date]) >= lookback:
        window = df.loc[:entry_date].tail(lookback)
        low_price = window['Low'].min()
        gain_pct = ((entry_price - low_price) / low_price) * 100
        
        print(f"\nExplosive Catalyst Check (previous {lookback} days):")
        print(f"  Low in window: ${low_price:.2f}")
        print(f"  Entry price: ${entry_price:.2f}")
        print(f"  Gain: {gain_pct:.1f}%")
        print(f"  Has explosive catalyst (>20%): {'✅ YES' if gain_pct > 20 else '❌ NO'}")
        
        # Show the window
        print(f"\nPrice history (last {lookback} days):")
        for date, row in window.iterrows():
            print(f"  {date.date()}: Close=${row['Close']:.2f}, Low=${row['Low']:.2f}, High=${row['High']:.2f}")
    else:
        print(f"❌ Not enough history ({len(df.loc[:entry_date])} days)")
    
    print()
