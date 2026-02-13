#!/usr/bin/env python3
"""
Trailing Stop Loss Strategy Backtester
========================================
Tests the strategy: "Buy on peak purchases, hold as long as it goes up, 
and increase stop loss by 1% for every 10% profit gained"

Strategy Rules:
1. Identify "peak purchases" - large purchases relative to insider's historical behavior
2. Buy at the FILING date (2 business days after transaction date)
3. Start with 5% stop loss
4. For every 10% profit gained, increase stop loss by 1% (from the peak price)
5. Hold indefinitely until stop loss triggers

Example:
- Buy at $10, stop loss at $9.50 (5%)
- Stock hits $11 (10% gain) → stop loss becomes $10.34 (6% from peak of $11)
- Stock hits $13 (30% gain) → stop loss becomes $11.96 (8% from peak of $13)
- Stock hits $20 (100% gain) → stop loss becomes $17.00 (15% from peak of $20)
- Stock drops to $17 → EXIT with +70% gain
"""

import json
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import sys
from collections import defaultdict


def get_business_days_later(date_str, days=2):
    """Add N business days to a date"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    business_days_added = 0
    current_date = date
    
    while business_days_added < days:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:
            business_days_added += 1
    
    return current_date.strftime('%Y-%m-%d')


def parse_value(value_str):
    """Convert '+$69,297,690' to 69297690.0"""
    if not value_str:
        return 0.0
    cleaned = value_str.replace('+', '').replace('$', '').replace(',', '').replace('-', '')
    try:
        return float(cleaned)
    except:
        return 0.0


def identify_peak_purchases(trades, threshold_percentile=75):
    """
    Identify peak purchases for each insider.
    A peak purchase is one in the top 25% of that insider's purchase values.
    """
    insider_trades = defaultdict(list)
    for trade in trades:
        if trade.get('value', '').startswith('+'):
            insider_name = trade.get('insider_name', '')
            value = parse_value(trade.get('value', '0'))
            insider_trades[insider_name].append({
                'trade': trade,
                'value': value
            })
    
    peak_purchases = []
    for insider_name, purchases in insider_trades.items():
        if len(purchases) == 0:
            continue
        
        values = [p['value'] for p in purchases]
        
        if len(purchases) <= 2:
            peak_purchases.extend([p['trade'] for p in purchases])
            continue
        
        threshold = pd.Series(values).quantile(threshold_percentile / 100.0)
        
        for purchase in purchases:
            if purchase['value'] >= threshold:
                peak_purchases.append(purchase['trade'])
    
    return peak_purchases


def calculate_stop_loss_pct(profit_pct, base_stop_loss=0.05):
    """
    Calculate trailing stop loss percentage based on profit.
    For every 10% profit, increase stop loss by 1%.
    
    Examples:
    - 0% profit → 5% stop loss
    - 10% profit → 6% stop loss
    - 50% profit → 10% stop loss
    - 100% profit → 15% stop loss
    """
    additional_stop = (profit_pct // 10) * 0.01  # +1% for every 10% profit
    return base_stop_loss + additional_stop


def simulate_trailing_stop_trade(ticker, entry_date, base_stop_loss=0.05, max_days=365):
    """
    Simulate buying at entry_date with trailing stop loss that increases with profit.
    
    Returns:
        dict with: success, entry_price, exit_price, return_pct, exit_reason, days_held, 
                   peak_price, peak_return_pct, max_stop_loss_pct
    """
    try:
        entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
        start_date = (entry_dt - timedelta(days=5)).strftime('%Y-%m-%d')
        
        # Get data until today or max holding period
        today = datetime.now()
        max_end_date = entry_dt + timedelta(days=max_days)
        end_date = min(today, max_end_date).strftime('%Y-%m-%d')
        
        stock = yf.Ticker(ticker)
        history = stock.history(start=start_date, end=end_date)
        
        if history.empty:
            return {'success': False, 'error': 'No price data'}
        
        history.index = pd.to_datetime(history.index).strftime('%Y-%m-%d')
        
        if entry_date not in history.index:
            available_dates = sorted([d for d in history.index if d >= entry_date])
            if not available_dates:
                return {'success': False, 'error': 'No price data after entry date'}
            entry_date = available_dates[0]
        
        entry_price = history.loc[entry_date, 'Close']
        
        # Track the highest price (peak) and current stop loss
        peak_price = entry_price
        current_stop_loss_pct = base_stop_loss
        stop_loss_price = entry_price * (1 - current_stop_loss_pct)
        
        days_after_entry = [d for d in history.index if d >= entry_date]
        
        for i, date in enumerate(days_after_entry[1:], 1):
            low_price = history.loc[date, 'Low']
            high_price = history.loc[date, 'High']
            close_price = history.loc[date, 'Close']
            
            # Update peak if we hit a new high
            if high_price > peak_price:
                peak_price = high_price
                
                # Calculate profit from entry to peak
                profit_pct = ((peak_price - entry_price) / entry_price) * 100
                
                # Update stop loss based on profit
                current_stop_loss_pct = calculate_stop_loss_pct(profit_pct, base_stop_loss)
                
                # Stop loss is calculated from the peak, not entry
                stop_loss_price = peak_price * (1 - current_stop_loss_pct)
            
            # Check if stop loss hit
            if low_price <= stop_loss_price:
                # Exit at stop loss price
                return_pct = ((stop_loss_price - entry_price) / entry_price) * 100
                peak_return_pct = ((peak_price - entry_price) / entry_price) * 100
                
                return {
                    'success': True,
                    'entry_price': round(entry_price, 2),
                    'exit_price': round(stop_loss_price, 2),
                    'return_pct': round(return_pct, 2),
                    'exit_reason': 'trailing_stop_loss',
                    'days_held': i,
                    'peak_price': round(peak_price, 2),
                    'peak_return_pct': round(peak_return_pct, 2),
                    'max_stop_loss_pct': round(current_stop_loss_pct * 100, 1)
                }
        
        # If we're still holding at end of data
        last_date = days_after_entry[-1]
        exit_price = history.loc[last_date, 'Close']
        return_pct = ((exit_price - entry_price) / entry_price) * 100
        peak_return_pct = ((peak_price - entry_price) / entry_price) * 100
        
        return {
            'success': True,
            'entry_price': round(entry_price, 2),
            'exit_price': round(exit_price, 2),
            'return_pct': round(return_pct, 2),
            'exit_reason': 'still_holding',
            'days_held': len(days_after_entry) - 1,
            'peak_price': round(peak_price, 2),
            'peak_return_pct': round(peak_return_pct, 2),
            'max_stop_loss_pct': round(current_stop_loss_pct * 100, 1)
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def backtest_trailing_stop_strategy(json_file, threshold_percentile=75, base_stop_loss=0.05, 
                                     max_days=365, use_filing_delay=True):
    """
    Backtest the trailing stop loss strategy across all stocks.
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    results = []
    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    still_holding = 0
    total_return = 0.0
    
    print(f"{'='*80}")
    print(f"TRAILING STOP LOSS STRATEGY BACKTEST")
    print(f"{'='*80}")
    print(f"Parameters:")
    print(f"  - Peak threshold: Top {100-threshold_percentile}% of insider's historical purchases")
    print(f"  - Initial stop loss: {base_stop_loss*100}%")
    print(f"  - Stop loss increase: +1% for every 10% profit gained")
    print(f"  - Max hold period: {max_days} days")
    print(f"  - Filing delay simulation: {'Yes (add 2 business days)' if use_filing_delay else 'No'}")
    print(f"\n{'='*80}\n")
    
    for stock_data in data['data']:
        ticker = stock_data['ticker']
        company = stock_data['company_name']
        trades = stock_data['trades']
        
        peak_purchases = identify_peak_purchases(trades, threshold_percentile)
        
        if not peak_purchases:
            continue
        
        print(f"\n{ticker} - {company}")
        print(f"  Found {len(peak_purchases)} peak purchase(s)")
        
        for trade in peak_purchases:
            trade_date = trade['trade_date']
            insider = trade['insider_name']
            value = trade['value']
            
            entry_date = get_business_days_later(trade_date, 2) if use_filing_delay else trade_date
            
            print(f"\n  Peak Purchase: {insider} on {trade_date} ({value})")
            print(f"    Entry Date: {entry_date}")
            
            result = simulate_trailing_stop_trade(ticker, entry_date, base_stop_loss, max_days)
            
            if result['success']:
                total_trades += 1
                return_pct = result['return_pct']
                total_return += return_pct
                
                if result['exit_reason'] == 'still_holding':
                    still_holding += 1
                    emoji = "📊"
                elif return_pct > 0:
                    winning_trades += 1
                    emoji = "✅"
                else:
                    losing_trades += 1
                    emoji = "❌"
                
                print(f"    {emoji} Entry: ${result['entry_price']} | "
                      f"Peak: ${result['peak_price']} (+{result['peak_return_pct']:.1f}%) | "
                      f"Exit: ${result['exit_price']} ({result['return_pct']:+.2f}%)")
                print(f"       Days held: {result['days_held']} | "
                      f"Exit: {result['exit_reason']} | "
                      f"Max stop loss: {result['max_stop_loss_pct']}%")
                
                results.append({
                    'ticker': ticker,
                    'company': company,
                    'insider': insider,
                    'trade_date': trade_date,
                    'entry_date': entry_date,
                    'value': value,
                    **result
                })
            else:
                print(f"    ⚠️  Could not simulate: {result.get('error', 'Unknown error')}")
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"Total Trades: {total_trades}")
    
    completed_trades = total_trades - still_holding
    if completed_trades > 0:
        print(f"Completed Trades: {completed_trades}")
        print(f"  Winning: {winning_trades} ({winning_trades/completed_trades*100:.1f}%)")
        print(f"  Losing: {losing_trades} ({losing_trades/completed_trades*100:.1f}%)")
    
    if still_holding > 0:
        print(f"Still Holding: {still_holding} positions")
    
    if total_trades > 0:
        avg_return = total_return / total_trades
        print(f"\nAverage Return per Trade: {avg_return:+.2f}%")
        print(f"Total Return (sum): {total_return:+.2f}%")
        
        if results:
            returns = [r['return_pct'] for r in results if 'return_pct' in r]
            print(f"\nBest Trade: {max(returns):+.2f}%")
            print(f"Worst Trade: {min(returns):+.2f}%")
            
            best_trade = max(results, key=lambda x: x.get('return_pct', -999))
            worst_trade = min(results, key=lambda x: x.get('return_pct', 999))
            
            print(f"\n🏆 Best Example: {best_trade['ticker']} - {best_trade['insider']} on {best_trade['trade_date']}")
            print(f"   Entry: ${best_trade['entry_price']} → Peak: ${best_trade['peak_price']} → Exit: ${best_trade['exit_price']}")
            print(f"   Return: {best_trade['return_pct']:+.2f}% | Held: {best_trade['days_held']} days | {best_trade['exit_reason']}")
            
            print(f"\n💀 Worst Example: {worst_trade['ticker']} - {worst_trade['insider']} on {worst_trade['trade_date']}")
            print(f"   Entry: ${worst_trade['entry_price']} → Peak: ${worst_trade['peak_price']} → Exit: ${worst_trade['exit_price']}")
            print(f"   Return: {worst_trade['return_pct']:+.2f}% | Held: {worst_trade['days_held']} days | {worst_trade['exit_reason']}")
            
            # Show some big winners that rode the wave
            big_winners = sorted([r for r in results if r.get('peak_return_pct', 0) > 30], 
                                key=lambda x: x.get('peak_return_pct', 0), reverse=True)[:3]
            
            if big_winners:
                print(f"\n🚀 Top Momentum Plays (Rode the wave up):")
                for i, trade in enumerate(big_winners, 1):
                    print(f"   {i}. {trade['ticker']}: Entry ${trade['entry_price']} → "
                          f"Peak ${trade['peak_price']} (+{trade['peak_return_pct']:.1f}%) → "
                          f"Exit ${trade['exit_price']} ({trade['return_pct']:+.1f}%)")
    
    print(f"\n{'='*80}")
    
    if total_trades > 0 and avg_return > 0:
        print(f"✅ VERDICT: This strategy would have been PROFITABLE")
        print(f"   Average gain of {avg_return:.2f}% per trade across {total_trades} trades")
        if completed_trades > 0:
            print(f"   Win rate on completed trades: {winning_trades/completed_trades*100:.1f}%")
    elif total_trades > 0:
        print(f"❌ VERDICT: This strategy would have LOST MONEY")
        print(f"   Average loss of {avg_return:.2f}% per trade across {total_trades} trades")
    else:
        print(f"⚠️  VERDICT: Insufficient data to test strategy")
    
    print(f"{'='*80}\n")
    
    return results


if __name__ == '__main__':
    json_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/top_monthly_insider_trades.json'
    
    results = backtest_trailing_stop_strategy(
        json_file=json_file,
        threshold_percentile=75,
        base_stop_loss=0.05,
        max_days=365,
        use_filing_delay=True
    )
    
    if results:
        import csv
        output_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_trailing_stop_results.csv'
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"Detailed results saved to: {output_file}")
