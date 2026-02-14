#!/usr/bin/env python3
"""
Aggressive Momentum Strategy with DAILY Position Checks
========================================================
Same aggressive rules as before, but checks EVERY business day (realistic trading).

Uses multiprocessing to speed up execution.
"""

import json
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
from multiprocessing import Pool, cpu_count
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


def generate_business_days(start_date, end_date):
    """Generate all business days between start and end"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    business_days = []
    current = start
    
    while current <= end:
        if current.weekday() < 5:  # Monday = 0, Sunday = 6
            business_days.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return business_days


def parse_value(value_str):
    """Convert '+$69,297,690' to 69297690.0"""
    if not value_str:
        return 0.0
    cleaned = value_str.replace('+', '').replace('$', '').replace(',', '').replace('-', '')
    try:
        return float(cleaned)
    except:
        return 0.0


def fetch_ticker_data(ticker):
    """Fetch historical data for a single ticker (for multiprocessing)"""
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(start='2022-01-01', end='2026-02-14')
        if not history.empty:
            history.index = pd.to_datetime(history.index).strftime('%Y-%m-%d')
            print(f"  ✓ {ticker} ({len(history)} days)")
            return (ticker, history)
        else:
            print(f"  ✗ {ticker} (no data)")
            return (ticker, None)
    except Exception as e:
        print(f"  ✗ {ticker} (error: {e})")
        return (ticker, None)


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


def backtest_aggressive_daily():
    """
    Backtest with daily position checks - realistic trading simulation.
    Uses MERGED data (full history + monthly) to include all stocks.
    """
    json_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/merged_insider_trades.json'
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Load all tickers in parallel
    print("🚀 Loading historical data with multiprocessing...")
    print(f"📊 Processing {len(data['data'])} stocks from merged dataset...")
    all_tickers = list(set(stock['ticker'] for stock in data['data']))
    
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(fetch_ticker_data, all_tickers)
    
    price_cache = {ticker: history for ticker, history in results if history is not None}
    print(f"\n✅ Loaded data for {len(price_cache)} tickers\n")
    
    # Build insider purchase timeline
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
                    filing_date = trade['filing_date'].split()[0]
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
    
    all_trades.sort(key=lambda x: x['entry_date'])
    
    # Generate all business days from first trade to today
    if not all_trades:
        print("No trades found!")
        return []
    
    start_date = all_trades[0]['entry_date']
    end_date = '2026-02-13'
    
    print(f"📅 Generating business day calendar ({start_date} to {end_date})...")
    all_business_days = generate_business_days(start_date, end_date)
    print(f"   {len(all_business_days)} business days\n")
    
    # Track positions
    open_positions = defaultdict(list)
    closed_trades = []
    pending_trades = list(all_trades)  # Trades waiting to be opened
    
    initial_position_size = 1000
    
    print(f"{'='*80}")
    print("STARTING DAILY-CHECKED AGGRESSIVE MOMENTUM BACKTEST")
    print(f"{'='*80}\n")
    
    # Process each business day
    for day_idx, current_date in enumerate(all_business_days):
        if day_idx % 50 == 0:
            print(f"📆 Processing: {current_date} (Day {day_idx+1}/{len(all_business_days)}) | Open positions: {sum(len(v) for v in open_positions.values())}")
        
        # Open any trades that start on this date
        trades_to_open = [t for t in pending_trades if t['entry_date'] == current_date]
        
        for trade in trades_to_open:
            ticker = trade['ticker']
            
            if ticker not in price_cache:
                continue
            
            history = price_cache[ticker]
            
            # Get entry price for this date
            if current_date not in history.index:
                # Find next available date
                available_dates = sorted([d for d in history.index if d >= current_date])
                if not available_dates:
                    continue
                actual_entry_date = available_dates[0]
            else:
                actual_entry_date = current_date
            
            entry_price = history.loc[actual_entry_date, 'Close']
            
            # Calculate position size based on insider momentum
            recent_purchase_count = count_recent_insider_purchases(ticker, current_date, all_insider_purchases, days_back=14)
            
            position_multiplier = 1.0
            if recent_purchase_count >= 5:
                position_multiplier = 2.0
            elif recent_purchase_count >= 3:
                position_multiplier = 1.5
            
            # Check if we should double down on existing profitable positions
            for pos in open_positions[ticker]:
                if current_date in history.index:
                    current_price = history.loc[current_date, 'Close']
                    current_profit_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                    
                    if current_profit_pct > 15:
                        position_multiplier = 0.5  # Add 50% of original position
                        break
            
            position_size = initial_position_size * position_multiplier
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
                'highest_price': entry_price,
                'days_held': 0
            }
            
            open_positions[ticker].append(position)
            pending_trades.remove(trade)
        
        # Check all open positions on this day
        for ticker in list(open_positions.keys()):
            if ticker not in price_cache:
                continue
            
            history = price_cache[ticker]
            
            if current_date not in history.index:
                continue
            
            high_price = history.loc[current_date, 'High']
            low_price = history.loc[current_date, 'Low']
            close_price = history.loc[current_date, 'Close']
            
            # Handle missing High/Low data (some stocks don't have intraday data)
            if pd.isna(high_price) or high_price is None:
                high_price = close_price
            if pd.isna(low_price) or low_price is None:
                low_price = close_price
            
            for pos in open_positions[ticker][:]:
                pos['days_held'] += 1
                
                # Update highest price
                if high_price > pos['highest_price']:
                    pos['highest_price'] = high_price
                
                current_profit_pct = ((close_price - pos['entry_price']) / pos['entry_price']) * 100
                
                # GRACE PERIOD: No stop loss for first 5 business days
                if pos['days_held'] <= 5:
                    continue
                
                # PROFIT CUSHION: Only apply stop loss if we're below +3% profit
                if current_profit_pct >= 3.0:
                    continue
                
                # Determine stop loss percentage
                has_recent_insider = has_insider_purchase_within_days(ticker, current_date, all_insider_purchases, days_back=7)
                
                if current_profit_pct > 10:
                    stop_loss_pct = 0.10
                elif current_profit_pct > 5:
                    stop_loss_pct = 0.07
                elif has_recent_insider:
                    stop_loss_pct = 0.07
                else:
                    stop_loss_pct = 0.05
                
                trailing_stop_price = pos['highest_price'] * (1 - stop_loss_pct)
                
                # Check if stop loss hit
                if low_price <= trailing_stop_price:
                    # Use realistic fill: the trailing stop price OR the open price if it gapped down
                    # For simplicity, use close price as a conservative estimate
                    actual_exit_price = min(trailing_stop_price, close_price)
                    
                    return_pct = ((actual_exit_price - pos['entry_price']) / pos['entry_price']) * 100
                    profit_loss = pos['amount_invested'] * (return_pct / 100)
                    returned_amount = pos['amount_invested'] + profit_loss
                    
                    closed_trades.append({
                        'ticker': ticker,
                        'company': pos['company'],
                        'trade_date': pos['trade_date'],
                        'entry_date': pos['entry_date'],
                        'entry_price': pos['entry_price'],
                        'exit_date': current_date,
                        'exit_price': actual_exit_price,
                        'exit_reason': 'stop_loss',
                        'amount_invested': pos['amount_invested'],
                        'returned_amount': returned_amount,
                        'profit_loss': profit_loss,
                        'return_pct': return_pct,
                        'shares': pos['shares'],
                        'insider': pos['insider'],
                        'role': pos['role'],
                        'peak_price': pos['highest_price'],
                        'highest_price': pos['highest_price'],
                        'days_held': pos['days_held']
                    })
                    
                    open_positions[ticker].remove(pos)
    
    # Close remaining positions
    print(f"\n{'='*80}")
    print("CLOSING REMAINING OPEN POSITIONS")
    print(f"{'='*80}\n")
    
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
                'highest_price': pos['highest_price'],
                'days_held': pos['days_held']
            })
    
    # Calculate results
    print(f"\n{'='*80}")
    print("FINAL RESULTS - DAILY-CHECKED AGGRESSIVE STRATEGY")
    print(f"{'='*80}\n")
    
    total_trades = len(closed_trades)
    winning_trades = [t for t in closed_trades if t['profit_loss'] > 0]
    losing_trades = [t for t in closed_trades if t['profit_loss'] <= 0]
    
    total_invested = sum(t['amount_invested'] for t in closed_trades)
    total_returned = sum(t['returned_amount'] for t in closed_trades)
    net_profit = total_returned - total_invested
    
    avg_return = sum(t['return_pct'] for t in closed_trades) / len(closed_trades) if closed_trades else 0
    avg_days_held = sum(t['days_held'] for t in closed_trades) / len(closed_trades) if closed_trades else 0
    
    print(f"Total Trades: {total_trades}")
    print(f"  Winning: {len(winning_trades)} ({len(winning_trades)/total_trades*100:.1f}%)")
    print(f"  Losing: {len(losing_trades)} ({len(losing_trades)/total_trades*100:.1f}%)")
    print(f"\nAverage Return per Trade: {avg_return:+.2f}%")
    print(f"Average Days Held: {avg_days_held:.0f} days")
    
    print(f"\n💰 PORTFOLIO PERFORMANCE:")
    print(f"   Total Invested: ${total_invested:,.2f}")
    print(f"   Total Returned: ${total_returned:,.2f}")
    print(f"   Net Profit/Loss: ${net_profit:,.2f}")
    print(f"   ROI: {(net_profit/total_invested*100):+.2f}%")
    
    if winning_trades:
        best_trade = max(winning_trades, key=lambda x: x['return_pct'])
        print(f"\n🏆 Best Trade: {best_trade['ticker']} - {best_trade['return_pct']:+.1f}%")
        print(f"   ${best_trade['entry_price']:.2f} → ${best_trade['exit_price']:.2f} ({best_trade['days_held']} days)")
        print(f"   Invested: ${best_trade['amount_invested']:,.0f} | Returned: ${best_trade['returned_amount']:,.0f}")
    
    if losing_trades:
        worst_trade = min(losing_trades, key=lambda x: x['return_pct'])
        print(f"\n💀 Worst Trade: {worst_trade['ticker']} - {worst_trade['return_pct']:+.1f}%")
        print(f"   ${worst_trade['entry_price']:.2f} → ${worst_trade['exit_price']:.2f} ({worst_trade['days_held']} days)")
    
    # Show longest holds
    longest_holds = sorted(closed_trades, key=lambda x: x['days_held'], reverse=True)[:5]
    print(f"\n📊 Longest Positions Held:")
    for t in longest_holds:
        print(f"   {t['ticker']}: {t['days_held']} days | {t['return_pct']:+.1f}% | {t['exit_reason']}")
    
    print(f"\n{'='*80}\n")
    
    return closed_trades


if __name__ == '__main__':
    results = backtest_aggressive_daily()
    
    if results:
        import csv
        output_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_aggressive_daily_results.csv'
        
        all_fields = set()
        for result in results:
            all_fields.update(result.keys())
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(all_fields))
            writer.writeheader()
            writer.writerows(results)
        
        print(f"✅ Results saved to: {output_file}")
