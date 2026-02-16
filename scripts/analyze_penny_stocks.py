#!/usr/bin/env python3
"""Analyze penny stock performance to see if insider buys are a stronger signal"""

import pandas as pd

# Load current results (percentage-based)
df = pd.read_csv('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_latest_results.csv')

# Find penny stocks (entry price < $5)
penny_stocks = df[df['entry_price'] < 5.0].copy()

print(f"\n{'='*80}")
print(f"PENNY STOCK ANALYSIS (Entry Price < $5)")
print(f"{'='*80}\n")

print(f"Total Penny Stock Trades: {len(penny_stocks)}")
print(f"Percentage of All Trades: {len(penny_stocks) / len(df) * 100:.1f}%\n")

# Performance comparison
print(f"PENNY STOCKS vs REGULAR STOCKS:")
print(f"-" * 80)
regular_stocks = df[df['entry_price'] >= 5.0]

penny_roi = penny_stocks['profit_loss'].sum() / penny_stocks['amount_invested'].sum() * 100
regular_roi = regular_stocks['profit_loss'].sum() / regular_stocks['amount_invested'].sum() * 100

print(f"Penny Stocks ROI: {penny_roi:+.2f}%")
print(f"Regular Stocks ROI: {regular_roi:+.2f}%\n")

penny_win_rate = len(penny_stocks[penny_stocks['return_pct'] > 0]) / len(penny_stocks) * 100
regular_win_rate = len(regular_stocks[regular_stocks['return_pct'] > 0]) / len(regular_stocks) * 100

print(f"Penny Win Rate: {penny_win_rate:.1f}%")
print(f"Regular Win Rate: {regular_win_rate:.1f}%\n")

print(f"Penny Avg Return: {penny_stocks['return_pct'].mean():+.2f}%")
print(f"Regular Avg Return: {regular_stocks['return_pct'].mean():+.2f}%\n")

print(f"Penny Avg Days Held: {penny_stocks['days_held'].mean():.0f} days")
print(f"Regular Avg Days Held: {regular_stocks['days_held'].mean():.0f} days\n")

# Show worst penny stock losses
print(f"\n{'='*80}")
print(f"WORST PENNY STOCK LOSSES (Current Strategy)")
print(f"{'='*80}\n")
worst_penny = penny_stocks.nsmallest(10, 'return_pct')[['ticker', 'entry_date', 'entry_price', 'exit_price', 'return_pct', 'days_held', 'exit_reason']]
print(worst_penny.to_string(index=False))

# Show best penny stock gains
print(f"\n{'='*80}")
print(f"BEST PENNY STOCK GAINS (Current Strategy)")
print(f"{'='*80}\n")
best_penny = penny_stocks.nlargest(10, 'return_pct')[['ticker', 'entry_date', 'entry_price', 'exit_price', 'return_pct', 'days_held', 'exit_reason']]
print(best_penny.to_string(index=False))

# Check if penny stocks that were held longer did better
print(f"\n{'='*80}")
print(f"PENNY STOCKS: HOLD TIME vs RETURNS")
print(f"{'='*80}\n")

penny_short = penny_stocks[penny_stocks['days_held'] <= 30]
penny_medium = penny_stocks[(penny_stocks['days_held'] > 30) & (penny_stocks['days_held'] <= 90)]
penny_long = penny_stocks[penny_stocks['days_held'] > 90]

print(f"Short Hold (≤30 days): {len(penny_short)} trades, avg return: {penny_short['return_pct'].mean():+.2f}%")
print(f"Medium Hold (31-90 days): {len(penny_medium)} trades, avg return: {penny_medium['return_pct'].mean():+.2f}%")
print(f"Long Hold (>90 days): {len(penny_long)} trades, avg return: {penny_long['return_pct'].mean():+.2f}%")

# Distribution analysis
print(f"\n{'='*80}")
print(f"PENNY STOCK RETURN DISTRIBUTION")
print(f"{'='*80}\n")

ranges = [
    (-100, -20, "Massive Loss"),
    (-20, -10, "Bad Loss"),
    (-10, 0, "Small Loss"),
    (0, 20, "Small Win"),
    (20, 50, "Good Win"),
    (50, 100, "Great Win"),
    (100, float('inf'), "Explosive Win")
]

for min_ret, max_ret, label in ranges:
    count = len(penny_stocks[(penny_stocks['return_pct'] >= min_ret) & (penny_stocks['return_pct'] < max_ret)])
    pct = count / len(penny_stocks) * 100 if len(penny_stocks) > 0 else 0
    print(f"{label:20s}: {count:3d} trades ({pct:5.1f}%)")
