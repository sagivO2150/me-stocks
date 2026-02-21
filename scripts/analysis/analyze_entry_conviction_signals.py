#!/usr/bin/env python3
"""
Analyze entry conditions for winners vs losers.
Can we predict BEFORE entering whether a trade will succeed?

Signals to check:
1. Total insider investment amount
2. Number of insiders (clustering signal)
3. Fall percentage before the trade
4. Buy type (absorption vs shopping spree)
5. Time between insider buy and rise start (staleness)
"""
import json
import pandas as pd
from datetime import datetime

with open('output CSVs/insider_conviction_all_stocks_results.json') as f:
    data = json.load(f)

# Load the expanded trades data to get insider details
with open('output CSVs/expanded_insider_trades_filtered.json') as f:
    insider_data = json.load(f)

# Create lookup for insider trades by ticker
insider_lookup = {}
for stock in insider_data['data']:
    ticker = stock.get('ticker', '')
    if ticker:
        insider_lookup[ticker] = stock

# Collect all trades with entry conviction metrics
trades_analysis = []

for stock in data['all_results']:
    if 'trades' not in stock:
        continue
    
    ticker = stock['ticker']
    
    for trade in stock['trades']:
        # Skip end_of_period trades (incomplete data)
        if trade['sell_reason'] == 'end_of_period':
            continue
        
        # Look up insider trades for this ticker
        stock_data = insider_lookup.get(ticker)
        if not stock_data:
            continue
        
        # Find insider trades that occurred before this entry
        entry_date = pd.to_datetime(trade['entry_date'])
        
        # Get all insider trades before entry (within 60 days)
        relevant_insiders = []
        for insider_trade in stock_data.get('trades', []):
            insider_date = pd.to_datetime(insider_trade.get('trade_date', ''))
            if pd.isna(insider_date):
                continue
            
            days_before = (entry_date - insider_date).days
            if 0 <= days_before <= 60:
                # Parse insider value
                value_str = str(insider_trade.get('value', '0')).replace('$', '').replace('+', '').replace(',', '')
                try:
                    value = float(value_str)
                except:
                    value = 0
                
                relevant_insiders.append({
                    'date': insider_date,
                    'days_before': days_before,
                    'value': value,
                    'name': insider_trade.get('insider_name', ''),
                    'title': insider_trade.get('title', '')
                })
        
        if not relevant_insiders:
            continue
        
        # Calculate conviction signals
        total_investment = sum(abs(i['value']) for i in relevant_insiders)
        num_insiders = len(set(i['name'] for i in relevant_insiders))
        max_single_trade = max(abs(i['value']) for i in relevant_insiders)
        avg_days_before = sum(i['days_before'] for i in relevant_insiders) / len(relevant_insiders)
        
        # Classify as winner or loser
        is_winner = trade['return_pct'] > 0
        
        trades_analysis.append({
            'ticker': ticker,
            'entry_date': trade['entry_date'],
            'return_pct': trade['return_pct'],
            'days_held': trade['days_held'],
            'exit_reason': trade['sell_reason'],
            'buy_type': trade['buy_type'],
            'is_winner': is_winner,
            'total_investment': total_investment,
            'num_insiders': num_insiders,
            'max_single_trade': max_single_trade,
            'avg_days_before': avg_days_before,
            'num_insider_trades': len(relevant_insiders)
        })

# Convert to DataFrame for analysis
df = pd.DataFrame(trades_analysis)

print("=" * 80)
print("ENTRY CONVICTION ANALYSIS: Can we predict winners before entering?")
print("=" * 80)
print(f"Total trades analyzed: {len(df)}")
print(f"Winners: {df['is_winner'].sum()} ({df['is_winner'].sum() / len(df) * 100:.1f}%)")
print(f"Losers: {(~df['is_winner']).sum()} ({(~df['is_winner']).sum() / len(df) * 100:.1f}%)")
print()

# Split into winners and losers
winners = df[df['is_winner']]
losers = df[~df['is_winner']]

print("CONVICTION SIGNAL COMPARISON")
print("=" * 80)
print(f"{'Metric':<30} {'Winners (avg)':<20} {'Losers (avg)':<20} {'Difference':<15}")
print("-" * 80)

# Total investment
w_inv = winners['total_investment'].mean()
l_inv = losers['total_investment'].mean()
print(f"{'Total Insider Investment':<30} ${w_inv:>18,.0f} ${l_inv:>18,.0f} {(w_inv - l_inv) / l_inv * 100:>+13.1f}%")

# Number of insiders
w_num = winners['num_insiders'].mean()
l_num = losers['num_insiders'].mean()
print(f"{'Number of Insiders':<30} {w_num:>19.1f} {l_num:>19.1f} {(w_num - l_num) / l_num * 100:>+13.1f}%")

# Max single trade
w_max = winners['max_single_trade'].mean()
l_max = losers['max_single_trade'].mean()
print(f"{'Largest Single Trade':<30} ${w_max:>18,.0f} ${l_max:>18,.0f} {(w_max - l_max) / l_max * 100:>+13.1f}%")

# Staleness
w_stale = winners['avg_days_before'].mean()
l_stale = losers['avg_days_before'].mean()
print(f"{'Avg Days Before Entry':<30} {w_stale:>19.1f} {l_stale:>19.1f} {(w_stale - l_stale) / l_stale * 100:>+13.1f}%")

# Number of insider trades
w_trades = winners['num_insider_trades'].mean()
l_trades = losers['num_insider_trades'].mean()
print(f"{'Number of Insider Trades':<30} {w_trades:>19.1f} {l_trades:>19.1f} {(w_trades - l_trades) / l_trades * 100:>+13.1f}%")

print()
print("RETURN BY INVESTMENT LEVEL")
print("=" * 80)

# Group by investment buckets
investment_buckets = [0, 10000, 25000, 50000, 100000, 250000, 500000, float('inf')]
bucket_labels = ['<$10K', '$10-25K', '$25-50K', '$50-100K', '$100-250K', '$250-500K', '$500K+']

df['investment_bucket'] = pd.cut(df['total_investment'], bins=investment_buckets, labels=bucket_labels)

print(f"{'Investment Range':<15} {'Count':<8} {'Win Rate':<12} {'Avg Return':<15} {'Median Return':<15}")
print("-" * 80)

for bucket in bucket_labels:
    bucket_df = df[df['investment_bucket'] == bucket]
    if len(bucket_df) == 0:
        continue
    
    count = len(bucket_df)
    win_rate = bucket_df['is_winner'].sum() / count * 100
    avg_return = bucket_df['return_pct'].mean()
    median_return = bucket_df['return_pct'].median()
    
    print(f"{bucket:<15} {count:<8} {win_rate:>10.1f}% {avg_return:>+13.2f}% {median_return:>+13.2f}%")

print()
print("RETURN BY NUMBER OF INSIDERS")
print("=" * 80)

print(f"{'# Insiders':<15} {'Count':<8} {'Win Rate':<12} {'Avg Return':<15} {'Median Return':<15}")
print("-" * 80)

for num in sorted(df['num_insiders'].unique()):
    insiders_df = df[df['num_insiders'] == num]
    count = len(insiders_df)
    win_rate = insiders_df['is_winner'].sum() / count * 100
    avg_return = insiders_df['return_pct'].mean()
    median_return = insiders_df['return_pct'].median()
    
    print(f"{int(num):<15} {count:<8} {win_rate:>10.1f}% {avg_return:>+13.2f}% {median_return:>+13.2f}%")

print()
print("RETURN BY BUY TYPE")
print("=" * 80)

print(f"{'Buy Type':<20} {'Count':<8} {'Win Rate':<12} {'Avg Return':<15}")
print("-" * 80)

for buy_type in df['buy_type'].unique():
    type_df = df[df['buy_type'] == buy_type]
    count = len(type_df)
    win_rate = type_df['is_winner'].sum() / count * 100
    avg_return = type_df['return_pct'].mean()
    
    print(f"{buy_type:<20} {count:<8} {win_rate:>10.1f}% {avg_return:>+13.2f}%")

print()
print("RETURN BY STALENESS (Days Between Insider Buy and Entry)")
print("=" * 80)

staleness_buckets = [0, 7, 14, 21, 30, 45, 60]
staleness_labels = ['0-7d', '8-14d', '15-21d', '22-30d', '31-45d', '46-60d']

df['staleness_bucket'] = pd.cut(df['avg_days_before'], bins=staleness_buckets, labels=staleness_labels)

print(f"{'Staleness':<15} {'Count':<8} {'Win Rate':<12} {'Avg Return':<15} {'Median Return':<15}")
print("-" * 80)

for bucket in staleness_labels:
    bucket_df = df[df['staleness_bucket'] == bucket]
    if len(bucket_df) == 0:
        continue
    
    count = len(bucket_df)
    win_rate = bucket_df['is_winner'].sum() / count * 100
    avg_return = bucket_df['return_pct'].mean()
    median_return = bucket_df['return_pct'].median()
    
    print(f"{bucket:<15} {count:<8} {win_rate:>10.1f}% {avg_return:>+13.2f}% {median_return:>+13.2f}%")

print()
print("TOP 10 WINNERS - Entry Conviction Signals")
print("=" * 80)
top_winners = df.nlargest(10, 'return_pct')
print(f"{'Ticker':<8} {'Return':<10} {'Investment':<15} {'# Insiders':<12} {'Staleness':<12}")
print("-" * 80)
for _, row in top_winners.iterrows():
    print(f"{row['ticker']:<8} {row['return_pct']:>+8.1f}% ${row['total_investment']:>12,.0f} {int(row['num_insiders']):>11} {row['avg_days_before']:>10.1f}d")

print()
print("BOTTOM 10 LOSERS - Entry Conviction Signals")
print("=" * 80)
bottom_losers = df.nsmallest(10, 'return_pct')
print(f"{'Ticker':<8} {'Return':<10} {'Investment':<15} {'# Insiders':<12} {'Staleness':<12}")
print("-" * 80)
for _, row in bottom_losers.iterrows():
    print(f"{row['ticker']:<8} {row['return_pct']:>+8.1f}% ${row['total_investment']:>12,.0f} {int(row['num_insiders']):>11} {row['avg_days_before']:>10.1f}d")

print()
print("=" * 80)
print("RECOMMENDATIONS:")
print("=" * 80)

# Find optimal thresholds
high_conviction_min_investment = 50000
high_conviction_min_insiders = 2

high_conviction = df[(df['total_investment'] >= high_conviction_min_investment) | 
                     (df['num_insiders'] >= high_conviction_min_insiders)]

if len(high_conviction) > 0:
    hc_win_rate = high_conviction['is_winner'].sum() / len(high_conviction) * 100
    hc_avg_return = high_conviction['return_pct'].mean()
    
    print(f"High Conviction Filter: $50K+ OR 2+ insiders")
    print(f"  Trades: {len(high_conviction)} ({len(high_conviction) / len(df) * 100:.1f}% of total)")
    print(f"  Win Rate: {hc_win_rate:.1f}%")
    print(f"  Avg Return: {hc_avg_return:+.2f}%")
    print()

# Compare to low conviction
low_conviction = df[(df['total_investment'] < high_conviction_min_investment) & 
                    (df['num_insiders'] < high_conviction_min_insiders)]

if len(low_conviction) > 0:
    lc_win_rate = low_conviction['is_winner'].sum() / len(low_conviction) * 100
    lc_avg_return = low_conviction['return_pct'].mean()
    
    print(f"Low Conviction (would be filtered out):")
    print(f"  Trades: {len(low_conviction)} ({len(low_conviction) / len(df) * 100:.1f}% of total)")
    print(f"  Win Rate: {lc_win_rate:.1f}%")
    print(f"  Avg Return: {lc_avg_return:+.2f}%")
