#!/usr/bin/env python3
"""
TREND FOLLOWING STRATEGY - "Ride the Wave, Exit on Double Dip"
================================================================
Core Concept: After insider purchase, wait for announcement catalyst.
Once uptrend starts, hold as long as trend continues.
Exit on second dip that fails to recover (confirms trend reversal).

Rules:
1. Buy on insider purchase signal
2. Grace period: 48 hours (2 business days) minimum hold
3. Stop loss: -5% from entry (safety net)
4. Track highest high (peak price)
5. Detect dips: price drops >X% from recent peak
6. First dip: HOLD and wait for recovery
7. If recovers to new high: reset dip counter, trend continues
8. Second dip without new high: SELL (trend reversed)
"""

import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from multiprocessing import Pool, cpu_count

def fetch_ticker_data(ticker):
    """Fetch historical data for a ticker"""
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(start='2022-03-16', end='2026-02-14')
        
        if not history.empty:
            history.index = history.index.tz_localize(None)
            return (ticker, history)
    except:
        pass
    return (ticker, None)

def parse_value(value_str):
    """Parse value string like '+$8,783,283' to float"""
    if not value_str:
        return 0
    cleaned = value_str.replace('+', '').replace('$', '').replace(',', '')
    try:
        return float(cleaned)
    except:
        return 0

def generate_business_days(start_date, end_date):
    """Generate list of business days between two dates"""
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    business_days = pd.bdate_range(start=start, end=end)
    return [d.strftime('%Y-%m-%d') for d in business_days]

def calculate_velocity(price_history, start_idx, end_idx):
    """Calculate the velocity (slope) of price movement between two points"""
    if end_idx <= start_idx or end_idx >= len(price_history):
        return 0
    
    start_date, start_price = price_history[start_idx]
    end_date, end_price = price_history[end_idx]
    
    days = (end_date - start_date).days
    if days == 0:
        return 0
    
    price_change = end_price - start_price
    velocity = price_change / days  # dollars per day
    
    return velocity

def detect_trend_reversal(position, current_date, history):
    """
    Detect trend reversal using VELOCITY-BASED dip detection.
    Only "violent" dips (similar slope to rise) count as real dips.
    
    Returns: (should_exit, reason, exit_price)
    """
    current_date_ts = pd.Timestamp(current_date)
    
    if current_date_ts not in history.index:
        return (False, None, None)
    
    close_price = history.loc[current_date_ts, 'Close']
    high_price = history.loc[current_date_ts, 'High']
    
    # Add current price to history
    position['price_history'].append((current_date_ts, close_price))
    
    # Calculate current profit from entry
    current_profit_pct = ((close_price - position['entry_price']) / position['entry_price']) * 100
    
    # SAFETY: Hard stop loss at -5% from entry
    if current_profit_pct < -5.0:
        return (True, 'stop_loss', close_price)
    
    # GRACE PERIOD: Don't exit in first 2 business days
    if position['days_held'] <= 2:
        return (False, None, None)
    
    # Update highest price and track peak
    if high_price > position['highest_price']:
        old_peak = position['highest_price']
        position['highest_price'] = high_price
        position['peak_date'] = current_date_ts
        position['peak_idx'] = len(position['price_history']) - 1
        
        # Calculate upward velocity to this peak
        # Look back to find where the rise started (after previous dip/entry)
        lookback_idx = max(0, position['peak_idx'] - 20)  # Look back up to 20 days
        position['up_velocity'] = calculate_velocity(position['price_history'], lookback_idx, position['peak_idx'])
        
        # New high reached - reset dip tracking
        if high_price > old_peak * 1.02:  # At least 2% higher
            position['violent_dip_count'] = 0
            position['in_violent_dip'] = False
            position['failed_recovery'] = False
            print(f"      ✅ NEW HIGH for {position['ticker']}: ${high_price:.2f} - trend intact, reset dip counter")
    
    # Calculate drawdown from peak
    peak = position['highest_price']
    drawdown_pct = ((close_price - peak) / peak) * 100
    
    # Detect if we're in a decline
    if drawdown_pct < -3.0 and not position['in_violent_dip']:  # At least 3% down to start checking
        # Calculate downward velocity
        current_idx = len(position['price_history']) - 1
        peak_idx = position['peak_idx']
        
        if current_idx > peak_idx:
            down_velocity = calculate_velocity(position['price_history'], peak_idx, current_idx)
            
            # Check if this is a VIOLENT dip (velocity comparison)
            # Down velocity should be 60-80% of up velocity (in absolute terms)
            up_vel_abs = abs(position['up_velocity'])
            down_vel_abs = abs(down_velocity)
            
            velocity_ratio = down_vel_abs / up_vel_abs if up_vel_abs > 0 else 0
            
            # VIOLENT DIP: downward slope is at least 50% as steep as upward slope
            if velocity_ratio >= 0.5 and down_vel_abs > 0.05:  # At least $0.05/day decline
                if not position['in_violent_dip']:
                    position['in_violent_dip'] = True
                    position['violent_dip_count'] += 1
                    position['dip_start_date'] = current_date_ts
                    position['dip_start_idx'] = current_idx
                    print(f"      🔻 VIOLENT DIP #{position['violent_dip_count']} for {position['ticker']}")
                    print(f"         Up velocity: ${up_vel_abs:.3f}/day | Down velocity: ${down_vel_abs:.3f}/day | Ratio: {velocity_ratio:.1%}")
    
    # Check if we're recovering from a violent dip
    if position['in_violent_dip']:
        dip_start_idx = position['dip_start_idx']
        current_idx = len(position['price_history']) - 1
        
        if current_idx > dip_start_idx:
            # Find the low point since dip started
            dip_low = min([p for _, p in position['price_history'][dip_start_idx:current_idx + 1]])
            recovery_pct = ((close_price - dip_low) / dip_low) * 100
            
            # Recovery detected: at least 3% up from the low
            if recovery_pct > 3.0:
                print(f"      ↗️  Recovery from violent dip for {position['ticker']}: +{recovery_pct:.1f}% from low")
                position['in_violent_dip'] = False
                
                # Check if we made a NEW HIGH
                if close_price > peak * 0.98:  # Within 2% of old peak
                    print(f"      ✅ Recovery reached near peak - trend continues!")
                    # Don't reset dip count yet, will reset on actual new high
                else:
                    # Failed to make new high - mark this
                    print(f"      ⚠️  Failed recovery - didn't reach new high (peak: ${peak:.2f}, now: ${close_price:.2f})")
                    position['failed_recovery'] = True
    
    # DECISION: Sell on second violent dip after failed recovery
    if position['violent_dip_count'] >= 2 and position['in_violent_dip'] and position['failed_recovery']:
        print(f"      🚨 SECOND VIOLENT DIP after failed recovery - TREND REVERSED - EXITING {position['ticker']}")
        return (True, 'trend_reversal', close_price)
    
    return (False, None, None)

def backtest_trend_following():
    """Backtest the trend following strategy"""
    
    print(f"\n{'='*100}")
    print("TREND FOLLOWING STRATEGY - 'RIDE THE WAVE, EXIT ON DOUBLE DIP'")
    print(f"{'='*100}\n")
    
    # Load insider trades data
    with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/merged_insider_trades.json', 'r') as f:
        data = json.load(f)
    
    tickers = [stock['ticker'] for stock in data['data']]
    
    print(f"🔄 Loading stock data for {len(tickers)} tickers...")
    with Pool(cpu_count()) as pool:
        results = pool.map(fetch_ticker_data, tickers)
    
    price_cache = {}
    for ticker, history in results:
        if history is not None:
            price_cache[ticker] = history
    
    print(f"   ✅ Loaded {len(price_cache)} stocks with price data\n")
    
    # Build trading signals
    all_trades = []
    for stock_data in data['data']:
        ticker = stock_data['ticker']
        
        if ticker not in price_cache:
            continue
        
        company = stock_data['company_name']
        
        for trade in stock_data['trades']:
            if trade.get('value', '').startswith('+'):
                trade_date = trade['trade_date']
                
                if 'filing_date' in trade and trade['filing_date']:
                    filing_date = trade['filing_date'].split()[0]
                else:
                    filing_date = trade_date
                
                entry_date = filing_date
                trade_value = parse_value(trade['value'])
                
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
    
    if not all_trades:
        print("No trades found!")
        return []
    
    start_date = all_trades[0]['entry_date']
    end_date = '2026-02-13'
    
    print(f"📅 Generating business day calendar ({start_date} to {end_date})...")
    all_business_days = generate_business_days(start_date, end_date)
    print(f"   {len(all_business_days)} business days\n")
    
    open_positions = defaultdict(list)
    closed_trades = []
    pending_trades = list(all_trades)
    
    initial_position_size = 1000
    
    print(f"{'='*100}")
    print("RUNNING TREND FOLLOWING BACKTEST")
    print(f"{'='*100}\n")
    
    for day_idx, current_date in enumerate(all_business_days):
        if day_idx % 50 == 0:
            print(f"📆 {current_date} (Day {day_idx+1}/{len(all_business_days)}) | Open: {sum(len(v) for v in open_positions.values())} | Closed: {len(closed_trades)}")
        
        # Open new positions
        trades_to_open = [t for t in pending_trades if t['entry_date'] == current_date]
        
        for trade in trades_to_open:
            ticker = trade['ticker']
            
            if ticker not in price_cache:
                pending_trades.remove(trade)
                continue
            
            history = price_cache[ticker]
            
            current_date_ts = pd.Timestamp(current_date)
            if current_date_ts not in history.index:
                available_dates = sorted([d for d in history.index if d >= current_date_ts])
                if not available_dates:
                    pending_trades.remove(trade)
                    continue
                actual_entry_date = available_dates[0].strftime('%Y-%m-%d')
            else:
                actual_entry_date = current_date
            
            actual_entry_ts = pd.Timestamp(actual_entry_date)
            entry_price = history.loc[actual_entry_ts, 'Close']
            
            position_size = initial_position_size
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
                'days_held': 0,
                'violent_dip_count': 0,
                'in_violent_dip': False,
                'failed_recovery': False,
                'peak_date': actual_entry_ts,
                'peak_idx': 0,
                'up_velocity': 0,
                'dip_start_date': None,
                'dip_start_idx': 0,
                'price_history': [(actual_entry_ts, entry_price)]
            }
            
            open_positions[ticker].append(position)
            pending_trades.remove(trade)
        
        # Check all open positions for exit signals
        for ticker in list(open_positions.keys()):
            if ticker not in price_cache:
                continue
            
            history = price_cache[ticker]
            
            positions_to_close = []
            
            for pos in open_positions[ticker]:
                pos['days_held'] += 1
                
                should_exit, reason, exit_price = detect_trend_reversal(pos, current_date, history)
                
                if should_exit:
                    return_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
                    profit_loss = pos['amount_invested'] * (return_pct / 100)
                    returned_amount = pos['amount_invested'] + profit_loss
                    
                    closed_trades.append({
                        'ticker': ticker,
                        'company': pos['company'],
                        'trade_date': pos['trade_date'],
                        'entry_date': pos['entry_date'],
                        'entry_price': pos['entry_price'],
                        'exit_date': current_date,
                        'exit_price': exit_price,
                        'exit_reason': reason,
                        'amount_invested': pos['amount_invested'],
                        'returned_amount': returned_amount,
                        'profit_loss': profit_loss,
                        'return_pct': return_pct,
                        'shares': pos['shares'],
                        'days_held': pos['days_held'],
                        'highest_price': pos['highest_price'],
                        'peak_gain': ((pos['highest_price'] - pos['entry_price']) / pos['entry_price']) * 100
                    })
                    
                    positions_to_close.append(pos)
            
            for pos in positions_to_close:
                open_positions[ticker].remove(pos)
            
            if not open_positions[ticker]:
                del open_positions[ticker]
    
    # Close remaining positions
    print(f"\n{'='*100}")
    print("CLOSING REMAINING OPEN POSITIONS")
    print(f"{'='*100}\n")
    
    for ticker, positions in open_positions.items():
        if ticker not in price_cache:
            continue
        
        history = price_cache[ticker]
        end_date_ts = pd.Timestamp(end_date)
        available_dates = sorted([d for d in history.index if d <= end_date_ts])
        
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
                'exit_date': final_date.strftime('%Y-%m-%d'),
                'exit_price': final_price,
                'exit_reason': 'end_of_period',
                'amount_invested': pos['amount_invested'],
                'returned_amount': returned_amount,
                'profit_loss': profit_loss,
                'return_pct': return_pct,
                'shares': pos['shares'],
                'days_held': pos['days_held'],
                'highest_price': pos['highest_price'],
                'peak_gain': ((pos['highest_price'] - pos['entry_price']) / pos['entry_price']) * 100
            })
    
    # Calculate results
    if not closed_trades:
        print("❌ No trades were executed!")
        return []
    
    df = pd.DataFrame(closed_trades)
    
    total_invested = df['amount_invested'].sum()
    total_returned = df['returned_amount'].sum()
    total_profit = df['profit_loss'].sum()
    roi = (total_profit / total_invested) * 100
    
    winning_trades = df[df['return_pct'] > 0]
    losing_trades = df[df['return_pct'] <= 0]
    
    win_rate = len(winning_trades) / len(df) * 100
    avg_return = df['return_pct'].mean()
    median_return = df['return_pct'].median()
    avg_days_held = df['days_held'].mean()
    avg_peak_gain = df['peak_gain'].mean()
    
    print(f"\n{'='*100}")
    print("FINAL RESULTS - TREND FOLLOWING STRATEGY")
    print(f"{'='*100}")
    print(f"Total Trades: {len(df)}")
    print(f"  Winning: {len(winning_trades)} ({win_rate:.1f}%)")
    print(f"  Losing: {len(losing_trades)} ({100-win_rate:.1f}%)")
    print(f"\nAverage Return per Trade: {avg_return:+.2f}%")
    print(f"Median Return per Trade: {median_return:+.2f}%")
    print(f"Average Peak Gain: {avg_peak_gain:+.2f}% (how high it went)")
    print(f"Average Days Held: {avg_days_held:.0f} days")
    print(f"\n💰 PORTFOLIO PERFORMANCE:")
    print(f"   Total Invested: ${total_invested:,.2f}")
    print(f"   Total Returned: ${total_returned:,.2f}")
    print(f"   Net Profit/Loss: ${total_profit:,.2f}")
    print(f"   ROI: {roi:+.2f}%")
    
    # Exit reason breakdown
    print(f"\n📊 EXIT REASONS:")
    for reason in df['exit_reason'].unique():
        count = len(df[df['exit_reason'] == reason])
        avg_return = df[df['exit_reason'] == reason]['return_pct'].mean()
        print(f"   {reason}: {count} trades (avg return: {avg_return:+.2f}%)")
    
    best_trade = df.loc[df['return_pct'].idxmax()]
    print(f"\n🏆 Best Trade: {best_trade['ticker']} - {best_trade['return_pct']:+.1f}%")
    print(f"   ${best_trade['entry_price']:.2f} → ${best_trade['exit_price']:.2f} ({int(best_trade['days_held'])} days)")
    print(f"   Peak: ${best_trade['highest_price']:.2f} ({best_trade['peak_gain']:+.1f}%)")
    
    worst_trade = df.loc[df['return_pct'].idxmin()]
    print(f"\n💀 Worst Trade: {worst_trade['ticker']} - {worst_trade['return_pct']:+.1f}%")
    print(f"   ${worst_trade['entry_price']:.2f} → ${worst_trade['exit_price']:.2f} ({int(worst_trade['days_held'])} days)")
    
    print(f"\n{'='*100}\n")
    
    output_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_latest_results.csv'
    df.to_csv(output_path, index=False)
    print(f"✅ Results saved to: {output_path}")
    
    return closed_trades

if __name__ == '__main__':
    backtest_trend_following()
