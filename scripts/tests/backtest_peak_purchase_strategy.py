#!/usr/bin/env python3
"""
Peak Purchase Strategy Backtester
==================================
Tests the strategy: "When an insider makes a peak purchase, buy the stock and set a 5% stop loss"

Strategy Rules:
1. Identify "peak purchases" - large purchases relative to insider's historical behavior
2. Buy at the FILING date (or 2 business days after transaction date)
3. Set a 5% stop loss
4. Track performance across all Top Monthly Activity stocks

The key insight: Insiders must file within 2 business days, so we simulate buying when the
market learns about the trade.
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
        # Skip weekends
        if current_date.weekday() < 5:  # Monday=0, Sunday=6
            business_days_added += 1
    
    return current_date.strftime('%Y-%m-%d')


def parse_value(value_str):
    """Convert '+$69,297,690' to 69297690.0"""
    if not value_str:
        return 0.0
    # Remove +, $, and commas
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
    # Group trades by insider
    insider_trades = defaultdict(list)
    for trade in trades:
        if trade.get('value', '').startswith('+'):  # Only purchases
            insider_name = trade.get('insider_name', '')
            value = parse_value(trade.get('value', '0'))
            insider_trades[insider_name].append({
                'trade': trade,
                'value': value
            })
    
    # Identify peaks
    peak_purchases = []
    for insider_name, purchases in insider_trades.items():
        if len(purchases) == 0:
            continue
        
        values = [p['value'] for p in purchases]
        
        # If insider has only made 1-2 purchases, consider them all peaks
        if len(purchases) <= 2:
            peak_purchases.extend([p['trade'] for p in purchases])
            continue
        
        # Calculate threshold (75th percentile)
        threshold = pd.Series(values).quantile(threshold_percentile / 100.0)
        
        # Mark purchases above threshold as peaks
        for purchase in purchases:
            if purchase['value'] >= threshold:
                peak_purchases.append(purchase['trade'])
    
    return peak_purchases


def simulate_trade(ticker, entry_date, stop_loss_pct=0.05, hold_days=30):
    """
    Simulate buying at entry_date and tracking if stop loss hits or profit is made.
    
    Returns:
        dict with: success, entry_price, exit_price, return_pct, exit_reason, days_held
    """
    try:
        # Get 3 months of data around the entry date for simulation
        entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
        start_date = (entry_dt - timedelta(days=5)).strftime('%Y-%m-%d')
        end_date = (entry_dt + timedelta(days=hold_days + 10)).strftime('%Y-%m-%d')
        
        stock = yf.Ticker(ticker)
        history = stock.history(start=start_date, end=end_date)
        
        if history.empty:
            return {'success': False, 'error': 'No price data'}
        
        # Find entry price (first available price on or after entry_date)
        history.index = pd.to_datetime(history.index).strftime('%Y-%m-%d')
        
        if entry_date not in history.index:
            # Find next available date
            available_dates = sorted([d for d in history.index if d >= entry_date])
            if not available_dates:
                return {'success': False, 'error': 'No price data after entry date'}
            entry_date = available_dates[0]
        
        entry_price = history.loc[entry_date, 'Close']
        stop_loss_price = entry_price * (1 - stop_loss_pct)
        
        # Track daily prices to see if stop loss hits
        days_after_entry = [d for d in history.index if d >= entry_date]
        
        for i, date in enumerate(days_after_entry[1:hold_days+1], 1):  # Start from day 1
            low_price = history.loc[date, 'Low']
            close_price = history.loc[date, 'Close']
            
            # Check if stop loss hit (using intraday low)
            if low_price <= stop_loss_price:
                return_pct = -stop_loss_pct * 100  # -5%
                return {
                    'success': True,
                    'entry_price': round(entry_price, 2),
                    'exit_price': round(stop_loss_price, 2),
                    'return_pct': round(return_pct, 2),
                    'exit_reason': 'stop_loss',
                    'days_held': i
                }
        
        # If we reach here, stop loss never hit within hold period
        # Exit at the last available price
        last_date = days_after_entry[min(hold_days, len(days_after_entry)-1)]
        exit_price = history.loc[last_date, 'Close']
        return_pct = ((exit_price - entry_price) / entry_price) * 100
        
        return {
            'success': True,
            'entry_price': round(entry_price, 2),
            'exit_price': round(exit_price, 2),
            'return_pct': round(return_pct, 2),
            'exit_reason': 'hold_period_end',
            'days_held': min(hold_days, len(days_after_entry)-1)
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def backtest_strategy(json_file, threshold_percentile=75, stop_loss_pct=0.05, hold_days=30, 
                     use_filing_delay=True):
    """
    Backtest the peak purchase strategy across all stocks.
    
    Args:
        json_file: Path to top_monthly_insider_trades.json
        threshold_percentile: What percentile defines a "peak" (default 75 = top 25%)
        stop_loss_pct: Stop loss percentage (default 0.05 = 5%)
        hold_days: Maximum holding period if stop loss not hit (default 30 days)
        use_filing_delay: If True, add 2 business days to simulate filing delay
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    results = []
    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    total_return = 0.0
    
    print(f"{'='*80}")
    print(f"PEAK PURCHASE STRATEGY BACKTEST")
    print(f"{'='*80}")
    print(f"Parameters:")
    print(f"  - Peak threshold: Top {100-threshold_percentile}% of insider's historical purchases")
    print(f"  - Stop loss: {stop_loss_pct*100}%")
    print(f"  - Hold period: {hold_days} days")
    print(f"  - Filing delay simulation: {'Yes (add 2 business days)' if use_filing_delay else 'No'}")
    print(f"\n{'='*80}\n")
    
    for stock_data in data['data']:
        ticker = stock_data['ticker']
        company = stock_data['company_name']
        trades = stock_data['trades']
        
        # Identify peak purchases for this stock
        peak_purchases = identify_peak_purchases(trades, threshold_percentile)
        
        if not peak_purchases:
            continue
        
        print(f"\n{ticker} - {company}")
        print(f"  Found {len(peak_purchases)} peak purchase(s)")
        
        for trade in peak_purchases:
            trade_date = trade['trade_date']
            insider = trade['insider_name']
            value = trade['value']
            
            # Use filing_date if available (more realistic), otherwise apply delay if enabled
            if 'filing_date' in trade and trade['filing_date']:
                entry_date = trade['filing_date']
            else:
                entry_date = get_business_days_later(trade_date, 2) if use_filing_delay else trade_date
            
            print(f"\n  Peak Purchase: {insider} on {trade_date} ({value})")
            print(f"    Entry Date: {entry_date} (filing date)")
            
            # Simulate the trade
            result = simulate_trade(ticker, entry_date, stop_loss_pct, hold_days)
            
            if result['success']:
                total_trades += 1
                return_pct = result['return_pct']
                total_return += return_pct
                
                if return_pct > 0:
                    winning_trades += 1
                    emoji = "✅"
                else:
                    losing_trades += 1
                    emoji = "❌"
                
                print(f"    {emoji} Entry: ${result['entry_price']} | Exit: ${result['exit_price']} | "
                      f"Return: {return_pct:+.2f}% | Exit: {result['exit_reason']} | "
                      f"Days: {result['days_held']}")
                
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
    print(f"Winning Trades: {winning_trades} ({winning_trades/total_trades*100:.1f}%)" if total_trades > 0 else "No trades")
    print(f"Losing Trades: {losing_trades} ({losing_trades/total_trades*100:.1f}%)" if total_trades > 0 else "")
    
    if total_trades > 0:
        avg_return = total_return / total_trades
        print(f"\nAverage Return per Trade: {avg_return:+.2f}%")
        print(f"Total Return (sum): {total_return:+.2f}%")
        
        # Calculate max drawdown and best/worst trades
        if results:
            returns = [r['return_pct'] for r in results if 'return_pct' in r]
            print(f"\nBest Trade: {max(returns):+.2f}%")
            print(f"Worst Trade: {min(returns):+.2f}%")
            
            # Show best and worst examples
            best_trade = max(results, key=lambda x: x.get('return_pct', -999))
            worst_trade = min(results, key=lambda x: x.get('return_pct', 999))
            
            print(f"\nBest Example: {best_trade['ticker']} - {best_trade['insider']} on {best_trade['trade_date']}")
            print(f"  Entry: ${best_trade['entry_price']} → Exit: ${best_trade['exit_price']} = {best_trade['return_pct']:+.2f}%")
            
            print(f"\nWorst Example: {worst_trade['ticker']} - {worst_trade['insider']} on {worst_trade['trade_date']}")
            print(f"  Entry: ${worst_trade['entry_price']} → Exit: ${worst_trade['exit_price']} = {worst_trade['return_pct']:+.2f}%")
    
    print(f"\n{'='*80}")
    
    # Final verdict
    if total_trades > 0 and avg_return > 0:
        print(f"✅ VERDICT: This strategy would have been PROFITABLE")
        print(f"   Average gain of {avg_return:.2f}% per trade across {total_trades} trades")
    elif total_trades > 0:
        print(f"❌ VERDICT: This strategy would have LOST MONEY")
        print(f"   Average loss of {avg_return:.2f}% per trade across {total_trades} trades")
    else:
        print(f"⚠️  VERDICT: Insufficient data to test strategy")
    
    print(f"{'='*80}\n")
    
    return results


if __name__ == '__main__':
    json_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/top_monthly_insider_trades.json'
    
    # Run the backtest with default parameters
    results = backtest_strategy(
        json_file=json_file,
        threshold_percentile=75,  # Top 25% of insider's purchases
        stop_loss_pct=0.05,       # 5% stop loss
        hold_days=30,             # Hold for up to 30 days
        use_filing_delay=True     # Simulate 2-day filing delay
    )
    
    # Optionally save results to CSV
    if results:
        import csv
        output_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_results.csv'
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"Detailed results saved to: {output_file}")
