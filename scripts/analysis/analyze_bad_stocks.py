#!/usr/bin/env python3
"""
Deep analysis of what makes stocks fail in our strategy
"""
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

df = pd.read_csv('output CSVs/backtest_aggressive_daily_results.csv')

# Get ticker-level performance
ticker_perf = df.groupby('ticker').agg({
    'profit_loss': 'sum',
    'return_pct': ['count', 'mean', 'std'],
    'days_held': 'mean',
    'entry_price': 'mean',
    'exit_reason': lambda x: (x == 'stop_loss').sum() / len(x) * 100
}).round(2)

ticker_perf.columns = ['profit_loss', 'trades', 'avg_return', 'volatility', 'avg_days', 'avg_entry_price', 'stop_loss_pct']
ticker_perf['win_rate'] = df.groupby('ticker')['return_pct'].apply(lambda x: (x > 0).sum() / len(x) * 100).round(1)

# Split into winners and losers
losers = ticker_perf[ticker_perf['profit_loss'] < -100].sort_values('profit_loss')
winners = ticker_perf[ticker_perf['profit_loss'] > 1000].sort_values('profit_loss', ascending=False)

print("="*80)
print("WORST PERFORMERS (lost >$100):")
print("="*80)
print(f"{'Ticker':<8} {'Trades':<8} {'Avg Ret':<10} {'Win%':<8} {'StopLoss%':<12} {'AvgDays':<10} {'AvgPrice':<10} {'Loss':<10}")
print("-"*80)
for ticker, row in losers.iterrows():
    print(f"{ticker:<8} {int(row['trades']):<8} {row['avg_return']:>8.1f}%  {row['win_rate']:>6.1f}%  {row['stop_loss_pct']:>10.1f}%  {row['avg_days']:>8.0f}  ${row['avg_entry_price']:>8.2f}  ${abs(row['profit_loss']):>8.0f}")

print("\n" + "="*80)
print("BEST PERFORMERS (made >$1000):")
print("="*80)
print(f"{'Ticker':<8} {'Trades':<8} {'Avg Ret':<10} {'Win%':<8} {'StopLoss%':<12} {'AvgDays':<10} {'AvgPrice':<10} {'Profit':<10}")
print("-"*80)
for ticker, row in winners.iterrows():
    print(f"{ticker:<8} {int(row['trades']):<8} {row['avg_return']:>8.1f}%  {row['win_rate']:>6.1f}%  {row['stop_loss_pct']:>10.1f}%  {row['avg_days']:>8.0f}  ${row['avg_entry_price']:>8.2f}  ${row['profit_loss']:>8.0f}")

# Pattern analysis
print("\n" + "="*80)
print("PATTERN ANALYSIS:")
print("="*80)

print("\n🔍 PRICE ANALYSIS:")
print(f"  Losers avg entry price: ${losers['avg_entry_price'].mean():.2f}")
print(f"  Winners avg entry price: ${winners['avg_entry_price'].mean():.2f}")
penny_losers = (losers['avg_entry_price'] < 10).sum()
print(f"  Losers with price < $10: {penny_losers}/{len(losers)} ({penny_losers/len(losers)*100:.0f}%)")
penny_winners = (winners['avg_entry_price'] < 10).sum()
print(f"  Winners with price < $10: {penny_winners}/{len(winners)} ({penny_winners/len(winners)*100:.0f}%)")

print("\n🎯 WIN RATE ANALYSIS:")
print(f"  Losers avg win rate: {losers['win_rate'].mean():.1f}%")
print(f"  Winners avg win rate: {winners['win_rate'].mean():.1f}%")

print("\n⏱️  HOLDING PERIOD:")
print(f"  Losers avg days held: {losers['avg_days'].mean():.0f} days")
print(f"  Winners avg days held: {winners['avg_days'].mean():.0f} days")

print("\n🛑 STOP LOSS RATE:")
print(f"  Losers stop loss rate: {losers['stop_loss_pct'].mean():.1f}%")
print(f"  Winners stop loss rate: {winners['stop_loss_pct'].mean():.1f}%")

print("\n📊 VOLATILITY:")
print(f"  Losers avg volatility (std): {losers['volatility'].mean():.1f}%")
print(f"  Winners avg volatility (std): {winners['volatility'].mean():.1f}%")

# Check market cap for a few examples
print("\n" + "="*80)
print("MARKET CAP CHECK (sampling worst 5):")
print("="*80)
for ticker in losers.head(5).index:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        market_cap = info.get('marketCap', 0)
        if market_cap:
            if market_cap < 1e9:
                cap_str = f"${market_cap/1e6:.0f}M (SMALL)"
            elif market_cap < 10e9:
                cap_str = f"${market_cap/1e9:.1f}B (MID)"
            else:
                cap_str = f"${market_cap/1e9:.1f}B (LARGE)"
        else:
            cap_str = "N/A"
        print(f"  {ticker}: {cap_str}")
    except:
        print(f"  {ticker}: Error fetching data")

print("\n" + "="*80)
print("RECOMMENDATIONS:")
print("="*80)

# Filters that would work
penny_threshold = 15
losers_under_price = (losers['avg_entry_price'] < penny_threshold).sum()
total_losers = len(losers)

print(f"\n💡 FILTER: Price > ${penny_threshold}")
print(f"   Would eliminate {losers_under_price}/{total_losers} losing stocks")

low_win_rate = 35
losers_low_wr = (losers['win_rate'] < low_win_rate).sum()
print(f"\n💡 FILTER: Require win rate > {low_win_rate}% after first few trades")
print(f"   (Retrospective) Would catch {losers_low_wr}/{total_losers} losing stocks")

print(f"\n💡 FILTER: Require market cap > $500M")
print(f"   (Needs API check, but likely eliminates many penny stocks)")
