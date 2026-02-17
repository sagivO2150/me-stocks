#!/usr/bin/env python3
import json

# Check the full cache
with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/yfinance_cache_full.json', 'r') as f:
    full_cache = json.load(f)

# Check insider trades
with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/expanded_insider_trades.json', 'r') as f:
    insider_data = json.load(f)

total_insider_tickers = len(insider_data['data'])
cached_tickers = len(full_cache['data'])
missing = total_insider_tickers - cached_tickers

print('📊 CACHE STATUS:')
print('=' * 60)
print(f'Total stocks with insider trades: {total_insider_tickers}')
print(f'Stocks in yfinance cache: {cached_tickers}')
print(f'Missing from cache: {missing} ({(missing/total_insider_tickers)*100:.1f}%)')
print()
print(f'Progress: {(cached_tickers/total_insider_tickers)*100:.1f}% complete')
print()

# Sample a few stocks to verify data quality
sample_tickers = list(full_cache['data'].keys())[:5]
print('Sample stocks (verifying full lifespan data):')
for ticker in sample_tickers:
    stock = full_cache['data'][ticker]
    print(f'  {ticker}: {len(stock["dates"])} days ({stock["dates"][0]} to {stock["dates"][-1]})')

print()
if missing > 0:
    print(f'⚠️  Still need to fetch {missing} more stocks (60% remaining)')
    print(f'📦 Run fetch_yfinance_cache_full.py to continue')
else:
    print('✅ ALL DATA CACHED! Ready for local backtesting')
