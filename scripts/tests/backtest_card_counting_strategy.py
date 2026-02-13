#!/usr/bin/env python3
"""
Card Counting Style Insider Trading Strategy
=============================================
Treats insider buying like "hot deck" in card counting:
1. Buy on every insider purchase with 5% TRAILING stop loss
2. If another insider buys while holding and profitable → DOUBLE DOWN
3. Adjust position sizing based on win/loss streak:
   - Win: Increase next base position by 10%
   - Loss: Decrease next base position by 10%

TRAILING STOP LOSS: Stop loss follows the highest price reached.
- Buy at $10 → stop at $9.50
- Stock rises to $20 → stop moves to $19 (5% below peak)
- Stock drops to $19 → SELL (preserve gains, limit downside)

ENTRY TIMING: Uses actual filing date from insider data (when info becomes public).
This mimics real-world bot behavior - we only know about trades when they're filed.

This tests if momentum/clustering of insider buying creates exploitable patterns.
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


def get_price_at_date(ticker, target_date, days_forward=5):
    """Get stock price on or after target date"""
    try:
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        start_date = (target_dt - timedelta(days=5)).strftime('%Y-%m-%d')
        end_date = (target_dt + timedelta(days=days_forward)).strftime('%Y-%m-%d')
        
        stock = yf.Ticker(ticker)
        history = stock.history(start=start_date, end=end_date)
        
        if history.empty:
            return None
        
        history.index = pd.to_datetime(history.index).strftime('%Y-%m-%d')
        
        # Find first available date on or after target
        available_dates = sorted([d for d in history.index if d >= target_date])
        if not available_dates:
            return None
        
        actual_date = available_dates[0]
        return history.loc[actual_date, 'Close'], actual_date
    except:
        return None


def check_position_status(ticker, entry_date, entry_price, check_date, stop_loss_pct=0.05, grace_days=2):
    """
    Check if position is still open or hit TRAILING stop loss by check_date.
    GRACE PERIOD: First 2 business days - no stop loss.
    After grace period: If 5%+ below entry, sell immediately. Otherwise start trailing stop.
    TRAILING STOP: Stop loss follows the highest price reached.
    Returns: (still_open, exit_price, exit_date, current_profit_pct)
    """
    try:
        entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
        check_dt = datetime.strptime(check_date, '%Y-%m-%d')
        
        if check_dt <= entry_dt:
            return True, None, None, 0.0  # Not entered yet
        
        start_date = entry_date
        end_date = (check_dt + timedelta(days=1)).strftime('%Y-%m-%d')
        
        stock = yf.Ticker(ticker)
        history = stock.history(start=start_date, end=end_date)
        
        if history.empty:
            return False, None, None, None  # Can't determine
        
        history.index = pd.to_datetime(history.index).strftime('%Y-%m-%d')
        
        # TRAILING STOP: Track highest price and stop loss follows it
        highest_price = entry_price
        trailing_stop_price = entry_price * (1 - stop_loss_pct)
        
        # Check each day for trailing stop loss
        dates_after_entry = sorted([d for d in history.index if d > entry_date])
        business_days_count = 0
        
        for date in dates_after_entry:
            if date > check_date:
                break
            
            business_days_count += 1
            high_price = history.loc[date, 'High']
            low_price = history.loc[date, 'Low']
            close_price = history.loc[date, 'Close']
            
            # GRACE PERIOD: Skip stop loss for first 2 business days
            if business_days_count <= grace_days:
                # Update highest price during grace period
                if high_price > highest_price:
                    highest_price = high_price
                continue
            
            # After grace period: Check if 5% below entry on the first check (day 3)
            if business_days_count == grace_days + 1:
                if close_price <= entry_price * (1 - stop_loss_pct):
                    # Immediate sell if 5%+ below entry after grace period
                    loss_pct = ((close_price - entry_price) / entry_price) * 100
                    return False, close_price, date, loss_pct
            
            # Update highest price if new high reached
            if high_price > highest_price:
                highest_price = high_price
                trailing_stop_price = highest_price * (1 - stop_loss_pct)
            
            # Check if trailing stop hit
            if low_price <= trailing_stop_price:
                loss_from_peak = ((trailing_stop_price - highest_price) / highest_price) * 100
                return False, trailing_stop_price, date, loss_from_peak
        
        # If we get here, position is still open
        # Get current price at check_date
        if check_date in history.index:
            current_price = history.loc[check_date, 'Close']
        else:
            dates_before_check = [d for d in history.index if d <= check_date]
            if not dates_before_check:
                return True, None, None, 0.0
            current_price = history.loc[dates_before_check[-1], 'Close']
        
        current_profit_pct = ((current_price - entry_price) / entry_price) * 100
        
        return True, current_price, None, current_profit_pct
        
    except Exception as e:
        return False, None, None, None


def close_position_if_open(ticker, entry_date, entry_price, max_hold_days=365, grace_days=2):
    """
    Close position at end of period (today or max hold days) using TRAILING STOP.
    GRACE PERIOD: First 2 business days - no stop loss.
    After grace period: If 5%+ below entry, sell immediately. Otherwise start trailing stop.
    Returns: (exit_price, exit_date, return_pct, exit_reason)
    """
    try:
        entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
        today = datetime.now()
        max_end_date = entry_dt + timedelta(days=max_hold_days)
        end_date = min(today, max_end_date).strftime('%Y-%m-%d')
        
        start_date = entry_date
        
        stock = yf.Ticker(ticker)
        history = stock.history(start=start_date, end=end_date)
        
        if history.empty:
            return None, None, None, 'no_data'
        
        history.index = pd.to_datetime(history.index).strftime('%Y-%m-%d')
        
        # TRAILING STOP: Track highest price
        highest_price = entry_price
        trailing_stop_price = entry_price * 0.95
        
        # Check for trailing stop loss
        dates_after_entry = sorted([d for d in history.index if d > entry_date])
        business_days_count = 0
        
        for date in dates_after_entry:
            business_days_count += 1
            high_price = history.loc[date, 'High']
            low_price = history.loc[date, 'Low']
            close_price = history.loc[date, 'Close']
            
            # GRACE PERIOD: Skip stop loss for first 2 business days
            if business_days_count <= grace_days:
                # Update highest price during grace period
                if high_price > highest_price:
                    highest_price = high_price
                continue
            
            # After grace period: Check if 5% below entry on the first check (day 3)
            if business_days_count == grace_days + 1:
                if close_price <= entry_price * 0.95:
                    # Immediate sell if 5%+ below entry after grace period
                    return_pct = ((close_price - entry_price) / entry_price) * 100
                    return close_price, date, return_pct, 'stop_loss'
            
            # Update highest price if new high reached
            if high_price > highest_price:
                highest_price = high_price
                trailing_stop_price = highest_price * 0.95
            
            # Check if trailing stop hit
            if low_price <= trailing_stop_price:
                return_pct = ((trailing_stop_price - entry_price) / entry_price) * 100
                return trailing_stop_price, date, return_pct, 'stop_loss'
        
        # If no stop loss, close at last available price
        last_date = dates_after_entry[-1] if dates_after_entry else entry_date
        exit_price = history.loc[last_date, 'Close']
        return_pct = ((exit_price - entry_price) / entry_price) * 100
        
        return exit_price, last_date, return_pct, 'still_holding'
        
    except Exception as e:
        return None, None, None, 'error'


def backtest_card_counting_strategy(json_file, initial_position_size=1000, base_adjustment=0.10):
    """
    Backtest the card counting strategy across all stocks chronologically.
    
    Args:
        initial_position_size: Starting position size ($)
        base_adjustment: How much to adjust position size on win/loss (0.10 = 10%)
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Pre-download all historical data for performance
    print("Pre-loading historical data for all tickers...")
    all_tickers = list(set(stock['ticker'] for stock in data['data']))
    price_cache = {}
    
    for ticker in all_tickers:
        try:
            stock = yf.Ticker(ticker)
            # Fetch 4 years of history to cover all insider trades
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
    
    # Flatten all trades across all stocks with entry dates
    all_trades = []
    for stock_data in data['data']:
        ticker = stock_data['ticker']
        
        # Skip if no price data
        if ticker not in price_cache:
            continue
        
        company = stock_data['company_name']
        
        for trade in stock_data['trades']:
            if trade.get('value', '').startswith('+'):  # Only purchases
                trade_date = trade['trade_date']
                # Use filing_date if available (more realistic), otherwise fall back to 2-day delay
                if 'filing_date' in trade and trade['filing_date']:
                    entry_date = trade['filing_date']
                else:
                    entry_date = get_business_days_later(trade_date, 2)
                
                all_trades.append({
                    'ticker': ticker,
                    'company': company,
                    'trade_date': trade_date,
                    'entry_date': entry_date,
                    'insider': trade['insider_name'],
                    'role': trade.get('role', ''),
                    'value': trade['value']
                })
    
    # Sort chronologically by entry date
    all_trades.sort(key=lambda x: x['entry_date'])
    
    # Track state
    open_positions = {}  # ticker -> list of positions
    closed_trades = []
    current_position_size = initial_position_size
    total_invested = 0
    total_returned = 0
    
    print(f"{'='*80}")
    print(f"CARD COUNTING INSIDER STRATEGY BACKTEST")
    print(f"{'='*80}")
    print(f"Strategy:")
    print(f"  - Buy every insider purchase")
    print(f"  - GRACE PERIOD: Hold 2 business days no matter what")
    print(f"  - After 48hrs: If 5%+ below entry → SELL immediately")
    print(f"  - Otherwise: Start 5% TRAILING stop loss (follows highest price)")
    print(f"  - Position size: ${initial_position_size:,.0f} (fixed)")
    print(f"  - Entry timing: Filing date (when data becomes public)")
    print(f"\n{'='*80}\n")
    
    for i, trade in enumerate(all_trades):
        ticker = trade['ticker']
        entry_date = trade['entry_date']
        
        if ticker not in price_cache:
            continue
        
        history = price_cache[ticker]
        
        # First, check status of all open positions as of this entry date
        for open_ticker in list(open_positions.keys()):
            if open_ticker not in price_cache:
                continue
                
            open_history = price_cache[open_ticker]
            positions_to_remove = []
            
            for pos_idx, position in enumerate(open_positions[open_ticker]):
                # Check if TRAILING stop loss hit between position entry and current entry date
                # GRACE PERIOD: First 2 business days - no stop loss
                pos_entry_date = position['entry_date']
                pos_entry_price = position['entry_price']
                
                # Track highest price and trailing stop
                highest_price = position.get('highest_price', pos_entry_price)
                trailing_stop_price = highest_price * 0.95
                
                # Get dates between position entry and now
                dates_between = [d for d in open_history.index if pos_entry_date < d <= entry_date]
                
                hit_stop_loss = False
                business_days_count = 0
                
                for date in dates_between:
                    business_days_count += 1
                    high_price = open_history.loc[date, 'High']
                    low_price = open_history.loc[date, 'Low']
                    close_price = open_history.loc[date, 'Close']
                    
                    # GRACE PERIOD: Skip stop loss for first 2 business days
                    if business_days_count <= 2:
                        # Update highest price during grace period
                        if high_price > highest_price:
                            highest_price = high_price
                        continue
                    
                    # After grace period: Check if 5% below entry on first check (day 3)
                    if business_days_count == 3:
                        if close_price <= pos_entry_price * 0.95:
                            # Immediate sell if 5%+ below entry after grace period
                            return_pct = ((close_price - pos_entry_price) / pos_entry_price) * 100
                            returned_amount = position['amount_invested'] * (1 + return_pct / 100)
                            
                            closed_trades.append({
                                **position,
                                'exit_date': date,
                                'exit_price': close_price,
                                'return_pct': return_pct,
                                'returned_amount': returned_amount,
                                'profit_loss': returned_amount - position['amount_invested'],
                                'exit_reason': 'stop_loss',
                                'peak_price': highest_price
                            })
                            
                            total_returned += returned_amount
                            
                            print(f"📉 CLOSED {open_ticker}: ${pos_entry_price:.2f} → ${highest_price:.2f} (peak) → ${close_price:.2f} = {return_pct:.1f}% "
                                  f"(${position['amount_invested']:,.0f} → ${returned_amount:,.0f})")
                            
                            positions_to_remove.append(pos_idx)
                            hit_stop_loss = True
                            break
                    
                    # Update highest price if new high reached
                    if high_price > highest_price:
                        highest_price = high_price
                        trailing_stop_price = highest_price * 0.95
                    
                    # Check if trailing stop hit
                    if low_price <= trailing_stop_price:
                        # Trailing stop loss hit!
                        return_pct = ((trailing_stop_price - pos_entry_price) / pos_entry_price) * 100
                        returned_amount = position['amount_invested'] * (1 + return_pct / 100)
                        
                        closed_trades.append({
                            **position,
                            'exit_date': date,
                            'exit_price': trailing_stop_price,
                            'return_pct': return_pct,
                            'returned_amount': returned_amount,
                            'profit_loss': returned_amount - position['amount_invested'],
                            'exit_reason': 'stop_loss',
                            'peak_price': highest_price
                        })
                        
                        total_returned += returned_amount
                        
                        print(f"📉 CLOSED {open_ticker}: ${pos_entry_price:.2f} → ${highest_price:.2f} (peak) → ${trailing_stop_price:.2f} = {return_pct:.1f}% "
                              f"(${position['amount_invested']:,.0f} → ${returned_amount:,.0f})")
                        
                        positions_to_remove.append(pos_idx)
                        hit_stop_loss = True
                        break
            
            # Remove closed positions
            for pos_idx in sorted(positions_to_remove, reverse=True):
                open_positions[open_ticker].pop(pos_idx)
            
            if not open_positions[open_ticker]:
                del open_positions[open_ticker]
        
        # Now process the new insider buy
        # Get entry price from cache
        available_dates = sorted([d for d in history.index if d >= entry_date])
        if not available_dates:
            continue
        
        actual_entry_date = available_dates[0]
        entry_price = history.loc[actual_entry_date, 'Close']
        
        # Always invest the same amount
        amount_to_invest = current_position_size
        
        if ticker in open_positions:
            print(f"\n💰 ADD to {ticker} @ ${entry_price:.2f} (${amount_to_invest:,.0f})")
        else:
            print(f"\n💰 NEW {ticker} @ ${entry_price:.2f} (${amount_to_invest:,.0f})")
        
        # Open the position
        if ticker not in open_positions:
            open_positions[ticker] = []
        
        open_positions[ticker].append({
            'ticker': ticker,
            'company': trade['company'],
            'trade_date': trade['trade_date'],
            'entry_date': actual_entry_date,
            'entry_price': entry_price,
            'insider': trade['insider'],
            'role': trade['role'],
            'amount_invested': amount_to_invest,
            'shares': amount_to_invest / entry_price,
            'highest_price': entry_price  # Track for trailing stop
        })
        
        total_invested += amount_to_invest
    
    # Close all remaining open positions
    print(f"\n{'='*80}")
    print(f"CLOSING REMAINING OPEN POSITIONS")
    print(f"{'='*80}\n")
    
    for ticker, positions in open_positions.items():
        if ticker not in price_cache:
            continue
            
        history = price_cache[ticker]
        
        for position in positions:
            pos_entry_date = position['entry_date']
            pos_entry_price = position['entry_price']
            
            # TRAILING STOP: Track highest price
            highest_price = position.get('highest_price', pos_entry_price)
            trailing_stop_price = highest_price * 0.95
            
            # Check for trailing stop loss after position entry
            dates_after_entry = [d for d in history.index if d > pos_entry_date]
            
            hit_stop_loss = False
            business_days_count = 0
            
            for date in dates_after_entry:
                business_days_count += 1
                high_price = history.loc[date, 'High']
                low_price = history.loc[date, 'Low']
                close_price = history.loc[date, 'Close']
                
                # GRACE PERIOD: Skip stop loss for first 2 business days
                if business_days_count <= 2:
                    # Update highest price during grace period
                    if high_price > highest_price:
                        highest_price = high_price
                    continue
                
                # After grace period: Check if 5% below entry on first check (day 3)
                if business_days_count == 3:
                    if close_price <= pos_entry_price * 0.95:
                        # Immediate sell if 5%+ below entry after grace period
                        return_pct = ((close_price - pos_entry_price) / pos_entry_price) * 100
                        returned_amount = position['amount_invested'] * (1 + return_pct / 100)
                        exit_price = close_price
                        exit_date = date
                        hit_stop_loss = True
                        break
                
                # Update highest price if new high reached
                if high_price > highest_price:
                    highest_price = high_price
                    trailing_stop_price = highest_price * 0.95
                
                # Check if trailing stop hit
                if low_price <= trailing_stop_price:
                    return_pct = ((trailing_stop_price - pos_entry_price) / pos_entry_price) * 100
                    returned_amount = position['amount_invested'] * (1 + return_pct / 100)
                    exit_price = trailing_stop_price
                    exit_date = date
                    hit_stop_loss = True
                    break
            
            if not hit_stop_loss:
                # Close at last available price
                exit_date = dates_after_entry[-1] if dates_after_entry else pos_entry_date
                exit_price = history.loc[exit_date, 'Close']
                return_pct = ((exit_price - pos_entry_price) / pos_entry_price) * 100
                returned_amount = position['amount_invested'] * (1 + return_pct / 100)
            
            closed_trades.append({
                **position,
                'exit_date': exit_date,
                'exit_price': exit_price,
                'return_pct': return_pct,
                'exit_reason': 'stop_loss' if hit_stop_loss else 'end_of_period',
                'returned_amount': returned_amount,
                'peak_price': highest_price,
                'profit_loss': returned_amount - position['amount_invested']
            })
            
            total_returned += returned_amount
            
            emoji = "✅" if return_pct > 0 else "❌"
            print(f"{emoji} CLOSED {ticker}: ${pos_entry_price:.2f} → "
                  f"${exit_price:.2f} = {return_pct:+.1f}% "
                  f"(${position['amount_invested']:,.0f} → ${returned_amount:,.0f})")
    
    # Calculate statistics
    print(f"\n{'='*80}")
    print(f"FINAL RESULTS")
    print(f"{'='*80}\n")
    
    print(f"Total Trades: {len(closed_trades)}")
    
    if closed_trades:
        winning_trades = [t for t in closed_trades if t['return_pct'] > 0]
        losing_trades = [t for t in closed_trades if t['return_pct'] <= 0]
        
        print(f"  Winning: {len(winning_trades)} ({len(winning_trades)/len(closed_trades)*100:.1f}%)")
        print(f"  Losing: {len(losing_trades)} ({len(losing_trades)/len(closed_trades)*100:.1f}%)")
        
        avg_return = sum(t['return_pct'] for t in closed_trades) / len(closed_trades)
        print(f"\nAverage Return per Trade: {avg_return:+.2f}%")
        
        total_profit = sum(t['profit_loss'] for t in closed_trades)
        print(f"\n💰 PORTFOLIO PERFORMANCE:")
        print(f"   Total Invested: ${total_invested:,.2f}")
        print(f"   Total Returned: ${total_returned:,.2f}")
        print(f"   Net Profit/Loss: ${total_profit:,.2f}")
        print(f"   ROI: {(total_profit / total_invested * 100):+.2f}%")
        
        # Position sizing evolution
        print(f"\n📊 POSITION SIZING:")
        print(f"   Starting size: ${initial_position_size:,.0f}")
        print(f"   Ending size: ${current_position_size:,.0f}")
        print(f"   Change: {(current_position_size / initial_position_size - 1) * 100:+.1f}%")
        
        # Best and worst
        best = max(closed_trades, key=lambda x: x['return_pct'])
        worst = min(closed_trades, key=lambda x: x['return_pct'])
        
        print(f"\n🏆 Best Trade: {best['ticker']} - {best['return_pct']:+.1f}%")
        print(f"   ${best['entry_price']:.2f} → ${best['exit_price']:.2f}")
        print(f"   Invested: ${best['amount_invested']:,.0f} | Returned: ${best['returned_amount']:,.0f}")
        
        print(f"\n💀 Worst Trade: {worst['ticker']} - {worst['return_pct']:+.1f}%")
        print(f"   ${worst['entry_price']:.2f} → ${worst['exit_price']:.2f}")
        print(f"   Invested: ${worst['amount_invested']:,.0f} | Returned: ${worst['returned_amount']:,.0f}")
        
        # Double down analysis
        double_downs = [t for t in closed_trades if t['amount_invested'] > initial_position_size * 1.5]
        if double_downs:
            dd_avg_return = sum(t['return_pct'] for t in double_downs) / len(double_downs)
            dd_profit = sum(t['profit_loss'] for t in double_downs)
            
            print(f"\n🔥 DOUBLE DOWN PERFORMANCE:")
            print(f"   Count: {len(double_downs)}")
            print(f"   Avg Return: {dd_avg_return:+.2f}%")
            print(f"   Total P/L from doubles: ${dd_profit:,.2f}")
    
    print(f"\n{'='*80}\n")
    
    return closed_trades


if __name__ == '__main__':
    json_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/full_history_insider_trades.json'
    
    results = backtest_card_counting_strategy(
        json_file=json_file,
        initial_position_size=1000,
        base_adjustment=0.10
    )
    
    # Save results
    if results:
        import csv
        output_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_card_counting_results.csv'
        
        # Get all possible field names
        all_fields = set()
        for result in results:
            all_fields.update(result.keys())
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(all_fields))
            writer.writeheader()
            writer.writerows(results)
        
        print(f"✅ Results saved to: {output_file}")
