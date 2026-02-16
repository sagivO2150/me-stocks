#!/usr/bin/env python3
"""
Test different strategies for penny stocks:
1. No penny stocks at all (filter them out)
2. Tighter rules for penny stocks
3. Current strategy (baseline)
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

def detect_trend_reversal(position, current_date, history, strategy_mode='current'):
    """
    Detect trend reversal - strategy varies by mode
    
    strategy_mode:
    - 'current': Normal rules (5%/day, 3%/day, -5% stop, 15 days)
    - 'tight_penny': Tighter rules for penny stocks (7%/day, 4%/day, -3% stop, 10 days)
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
    
    # GRACE PERIOD: Don't exit in first 2 business days
    if position['days_held'] <= 2:
        return (False, None, None)
    
    # Strategy-specific parameters
    is_penny = position['entry_price'] < 5.0
    
    if strategy_mode == 'tight_penny' and is_penny:
        stop_loss_pct = -3.0
        catalyst_timeout_days = 10
        catalyst_drawdown = -12.0
        first_dip_threshold = 7.0
        second_dip_threshold = 4.0
    else:
        stop_loss_pct = -5.0
        catalyst_timeout_days = 15
        catalyst_drawdown = -15.0
        first_dip_threshold = 5.0
        second_dip_threshold = 3.0
    
    # Update highest price and track peak
    if high_price > position['highest_price']:
        old_peak = position['highest_price']
        position['highest_price'] = high_price
        position['peak_date'] = current_date_ts
        position['peak_idx'] = len(position['price_history']) - 1
        
        if close_price > position.get('last_close', position['entry_price']):
            position['consecutive_up_days'] = position.get('consecutive_up_days', 0) + 1
        else:
            position['consecutive_up_days'] = 1
        
        position['consecutive_decline_days'] = 0
        
        # EXPLOSIVE CATALYST DETECTION
        if not position.get('catalyst_detected', False):
            lookback_window = min(5, len(position['price_history']))
            if lookback_window >= 3:
                lookback_idx = len(position['price_history']) - lookback_window
                lookback_price = position['price_history'][lookback_idx][1]
                gain_pct = ((high_price - lookback_price) / lookback_price) * 100
                
                if gain_pct > 20.0:
                    position['catalyst_detected'] = True
                    position['catalyst_price'] = high_price
                    position['days_since_peak'] = 0
        
        # New high reached - reset dip tracking
        if high_price > old_peak * 1.02:
            position['violent_dip_count'] = 0
            position['in_violent_dip'] = False
            position['failed_recovery'] = False
            position['days_since_peak'] = 0
    else:
        position['days_since_peak'] = position.get('days_since_peak', 0) + 1
        
        if close_price < position.get('last_close', position['entry_price']):
            position['consecutive_up_days'] = 0
        else:
            position['consecutive_up_days'] = position.get('consecutive_up_days', 0) + 1
    
    position['last_close'] = close_price
    
    # SAFETY STOP LOSS
    catalyst_detected = position.get('catalyst_detected', False)
    days_since_peak = position.get('days_since_peak', 0)
    peak = position['highest_price']
    drawdown_from_peak_pct = ((close_price - peak) / peak) * 100
    
    # Expire catalyst tracking
    catalyst_expired = False
    if catalyst_detected and (days_since_peak >= catalyst_timeout_days or drawdown_from_peak_pct <= catalyst_drawdown):
        catalyst_expired = True
    
    # Apply stop loss if no catalyst or expired
    if (not catalyst_detected or catalyst_expired) and current_profit_pct < stop_loss_pct:
        return (True, 'stop_loss', close_price)
    
    # SLOPE-BASED DIP DETECTION: Only after catalyst detected
    if not catalyst_detected:
        return (False, None, None)
    
    # Calculate drawdown from peak
    drawdown_pct = ((close_price - peak) / peak) * 100
    
    # Detect violent dips
    if drawdown_pct < -3.0 and not position['in_violent_dip']:
        is_violent = False
        reason = ""
        
        current_idx = len(position['price_history']) - 1
        lookback = min(2, current_idx)
        if lookback > 0:
            lookback_idx = current_idx - lookback
            recent_prices = position['price_history'][lookback_idx:current_idx + 1]
            
            start_price = recent_prices[0][1]
            end_price = recent_prices[-1][1]
            days = len(recent_prices) - 1
            
            if days > 0 and start_price > 0:
                price_change_pct = ((end_price - start_price) / start_price) * 100
                slope_pct_per_day = price_change_pct / days
                slope_pct_abs = abs(slope_pct_per_day)
            else:
                slope_pct_per_day = 0
                slope_pct_abs = 0
            
            if position.get('violent_dip_count', 0) == 0:
                # First dip: strategy-specific threshold
                if slope_pct_abs > first_dip_threshold:
                    is_violent = True
                    position['first_dip_slope'] = slope_pct_abs
                    reason = f"slope {slope_pct_abs:.1f}%/day (first dip)"
            else:
                # Second dip: Compare to first dip
                first_dip_slope = position.get('first_dip_slope', 0)
                if first_dip_slope > 0:
                    slope_ratio = slope_pct_abs / first_dip_slope
                    
                    if slope_ratio >= 0.5 and slope_pct_abs > second_dip_threshold:
                        is_violent = True
                        reason = f"slope {slope_pct_abs:.1f}%/day vs {first_dip_slope:.1f}%/day"
            
            if is_violent:
                position['in_violent_dip'] = True
                position['violent_dip_count'] += 1
                position['dip_start_date'] = current_date_ts
                position['dip_start_idx'] = current_idx
    
    # Check recovery from violent dip
    if position['in_violent_dip']:
        dip_start_idx = position['dip_start_idx']
        current_idx = len(position['price_history']) - 1
        
        if current_idx > dip_start_idx:
            dip_low = min([p for _, p in position['price_history'][dip_start_idx:current_idx + 1]])
            recovery_pct = ((close_price - dip_low) / dip_low) * 100
            
            if recovery_pct > 3.0:
                peak = position['highest_price']
                if close_price > peak * 0.98:
                    position['failed_recovery'] = False
                else:
                    position['failed_recovery'] = True
                
                position['in_violent_dip'] = False
    
    # DECISION: Sell on second violent dip after failed recovery
    if position['violent_dip_count'] >= 2 and position['in_violent_dip'] and position['failed_recovery']:
        return (True, 'trend_reversal', close_price)
    
    return (False, None, None)

def run_backtest(strategy_mode='current', min_entry_price=0):
    """
    Run backtest with specific strategy
    
    strategy_mode:
    - 'current': Current rules
    - 'tight_penny': Tighter rules for penny stocks
    - 'no_penny': Filter out penny stocks
    
    min_entry_price: Minimum entry price (0 = all stocks)
    """
    
    # Load insider trades data
    with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/merged_insider_trades.json', 'r') as f:
        data = json.load(f)
    
    tickers = [stock['ticker'] for stock in data['data']]
    
    with Pool(cpu_count()) as pool:
        results = pool.map(fetch_ticker_data, tickers)
    
    price_cache = {}
    for ticker, history in results:
        if history is not None:
            price_cache[ticker] = history
    
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
        return []
    
    start_date = all_trades[0]['entry_date']
    end_date = '2026-02-13'
    
    all_business_days = generate_business_days(start_date, end_date)
    
    open_positions = defaultdict(list)
    closed_trades = []
    pending_trades = list(all_trades)
    
    initial_position_size = 1000
    
    for day_idx, current_date in enumerate(all_business_days):
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
            
            # FILTER: Skip if below minimum entry price
            if entry_price < min_entry_price:
                pending_trades.remove(trade)
                continue
            
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
                'catalyst_detected': False,
                'consecutive_up_days': 0,
                'days_since_peak': 0,
                'first_dip_slope': 0,
                'last_close': entry_price,
                'peak_date': actual_entry_ts,
                'peak_idx': 0,
                'catalyst_price': 0,
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
                
                should_exit, reason, exit_price = detect_trend_reversal(pos, current_date, history, strategy_mode)
                
                if should_exit:
                    return_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
                    profit_loss = pos['amount_invested'] * (return_pct / 100)
                    returned_amount = pos['amount_invested'] + profit_loss
                    
                    closed_trades.append({
                        'ticker': ticker,
                        'company': pos['company'],
                        'entry_date': pos['entry_date'],
                        'entry_price': pos['entry_price'],
                        'exit_date': current_date,
                        'exit_price': exit_price,
                        'exit_reason': reason,
                        'amount_invested': pos['amount_invested'],
                        'returned_amount': returned_amount,
                        'profit_loss': profit_loss,
                        'return_pct': return_pct,
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
                'entry_date': pos['entry_date'],
                'entry_price': pos['entry_price'],
                'exit_date': final_date.strftime('%Y-%m-%d'),
                'exit_price': final_price,
                'exit_reason': 'end_of_period',
                'amount_invested': pos['amount_invested'],
                'returned_amount': returned_amount,
                'profit_loss': profit_loss,
                'return_pct': return_pct,
                'days_held': pos['days_held'],
                'highest_price': pos['highest_price'],
                'peak_gain': ((pos['highest_price'] - pos['entry_price']) / pos['entry_price']) * 100
            })
    
    return closed_trades

def print_results(trades, strategy_name):
    """Print backtest results"""
    if not trades:
        print(f"❌ No trades for {strategy_name}")
        return
    
    df = pd.DataFrame(trades)
    
    total_invested = df['amount_invested'].sum()
    total_returned = df['returned_amount'].sum()
    total_profit = df['profit_loss'].sum()
    roi = (total_profit / total_invested) * 100
    
    winning_trades = df[df['return_pct'] > 0]
    losing_trades = df[df['return_pct'] <= 0]
    
    win_rate = len(winning_trades) / len(df) * 100
    avg_return = df['return_pct'].mean()
    median_return = df['return_pct'].median()
    
    # Count penny vs regular
    penny_trades = df[df['entry_price'] < 5.0]
    regular_trades = df[df['entry_price'] >= 5.0]
    
    print(f"\n{'='*80}")
    print(f"{strategy_name}")
    print(f"{'='*80}")
    print(f"Total Trades: {len(df)}")
    print(f"  Penny Stocks (<$5): {len(penny_trades)} trades")
    print(f"  Regular Stocks (≥$5): {len(regular_trades)} trades")
    print(f"Winning: {len(winning_trades)} ({win_rate:.1f}%)")
    print(f"Average Return: {avg_return:+.2f}%")
    print(f"Median Return: {median_return:+.2f}%")
    print(f"\n💰 ROI: {roi:+.2f}%")
    print(f"   Invested: ${total_invested:,.2f}")
    print(f"   Returned: ${total_returned:,.2f}")
    print(f"   Profit: ${total_profit:,.2f}")
    
    # Exit reason breakdown
    print(f"\n📊 Exit Reasons:")
    for reason in df['exit_reason'].unique():
        count = len(df[df['exit_reason'] == reason])
        avg_ret = df[df['exit_reason'] == reason]['return_pct'].mean()
        print(f"   {reason}: {count} trades @ {avg_ret:+.2f}% avg")

if __name__ == '__main__':
    print(f"\n{'='*80}")
    print("TESTING PENNY STOCK STRATEGIES")
    print(f"{'='*80}\n")
    
    print("⏳ Running Strategy 1: CURRENT (baseline)...")
    current_trades = run_backtest(strategy_mode='current', min_entry_price=0)
    print_results(current_trades, "STRATEGY 1: CURRENT (All stocks, normal rules)")
    
    print("\n⏳ Running Strategy 2: NO PENNY STOCKS (filter entry_price < $5)...")
    no_penny_trades = run_backtest(strategy_mode='current', min_entry_price=5.0)
    print_results(no_penny_trades, "STRATEGY 2: NO PENNY STOCKS (≥$5 only)")
    
    print("\n⏳ Running Strategy 3: TIGHTER PENNY RULES...")
    tight_penny_trades = run_backtest(strategy_mode='tight_penny', min_entry_price=0)
    print_results(tight_penny_trades, "STRATEGY 3: TIGHTER PENNY RULES (7%/4% dips, -3% stop, 10 days)")
    
    print(f"\n{'='*80}")
    print("COMPARISON SUMMARY")
    print(f"{'='*80}")
    
    if current_trades and no_penny_trades and tight_penny_trades:
        current_roi = sum(t['profit_loss'] for t in current_trades) / sum(t['amount_invested'] for t in current_trades) * 100
        no_penny_roi = sum(t['profit_loss'] for t in no_penny_trades) / sum(t['amount_invested'] for t in no_penny_trades) * 100
        tight_penny_roi = sum(t['profit_loss'] for t in tight_penny_trades) / sum(t['amount_invested'] for t in tight_penny_trades) * 100
        
        print(f"\nCurrent Strategy: {current_roi:+.2f}% ({len(current_trades)} trades)")
        print(f"No Penny Stocks: {no_penny_roi:+.2f}% ({len(no_penny_trades)} trades)")
        print(f"Tighter Penny Rules: {tight_penny_roi:+.2f}% ({len(tight_penny_trades)} trades)")
        
        if no_penny_roi > current_roi:
            improvement = no_penny_roi - current_roi
            print(f"\n✅ NO PENNY STOCKS wins by +{improvement:.2f}% ROI!")
        elif tight_penny_roi > current_roi:
            improvement = tight_penny_roi - current_roi
            print(f"\n✅ TIGHTER PENNY RULES wins by +{improvement:.2f}% ROI!")
        else:
            print(f"\n⚠️  Current strategy is already optimal")
