#!/usr/bin/env python3
"""
Analyze top 5 best vs worst performers to understand what went wrong.
"""

import json
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd

# Load results
with open('output CSVs/insider_conviction_all_stocks_results.json') as f:
    data = json.load(f)

print('=' * 80)
print('TOP 5 BEST PERFORMERS')
print('=' * 80)

for stock in data['top_25_best'][:5]:
    print(f"\n{stock['ticker']}: {stock['roi']:.1f}% ROI")
    print(f"  Trades: {stock['total_trades']}, Win Rate: {stock['win_rate']:.1f}%")
    print(f"  Avg Return: {stock['avg_return']:.1f}%, Median: {stock['median_return']:.1f}%")
    print(f"  Max: {stock['max_return']:.1f}%, Min: {stock['min_return']:.1f}%")
    print(f"  Avg days held: {stock['avg_days_held']:.1f}")
    
    for i, trade in enumerate(stock['trades'], 1):
        print(f"  Trade {i}: {trade['entry_date']} @ ${trade['entry_price']:.2f} → {trade['exit_date']} @ ${trade['exit_price']:.2f}")
        print(f"          = {trade['return_pct']:.1f}% in {trade['days_held']} days ({trade['sell_reason']})")
        print(f"          Buy type: {trade.get('buy_type', 'N/A')}, Peak gain: {trade['peak_gain']:.1f}%")

print('\n\n' + '=' * 80)
print('TOP 5 WORST PERFORMERS')
print('=' * 80)

for stock in data['top_25_worst'][:5]:
    print(f"\n{stock['ticker']}: {stock['roi']:.1f}% ROI")
    print(f"  Trades: {stock['total_trades']}, Win Rate: {stock['win_rate']:.1f}%")
    print(f"  Avg Return: {stock['avg_return']:.1f}%, Median: {stock['median_return']:.1f}%")
    print(f"  Max: {stock['max_return']:.1f}%, Min: {stock['min_return']:.1f}%")
    print(f"  Avg days held: {stock['avg_days_held']:.1f}")
    
    for i, trade in enumerate(stock['trades'], 1):
        print(f"  Trade {i}: {trade['entry_date']} @ ${trade['entry_price']:.2f} → {trade['exit_date']} @ ${trade['exit_price']:.2f}")
        print(f"          = {trade['return_pct']:.1f}% in {trade['days_held']} days ({trade['sell_reason']})")
        print(f"          Buy type: {trade.get('buy_type', 'N/A')}, Peak gain: {trade['peak_gain']:.1f}%")

print('\n\n' + '=' * 80)
print('ANALYZING PRICE ACTION PATTERNS')
print('=' * 80)

# Now let's look at specific patterns
print("\n\nBEST PERFORMERS ANALYSIS:")
print("-" * 80)

for stock in data['top_25_best'][:5]:
    ticker = stock['ticker']
    print(f"\n{ticker}:")
    
    for trade in stock['trades']:
        entry_date = pd.to_datetime(trade['entry_date'])
        exit_date = pd.to_datetime(trade['exit_date'])
        
        # Get price data around entry
        try:
            ticker_obj = yf.Ticker(ticker)
            start = entry_date - timedelta(days=30)
            end = exit_date + timedelta(days=5)
            hist = ticker_obj.history(start=start, end=end)
            
            if len(hist) > 0:
                # Price action before entry
                pre_entry = hist[hist.index < entry_date]
                if len(pre_entry) >= 5:
                    last_5_days = pre_entry.tail(5)
                    price_change_5d = ((last_5_days['Close'].iloc[-1] - last_5_days['Close'].iloc[0]) / 
                                      last_5_days['Close'].iloc[0]) * 100
                    print(f"  - 5-day trend before entry: {price_change_5d:.1f}%")
                
                # Price action during trade
                during_trade = hist[(hist.index >= entry_date) & (hist.index <= exit_date)]
                if len(during_trade) > 0:
                    peak_price = during_trade['Close'].max()
                    peak_gain = ((peak_price - trade['entry_price']) / trade['entry_price']) * 100
                    print(f"  - Peak gain during trade: {peak_gain:.1f}%")
                    print(f"  - Exit reason: {trade['exit_reason']}")
                    print(f"  - Buy type: {trade.get('buy_type', 'N/A')}")
        except Exception as e:
            print(f"  - Could not fetch price data: {e}")

print("\n\nWORST PERFORMERS ANALYSIS:")
print("-" * 80)

for stock in data['top_25_worst'][:5]:
    ticker = stock['ticker']
    print(f"\n{ticker}:")
    
    for trade in stock['trades']:
        entry_date = pd.to_datetime(trade['entry_date'])
        exit_date = pd.to_datetime(trade['exit_date'])
        
        # Get price data around entry
        try:
            ticker_obj = yf.Ticker(ticker)
            start = entry_date - timedelta(days=30)
            end = exit_date + timedelta(days=5)
            hist = ticker_obj.history(start=start, end=end)
            
            if len(hist) > 0:
                # Price action before entry
                pre_entry = hist[hist.index < entry_date]
                if len(pre_entry) >= 5:
                    last_5_days = pre_entry.tail(5)
                    price_change_5d = ((last_5_days['Close'].iloc[-1] - last_5_days['Close'].iloc[0]) / 
                                      last_5_days['Close'].iloc[0]) * 100
                    print(f"  - 5-day trend before entry: {price_change_5d:.1f}%")
                
                # Price action during trade
                during_trade = hist[(hist.index >= entry_date) & (hist.index <= exit_date)]
                if len(during_trade) > 0:
                    low_price = during_trade['Close'].min()
                    max_drawdown = ((low_price - trade['entry_price']) / trade['entry_price']) * 100
                    print(f"  - Max drawdown during trade: {max_drawdown:.1f}%")
                    print(f"  - Exit reason: {trade['exit_reason']}")
                    print(f"  - Buy type: {trade.get('buy_type', 'N/A')}")
        except Exception as e:
            print(f"  - Could not fetch price data: {e}")

print("\n\n" + "=" * 80)
print("KEY OBSERVATIONS TO LOOK FOR:")
print("=" * 80)
print("""
1. Entry timing: Did winners enter on confirmed momentum vs losers on false starts?
2. Insider conviction: More insiders = better results?
3. Buy type distribution: Shopping spree vs absorption buy success rates
4. Exit timing: Are we exiting winners too early or losers too late?
5. Price trends: Strong uptrends before entry vs weak/downtrends?
6. Holding period: Optimal days held for winners vs losers?
""")
