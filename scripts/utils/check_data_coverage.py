#!/usr/bin/env python3
"""Check data coverage between insider trades and yfinance cache."""

import json
from datetime import datetime

def main():
    # Load insider trades
    with open('output CSVs/expanded_insider_trades.json', 'r') as f:
        insider_json = json.load(f)
        insider_data = insider_json.get('data', insider_json)  # Handle both formats

    # Load yfinance cache
    with open('output CSVs/yfinance_cache_full.json', 'r') as f:
        yfinance_cache = json.load(f)

    print('='*60)
    print('INSIDER TRADES DATA:')
    print('='*60)
    
    # Count all individual trades across all tickers
    total_trades = sum(len(stock_entry['trades']) for stock_entry in insider_data)
    print(f'Total insider trades: {total_trades:,}')
    
    unique_tickers = set(stock_entry["ticker"] for stock_entry in insider_data)
    print(f'Unique tickers with insider trades: {len(unique_tickers):,}')
    
    # Get date range from all trades
    all_trade_dates = []
    for stock_entry in insider_data:
        for trade in stock_entry['trades']:
            try:
                date_str = trade.get('trade_date', trade.get('transaction_date', ''))
                if date_str:
                    all_trade_dates.append(datetime.strptime(date_str, '%Y-%m-%d'))
            except:
                pass
    
    if all_trade_dates:
        print(f'Date range: {min(all_trade_dates).date()} to {max(all_trade_dates).date()}')
    print()

    print('='*60)
    print('YFINANCE CACHE DATA:')
    print('='*60)
    print(f'Total stocks with price history: {len(yfinance_cache["data"]):,}')
    print(f'Cache created: {yfinance_cache["metadata"]["created"]}')
    print(f'Date range: {yfinance_cache["metadata"]["date_range"]}')
    print()

    # Check coverage
    cached_tickers = set(yfinance_cache['data'].keys())
    missing_from_cache = unique_tickers - cached_tickers

    print('='*60)
    print('COVERAGE ANALYSIS:')
    print('='*60)
    print(f'Tickers with insider trades: {len(unique_tickers):,}')
    print(f'Tickers with price history: {len(cached_tickers):,}')
    print(f'Missing from cache: {len(missing_from_cache):,}')
    coverage_pct = len(cached_tickers)/len(unique_tickers)*100
    print(f'Coverage: {coverage_pct:.2f}%')
    print()

    if missing_from_cache:
        print(f'Missing tickers ({len(missing_from_cache)}):')
        for ticker in sorted(list(missing_from_cache))[:30]:
            print(f'  - {ticker}')
        if len(missing_from_cache) > 30:
            print(f'  ... and {len(missing_from_cache) - 30} more')
    print()

    # Check sample price history ranges
    print('='*60)
    print('SAMPLE PRICE HISTORY DATE RANGES:')
    print('='*60)
    sample_tickers = sorted(list(cached_tickers))[:10]
    for ticker in sample_tickers:
        stock_data = yfinance_cache['data'][ticker]
        if stock_data['dates']:
            num_days = len(stock_data['dates'])
            print(f'{ticker:6} : {stock_data["dates"][0]} to {stock_data["dates"][-1]} ({num_days:,} days)')
        else:
            print(f'{ticker:6} : NO DATA')

if __name__ == '__main__':
    main()
