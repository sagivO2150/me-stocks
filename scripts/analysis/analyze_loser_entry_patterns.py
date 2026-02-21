#!/usr/bin/env python3
"""
Analyze entry conditions for worst performers to find warning signs.
Goal: Find indicators that would prevent losses WITHOUT eliminating winners.
"""

import json
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd

# Load results
with open('output CSVs/insider_conviction_all_stocks_results.json') as f:
    data = json.load(f)

# Load full insider trades data
with open('output CSVs/expanded_insider_trades_filtered.json') as f:
    insider_data = json.load(f)

# Create lookup for insider trades by ticker
insider_lookup = {}
for stock in insider_data['data']:
    ticker = stock.get('ticker', '')
    if ticker:
        insider_lookup[ticker] = stock

print('=' * 80)
print('ANALYZING ENTRY CONDITIONS: WORST 5 vs BEST 5')
print('=' * 80)

def analyze_entry_conditions(stock_result, insider_stock_data):
    """Analyze conditions at the time of entry for a stock's trades."""
    ticker = stock_result['ticker']
    
    try:
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(period='max')
        
        if hist.empty:
            return None
        
        analysis = {
            'ticker': ticker,
            'roi': stock_result['roi'],
            'trades': []
        }
        
        # Convert hist index to timezone-naive at the start
        if hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)
        
        for trade in stock_result['trades']:
            entry_date = pd.to_datetime(trade['entry_date'])
            if hasattr(entry_date, 'tz_localize'):
                entry_date = entry_date.tz_localize(None)
            entry_price = trade['entry_price']
            buy_type = trade['buy_type']
            
            # Get price data before entry
            pre_entry = hist[hist.index < entry_date]
            if len(pre_entry) < 30:
                continue
            
            # Calculate metrics at entry time
            last_30_days = pre_entry.tail(30)
            last_90_days = pre_entry.tail(90)
            
            # Price volatility
            volatility_30d = last_30_days['Close'].std() / last_30_days['Close'].mean() * 100
            
            # Price trend before entry (30 days)
            price_change_30d = ((last_30_days['Close'].iloc[-1] - last_30_days['Close'].iloc[0]) / 
                               last_30_days['Close'].iloc[0]) * 100
            
            # Average volume
            avg_volume_30d = last_30_days['Volume'].mean()
            recent_volume = last_30_days['Volume'].iloc[-1]
            volume_ratio = recent_volume / avg_volume_30d if avg_volume_30d > 0 else 0
            
            # Historical price range (all time before entry)
            historical_high = pre_entry['Close'].max()
            historical_low = pre_entry['Close'].min()
            price_vs_high = ((entry_price - historical_high) / historical_high) * 100
            price_vs_low = ((entry_price - historical_low) / historical_low) * 100
            
            # Get insider trades leading to this entry
            insider_trades_before = []
            if insider_stock_data:
                for insider_trade in insider_stock_data.get('trades', []):
                    trade_date_str = insider_trade.get('trade_date', '')
                    if trade_date_str:
                        trade_date = pd.to_datetime(trade_date_str)
                        # Look for insider trades in the 90 days before entry
                        if entry_date - timedelta(days=90) <= trade_date < entry_date:
                            insider_trades_before.append({
                                'date': trade_date_str,
                                'value': insider_trade.get('value', 0),
                                'title': insider_trade.get('title', '')
                            })
            
            num_insiders = len(insider_trades_before)
            total_insider_value = sum(abs(float(str(t['value']).replace('$', '').replace('+', '').replace(',', ''))) 
                                     for t in insider_trades_before if t['value'])
            
            # Days since last insider trade
            days_since_last_insider = None
            if insider_trades_before:
                last_insider_date = max(pd.to_datetime(t['date']) for t in insider_trades_before)
                days_since_last_insider = (entry_date - last_insider_date).days
            
            trade_analysis = {
                'entry_date': trade['entry_date'],
                'entry_price': entry_price,
                'buy_type': buy_type,
                'return_pct': trade['return_pct'],
                'peak_gain': trade['peak_gain'],
                'days_held': trade['days_held'],
                'exit_reason': trade['sell_reason'],
                
                # Entry condition metrics
                'volatility_30d': round(volatility_30d, 2),
                'price_trend_30d': round(price_change_30d, 2),
                'volume_ratio': round(volume_ratio, 2),
                'price_vs_historical_high_pct': round(price_vs_high, 2),
                'price_vs_historical_low_pct': round(price_vs_low, 2),
                'num_insiders': num_insiders,
                'total_insider_value': round(total_insider_value, 2),
                'days_since_last_insider': days_since_last_insider,
                'avg_volume_30d': int(avg_volume_30d)
            }
            
            analysis['trades'].append(trade_analysis)
        
        return analysis
        
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

# Analyze worst 5
print('\n📉 WORST 5 PERFORMERS - ENTRY CONDITIONS')
print('-' * 80)

worst_analyses = []
for stock in data['top_25_worst'][:5]:
    ticker = stock['ticker']
    insider_stock = insider_lookup.get(ticker)
    
    analysis = analyze_entry_conditions(stock, insider_stock)
    if analysis:
        worst_analyses.append(analysis)

for analysis in worst_analyses:
    print(f"\n{analysis['ticker']}: {analysis['roi']:.1f}% ROI")
    for i, trade in enumerate(analysis['trades'], 1):
        print(f"  Trade {i}: Entry {trade['entry_date']} @ ${trade['entry_price']:.2f}")
        print(f"    Result: {trade['return_pct']:+.1f}% (peak: {trade['peak_gain']:.1f}%)")
        print(f"    30-day trend before entry: {trade['price_trend_30d']:+.1f}%")
        print(f"    Volatility: {trade['volatility_30d']:.1f}%")
        print(f"    Price vs all-time high: {trade['price_vs_historical_high_pct']:+.1f}%")
        print(f"    Volume ratio: {trade['volume_ratio']:.2f}x")
        print(f"    Insiders: {trade['num_insiders']} (${trade['total_insider_value']:,.0f} total)")
        print(f"    Days since last insider: {trade['days_since_last_insider']}")
        print(f"    Avg volume: {trade['avg_volume_30d']:,}")

# Analyze best 5
print('\n\n✅ BEST 5 PERFORMERS - ENTRY CONDITIONS')
print('-' * 80)

best_analyses = []
for stock in data['top_25_best'][:5]:
    ticker = stock['ticker']
    insider_stock = insider_lookup.get(ticker)
    
    analysis = analyze_entry_conditions(stock, insider_stock)
    if analysis:
        best_analyses.append(analysis)

for analysis in best_analyses:
    print(f"\n{analysis['ticker']}: {analysis['roi']:.1f}% ROI")
    for i, trade in enumerate(analysis['trades'], 1):
        print(f"  Trade {i}: Entry {trade['entry_date']} @ ${trade['entry_price']:.2f}")
        print(f"    Result: {trade['return_pct']:+.1f}% (peak: {trade['peak_gain']:.1f}%)")
        print(f"    30-day trend before entry: {trade['price_trend_30d']:+.1f}%")
        print(f"    Volatility: {trade['volatility_30d']:.1f}%")
        print(f"    Price vs all-time high: {trade['price_vs_historical_high_pct']:+.1f}%")
        print(f"    Volume ratio: {trade['volume_ratio']:.2f}x")
        print(f"    Insiders: {trade['num_insiders']} (${trade['total_insider_value']:,.0f} total)")
        print(f"    Days since last insider: {trade['days_since_last_insider']}")
        print(f"    Avg volume: {trade['avg_volume_30d']:,}")

# Statistical comparison
print('\n\n' + '=' * 80)
print('STATISTICAL COMPARISON')
print('=' * 80)

def get_stats(analyses):
    """Calculate average metrics across all trades."""
    all_trades = []
    for analysis in analyses:
        all_trades.extend(analysis['trades'])
    
    if not all_trades:
        return None
    
    return {
        'avg_volatility': sum(t['volatility_30d'] for t in all_trades) / len(all_trades),
        'avg_price_trend': sum(t['price_trend_30d'] for t in all_trades) / len(all_trades),
        'avg_volume_ratio': sum(t['volume_ratio'] for t in all_trades) / len(all_trades),
        'avg_price_vs_high': sum(t['price_vs_historical_high_pct'] for t in all_trades) / len(all_trades),
        'avg_num_insiders': sum(t['num_insiders'] for t in all_trades) / len(all_trades),
        'avg_insider_value': sum(t['total_insider_value'] for t in all_trades) / len(all_trades),
        'avg_days_since_insider': sum(t['days_since_last_insider'] for t in all_trades if t['days_since_last_insider']) / 
                                  len([t for t in all_trades if t['days_since_last_insider']]),
        'avg_volume': sum(t['avg_volume_30d'] for t in all_trades) / len(all_trades)
    }

worst_stats = get_stats(worst_analyses)
best_stats = get_stats(best_analyses)

if worst_stats and best_stats:
    print("\n                          WORST 5    |    BEST 5     |  DIFFERENCE")
    print("-" * 80)
    print(f"30-day Trend:           {worst_stats['avg_price_trend']:+7.1f}%   |  {best_stats['avg_price_trend']:+7.1f}%   |  {best_stats['avg_price_trend'] - worst_stats['avg_price_trend']:+7.1f}%")
    print(f"Volatility:              {worst_stats['avg_volatility']:6.1f}%   |   {best_stats['avg_volatility']:6.1f}%   |   {best_stats['avg_volatility'] - worst_stats['avg_volatility']:+6.1f}%")
    print(f"Volume Ratio:              {worst_stats['avg_volume_ratio']:4.2f}x   |     {best_stats['avg_volume_ratio']:4.2f}x   |     {best_stats['avg_volume_ratio'] - worst_stats['avg_volume_ratio']:+4.2f}x")
    print(f"Price vs ATH:           {worst_stats['avg_price_vs_high']:+7.1f}%   |  {best_stats['avg_price_vs_high']:+7.1f}%   |  {best_stats['avg_price_vs_high'] - worst_stats['avg_price_vs_high']:+7.1f}%")
    print(f"Num Insiders:              {worst_stats['avg_num_insiders']:5.1f}    |     {best_stats['avg_num_insiders']:5.1f}    |     {best_stats['avg_num_insiders'] - worst_stats['avg_num_insiders']:+5.1f}")
    print(f"Insider Value:        ${worst_stats['avg_insider_value']:7,.0f}   | ${best_stats['avg_insider_value']:7,.0f}   | ${best_stats['avg_insider_value'] - worst_stats['avg_insider_value']:+7,.0f}")
    print(f"Days Since Insider:        {worst_stats['avg_days_since_insider']:5.1f}    |     {best_stats['avg_days_since_insider']:5.1f}    |     {best_stats['avg_days_since_insider'] - worst_stats['avg_days_since_insider']:+5.1f}")
    print(f"Avg Volume:            {worst_stats['avg_volume']:7,.0f}   |  {best_stats['avg_volume']:7,.0f}   |  {best_stats['avg_volume'] - worst_stats['avg_volume']:+7,.0f}")

print('\n\n' + '=' * 80)
print('KEY INSIGHTS - POTENTIAL FILTERS')
print('=' * 80)

print("""
Looking for filters that would:
✅ Eliminate losers
❌ NOT eliminate winners

Potential warning signs to test:
1. Volume: Low average volume might indicate illiquid/risky stocks
2. Volatility: Extremely high volatility = unstable
3. Price vs ATH: Buying near all-time highs vs deep in a hole
4. Insider recency: Old insider trades (>60 days) = stale signal
5. Trend before entry: Already declining when we enter?
6. Number of insiders: Single insider vs multiple = conviction level

Next step: Test these as filters on full dataset to see impact.
""")
