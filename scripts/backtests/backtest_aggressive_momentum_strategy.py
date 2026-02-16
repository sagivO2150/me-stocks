#!/usr/bin/env python3
"""
Aggressive Momentum Insider Trading Strategy
=============================================
More aggressive approach that stays in winning positions longer:

1. DYNAMIC STOP LOSS:
   - If stock is in strong uptrend (>10% above entry): 10% trailing stop
   - If stock is in moderate uptrend (>5% above entry): 7% trailing stop  
   - If stock hasn't reached +5% yet: 5% trailing stop (standard)
   
2. INSIDER MOMENTUM BOOST:
   - If 3+ insider purchases in past 14 days: 1.5x position size
   - If 5+ insider purchases in past 14 days: 2x position size
   
3. PROFIT CUSHION:
   - No stop loss for first 5 trading days (grace period)
   - After grace period, only apply stop loss if we're below +3% profit
   - This prevents exiting winning positions on minor dips
   
4. CLUSTER PROTECTION:
   - If there was an insider purchase in the last 7 days, relax stop to 7%
   - Rationale: Nearby insider activity suggests continued confidence
   
5. DOUBLE DOWN ON MOMENTUM:
   - If position is up >15% AND new insider buy occurs: add 50% to position
   
This strategy is designed to capture explosive moves while still protecting capital.
"""

import json
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
import sys


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


def count_recent_insider_purchases(ticker, check_date, all_insider_purchases, days_back=14):
    """Count how many insider purchases happened in the last N days"""
    check_dt = datetime.strptime(check_date, '%Y-%m-%d')
    count = 0
    
    for purchase in all_insider_purchases.get(ticker, []):
        purchase_dt = datetime.strptime(purchase['filing_date'], '%Y-%m-%d')
        days_diff = (check_dt - purchase_dt).days
        
        if 0 <= days_diff <= days_back:
            count += 1
    
    return count


def has_insider_purchase_within_days(ticker, check_date, all_insider_purchases, days_back=7):
    """Check if there was an insider purchase in the last N days"""
    return count_recent_insider_purchases(ticker, check_date, all_insider_purchases, days_back) > 0


def check_position_status_aggressive(ticker, entry_date, entry_price, check_date, 
                                     all_insider_purchases, grace_days=5):
    """
    Check position with aggressive momentum-based rules.
    
    Returns: (exit_price, exit_date, return_pct, exit_reason) or (None, None, None, 'still_holding')
    """
    try:
        entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
        check_dt = datetime.strptime(check_date, '%Y-%m-%d')
        
        if check_dt <= entry_dt:
            return None, None, None, 'still_holding'
        
        start_date = entry_date
        end_date = (check_dt + timedelta(days=1)).strftime('%Y-%m-%d')
        
        stock = yf.Ticker(ticker)
        history = stock.history(start=start_date, end=end_date)
        
        if history.empty:
            return None, None, None, 'error'
        
        history.index = pd.to_datetime(history.index).strftime('%Y-%m-%d')
        dates_after_entry = [d for d in history.index if d > entry_date]
        
        if not dates_after_entry:
            return None, None, None, 'still_holding'
        
        highest_price = entry_price
        business_days_count = 0
        
        for date in dates_after_entry:
            if date > check_date:
                break
            
            # Count business days
            if datetime.strptime(date, '%Y-%m-%d').weekday() < 5:
                business_days_count += 1
            
            high_price = history.loc[date, 'High']
            low_price = history.loc[date, 'Low']
            close_price = history.loc[date, 'Close']
            
            # Update highest price
            if high_price > highest_price:
                highest_price = high_price
            
            current_profit_pct = ((close_price - entry_price) / entry_price) * 100
            
            # GRACE PERIOD: No stop loss for first 5 business days
            if business_days_count <= grace_days:
                continue
            
            # PROFIT CUSHION: Only apply stop loss if we're below +3% profit
            if current_profit_pct >= 3.0:
                continue
            
            # Determine stop loss percentage based on performance and context
            base_stop_pct = 0.05  # 5% base
            
            # Check for nearby insider activity for cluster protection
            has_recent_insider = has_insider_purchase_within_days(ticker, date, all_insider_purchases, days_back=7)
            
            # DYNAMIC STOP LOSS based on profit level
            if current_profit_pct > 10:
                # Strong uptrend - allow 10% pullback
                stop_loss_pct = 0.10
            elif current_profit_pct > 5:
                # Moderate uptrend - allow 7% pullback
                stop_loss_pct = 0.07
            elif has_recent_insider:
                # Cluster protection - relax to 7%
                stop_loss_pct = 0.07
            else:
                # Standard 5% stop
                stop_loss_pct = base_stop_pct
            
            trailing_stop_price = highest_price * (1 - stop_loss_pct)
            
            # Check if stop loss hit
            if low_price <= trailing_stop_price:
                return_pct = ((trailing_stop_price - entry_price) / entry_price) * 100
                return trailing_stop_price, date, return_pct, 'stop_loss'
        
        # Still holding
        return None, None, None, 'still_holding'
        
    except Exception as e:
        print(f"Error checking {ticker}: {e}")
        return None, None, None, 'error'


def backtest_aggressive_momentum_strategy(json_file, initial_position_size=1000):
    """
    Backtest aggressive momentum strategy with dynamic position sizing.
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Pre-load all historical data
    print("Pre-loading historical data for all tickers...")
    all_tickers = list(set(stock['ticker'] for stock in data['data']))
    price_cache = {}
    
    for ticker in all_tickers:
        try:
            stock = yf.Ticker(ticker)
            history = stock.history(start='2022-01-01', end='2026-02-14')
            if not history.empty:
                history.index = pd.to_datetime(history.index).strftime('%Y-%m-%d')
                price_cache[ticker] = history
                print(f"  ✓ {ticker}")
            else:
                print(f"  ✗ {ticker} (no data)")
        except Exception as e:
            print(f"  ✗ {ticker} (error)")
    
    print(f"\nLoaded data for {len(price_cache)} tickers\n")
    
    # Build insider purchase timeline for each ticker
    all_insider_purchases = defaultdict(list)
    all_trades = []
    
    for stock_data in data['data']:
        ticker = stock_data['ticker']
        
        if ticker not in price_cache:
            continue
        
        company = stock_data['company_name']
        
        for trade in stock_data['trades']:
            if trade.get('value', '').startswith('+'):  # Only purchases
                trade_date = trade['trade_date']
                
                if 'filing_date' in trade and trade['filing_date']:
                    filing_date = trade['filing_date'].split()[0]  # Remove time if present
                    entry_date = filing_date
                else:
                    entry_date = get_business_days_later(trade_date, 2)
                
                trade_value = parse_value(trade['value'])
                
                purchase_info = {
                    'trade_date': trade_date,
                    'filing_date': entry_date,
                    'insider': trade['insider_name'],
                    'value': trade_value
                }
                
                all_insider_purchases[ticker].append(purchase_info)
                
                all_trades.append({
                    'ticker': ticker,
                    'company': company,
                    'trade_date': trade_date,
                    'entry_date': entry_date,
                    'insider': trade['insider_name'],
                    'role': trade.get('role', ''),
                    'value': trade_value
                })
    
    # Sort all trades chronologically
    all_trades.sort(key=lambda x: x['entry_date'])
    
    # Track positions and results
    open_positions = defaultdict(list)
    closed_trades = []
    current_base_size = initial_position_size
    
    print(f"{'='*80}")
    print("STARTING AGGRESSIVE MOMENTUM BACKTEST")
    print(f"{'='*80}\n")
    
    for trade in all_trades:
        ticker = trade['ticker']
        entry_date = trade['entry_date']
        
        # Check and close positions that hit stop loss
        for pos in open_positions[ticker][:]:
            result = check_position_status_aggressive(
                ticker, 
                pos['entry_date'],
                pos['entry_price'],
                entry_date,
                all_insider_purchases
            )
            
            exit_price, exit_date, return_pct, exit_reason = result
            
            if exit_price is not None:
                profit_loss = pos['amount_invested'] * (return_pct / 100)
                returned_amount = pos['amount_invested'] + profit_loss
                
                closed_trades.append({
                    'ticker': ticker,
                    'company': pos['company'],
                    'trade_date': pos['trade_date'],
                    'entry_date': pos['entry_date'],
                    'entry_price': pos['entry_price'],
                    'exit_date': exit_date,
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'amount_invested': pos['amount_invested'],
                    'returned_amount': returned_amount,
                    'profit_loss': profit_loss,
                    'return_pct': return_pct,
                    'shares': pos['shares'],
                    'insider': pos['insider'],
                    'role': pos['role'],
                    'peak_price': pos['highest_price'],
                    'highest_price': pos['highest_price']
                })
                
                emoji = "📉" if profit_loss >= 0 else "📉"
                print(f"{emoji} CLOSED {ticker}: ${pos['entry_price']:.2f} → ${pos['highest_price']:.2f} (peak) → ${exit_price:.2f} = {return_pct:+.1f}% (${pos['amount_invested']:,.0f} → ${returned_amount:,.0f})")
                
                open_positions[ticker].remove(pos)
        
        # Get entry price
        if ticker not in price_cache:
            continue
        
        history = price_cache[ticker]
        
        # Find first available date on or after entry_date
        available_dates = sorted([d for d in history.index if d >= entry_date])
        if not available_dates:
            continue
        
        actual_entry_date = available_dates[0]
        entry_price = history.loc[actual_entry_date, 'Close']
        
        # Count recent insider purchases for position sizing
        recent_purchase_count = count_recent_insider_purchases(ticker, entry_date, all_insider_purchases, days_back=14)
        
        # INSIDER MOMENTUM BOOST
        position_multiplier = 1.0
        if recent_purchase_count >= 5:
            position_multiplier = 2.0
            print(f"🔥 HEAVY INSIDER ACTIVITY ({recent_purchase_count} purchases in 14 days)")
        elif recent_purchase_count >= 3:
            position_multiplier = 1.5
            print(f"🔥 STRONG INSIDER ACTIVITY ({recent_purchase_count} purchases in 14 days)")
        
        # Calculate position size
        position_size = current_base_size * position_multiplier
        
        # Check if we should double down on existing profitable positions
        should_double_down = False
        for pos in open_positions[ticker]:
            current_price = entry_price
            current_profit_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
            
            if current_profit_pct > 15:
                should_double_down = True
                position_size = pos['amount_invested'] * 0.5  # Add 50% more
                print(f"⚡ DOUBLE DOWN on {ticker} (position up {current_profit_pct:.1f}%)")
                break
        
        # Open new position
        shares = position_size / entry_price
        
        position = {
            'ticker': ticker,
            'company': trade['company'],
            'trade_date': trade['trade_date'],
            'entry_date': actual_entry_date,
            'entry_price': entry_price,
            'amount_invested': position_size,
            'shares': shares,
            'insider': trade['insider'],
            'role': trade['role'],
            'highest_price': entry_price
        }
        
        open_positions[ticker].append(position)
        
        action = "ADD to" if open_positions[ticker].__len__() > 1 else "NEW"
        print(f"💰 {action} {ticker} @ ${entry_price:.2f} (${position_size:,.0f})")
    
    # Close remaining open positions at end date
    print(f"\n{'='*80}")
    print("CLOSING REMAINING OPEN POSITIONS")
    print(f"{'='*80}\n")
    
    end_date = '2026-02-13'
    for ticker, positions in open_positions.items():
        if ticker not in price_cache:
            continue
        
        history = price_cache[ticker]
        available_dates = sorted([d for d in history.index if d <= end_date])
        
        if not available_dates:
            continue
        
        final_date = available_dates[-1]
        final_price = history.loc[final_date, 'Close']
        
        for pos in positions:
            return_pct = ((final_price - pos['entry_price']) / pos['entry_price']) * 100
            profit_loss = pos['amount_invested'] * (return_pct / 100)
            returned_amount = pos['amount_invested'] + profit_loss
            
            closed_trades.append({
                'ticker': ticker,
                'company': pos['company'],
                'trade_date': pos['trade_date'],
                'entry_date': pos['entry_date'],
                'entry_price': pos['entry_price'],
                'exit_date': final_date,
                'exit_price': final_price,
                'exit_reason': 'end_of_period',
                'amount_invested': pos['amount_invested'],
                'returned_amount': returned_amount,
                'profit_loss': profit_loss,
                'return_pct': return_pct,
                'shares': pos['shares'],
                'insider': pos['insider'],
                'role': pos['role'],
                'peak_price': pos['highest_price'],
                'highest_price': pos['highest_price']
            })
            
            emoji = "✅" if profit_loss >= 0 else "❌"
            print(f"{emoji} CLOSED {ticker}: ${pos['entry_price']:.2f} → ${final_price:.2f} = {return_pct:+.1f}% (${pos['amount_invested']:,.0f} → ${returned_amount:,.0f})")
    
    # Calculate summary statistics
    print(f"\n{'='*80}")
    print("FINAL RESULTS - AGGRESSIVE MOMENTUM STRATEGY")
    print(f"{'='*80}\n")
    
    total_trades = len(closed_trades)
    winning_trades = [t for t in closed_trades if t['profit_loss'] > 0]
    losing_trades = [t for t in closed_trades if t['profit_loss'] <= 0]
    
    total_invested = sum(t['amount_invested'] for t in closed_trades)
    total_returned = sum(t['returned_amount'] for t in closed_trades)
    net_profit = total_returned - total_invested
    
    avg_return = sum(t['return_pct'] for t in closed_trades) / len(closed_trades) if closed_trades else 0
    
    print(f"Total Trades: {total_trades}")
    print(f"  Winning: {len(winning_trades)} ({len(winning_trades)/total_trades*100:.1f}%)")
    print(f"  Losing: {len(losing_trades)} ({len(losing_trades)/total_trades*100:.1f}%)")
    print(f"\nAverage Return per Trade: {avg_return:+.2f}%")
    
    print(f"\n💰 PORTFOLIO PERFORMANCE:")
    print(f"   Total Invested: ${total_invested:,.2f}")
    print(f"   Total Returned: ${total_returned:,.2f}")
    print(f"   Net Profit/Loss: ${net_profit:,.2f}")
    print(f"   ROI: {(net_profit/total_invested*100):+.2f}%")
    
    if winning_trades:
        best_trade = max(winning_trades, key=lambda x: x['return_pct'])
        print(f"\n🏆 Best Trade: {best_trade['ticker']} - {best_trade['return_pct']:+.1f}%")
        print(f"   ${best_trade['entry_price']:.2f} → ${best_trade['exit_price']:.2f}")
        print(f"   Invested: ${best_trade['amount_invested']:,.0f} | Returned: ${best_trade['returned_amount']:,.0f}")
    
    if losing_trades:
        worst_trade = min(losing_trades, key=lambda x: x['return_pct'])
        print(f"\n💀 Worst Trade: {worst_trade['ticker']} - {worst_trade['return_pct']:+.1f}%")
        print(f"   ${worst_trade['entry_price']:.2f} → ${worst_trade['exit_price']:.2f}")
        print(f"   Invested: ${worst_trade['amount_invested']:,.0f} | Returned: ${worst_trade['returned_amount']:,.0f}")
    
    print(f"\n{'='*80}\n")
    
    return closed_trades


if __name__ == '__main__':
    json_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/full_history_insider_trades.json'
    
    results = backtest_aggressive_momentum_strategy(
        json_file=json_file,
        initial_position_size=1000
    )
    
    # Save results
    if results:
        import csv
        output_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_aggressive_momentum_results.csv'
        
        all_fields = set()
        for result in results:
            all_fields.update(result.keys())
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(all_fields))
            writer.writeheader()
            writer.writerows(results)
        
        print(f"✅ Results saved to: {output_file}")
