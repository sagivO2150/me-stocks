#!/usr/bin/env python3
"""
Rise Event Strategy Backtest

Strategy Rules:
1. When insider buys, we expect an EXPLOSION
2. Buy DURING rise events (not after waiting for falls)
3. Exit when rise event ends
4. If rise is weak compared to previous rises, exit immediately or don't buy
5. Re-enter on next rise if explosion hasn't happened yet
6. The explosion is the goal - once we get it, we're done with that ticker
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import os

def load_insider_trades():
    """Load insider trades from expanded_insider_trades.json."""
    with open('output CSVs/expanded_insider_trades.json', 'r') as f:
        data = json.load(f)
    return data.get('data', [])

def load_yfinance_cache():
    """Load yfinance cache."""
    with open('output CSVs/yfinance_cache_full.json', 'r') as f:
        return json.load(f)

def parse_date(date_str):
    """Parse date string in DD/MM/YYYY format."""
    return datetime.strptime(date_str, '%d/%m/%Y')

def identify_rise_events(df: pd.DataFrame, min_days: int = 4, min_growth_pct: float = 2.0, 
                        min_decline_pct: float = 1.5, min_recovery_pct: float = 2.0) -> List[Dict]:
    """
    Identify rise events in stock price data.
    Returns list of rise events with start_date, end_date, days, growth_pct, start_price, end_price.
    """
    rise_events = []
    
    if len(df) < 3:
        return rise_events
    
    in_rise_event = False
    current_start_idx = None
    current_start_price = None
    peak_idx = None
    peak_price = None
    consecutive_dips = 0
    
    hunting_bottom = True
    potential_bottom_idx = 0
    potential_bottom_price = df['Close'].iloc[0]
    
    for i in range(len(df)):
        current_price = df['Close'].iloc[i]
        
        if hunting_bottom:
            if current_price <= potential_bottom_price:
                potential_bottom_idx = i
                potential_bottom_price = current_price
            
            if i > 0 and current_price > df['Close'].iloc[i - 1]:
                in_rise_event = True
                hunting_bottom = False
                current_start_idx = potential_bottom_idx
                current_start_price = potential_bottom_price
                peak_idx = i
                peak_price = current_price
                consecutive_dips = 0
            continue
        
        prev_price = df['Close'].iloc[i - 1]
        
        if current_price > prev_price:
            recovery_pct = ((current_price - prev_price) / prev_price) * 100
            
            if recovery_pct >= min_recovery_pct:
                consecutive_dips = 0
            
            if current_price > peak_price:
                peak_idx = i
                peak_price = current_price
                consecutive_dips = 0
                
        elif current_price < prev_price:
            decline_pct = ((prev_price - current_price) / prev_price) * 100
            
            if decline_pct >= min_decline_pct:
                consecutive_dips += 1
            
            if consecutive_dips >= 2 and peak_idx > current_start_idx:
                start_date = df.index[current_start_idx]
                end_date = df.index[peak_idx]
                growth_pct = ((peak_price - current_start_price) / current_start_price) * 100
                days_duration = peak_idx - current_start_idx + 1
                
                if days_duration >= min_days and growth_pct >= min_growth_pct:
                    rise_events.append({
                        'start_date': start_date,
                        'end_date': end_date,
                        'days': days_duration,
                        'growth_pct': round(growth_pct, 2),
                        'start_price': round(current_start_price, 2),
                        'end_price': round(peak_price, 2)
                    })
                
                in_rise_event = False
                hunting_bottom = True
                potential_bottom_idx = i
                potential_bottom_price = current_price
                consecutive_dips = 0
    
    # Handle last rise event if still active
    if in_rise_event and peak_idx is not None and peak_idx > current_start_idx:
        start_date = df.index[current_start_idx]
        end_date = df.index[peak_idx]
        growth_pct = ((peak_price - current_start_price) / current_start_price) * 100
        days_duration = peak_idx - current_start_idx + 1
        
        if days_duration >= min_days and growth_pct >= min_growth_pct:
            rise_events.append({
                'start_date': start_date,
                'end_date': end_date,
                'days': days_duration,
                'growth_pct': round(growth_pct, 2),
                'start_price': round(current_start_price, 2),
                'end_price': round(peak_price, 2)
            })
    
    return rise_events

def is_weak_rise(current_rise_pct: float, previous_rises: List[float], min_ratio: float = 0.5) -> bool:
    """
    Check if current rise is weak compared to previous rises.
    Returns True if current rise is less than min_ratio of the best previous rise.
    """
    if not previous_rises:
        return False  # First rise, can't compare
    
    best_previous = max(previous_rises)
    return current_rise_pct < (best_previous * min_ratio)

def backtest_rise_event_strategy():
    """Run backtest using rise event strategy."""
    
    print("Loading insider trades...")
    insider_data = load_insider_trades()
    
    print("Loading yfinance cache...")
    yfinance_cache = load_yfinance_cache()
    
    # Filter for stocks with insider purchases >= $20K
    qualifying_stocks = []
    
    for stock in insider_data:
        ticker = stock.get('ticker')
        trades = stock.get('trades', [])
        
        # Find qualifying trades (purchases >= $20K)
        for trade in trades:
            shares_str = trade.get('shares', '')
            value_str = trade.get('value', '')
            
            # Check if it's a purchase (positive shares)
            if isinstance(shares_str, str) and '+' in shares_str:
                # Parse value: "+$1450221" -> 1450221
                try:
                    value = float(value_str.replace('+$', '').replace('$', '').replace(',', ''))
                    if value >= 20000:
                        qualifying_stocks.append({
                            'ticker': ticker,
                            'trade_date': trade.get('trade_date'),
                            'value': value,
                            'insider_name': trade.get('insider_name', 'Unknown'),
                            'title': trade.get('title', '')
                        })
                except (ValueError, AttributeError):
                    continue
    
    print(f"Found {len(qualifying_stocks)} qualifying insider purchases")
    
    all_trades = []
    debug_counters = {
        'no_cache': 0,
        'empty_df': 0,
        'ipo_wait': 0,
        'price_too_high': 0,
        'not_at_low': 0,
        'no_rise_events': 0,
        'processed': 0
    }
    
    for i, stock_trade in enumerate(qualifying_stocks):
        ticker = stock_trade['ticker']
        insider_date_str = stock_trade['trade_date']  # YYYY-MM-DD
        insider_date = datetime.strptime(insider_date_str, '%Y-%m-%d')
        
        if ticker not in yfinance_cache:
            debug_counters['no_cache'] += 1
            continue
        
        # Get price data
        price_data = yfinance_cache[ticker]
        df = pd.DataFrame(price_data)
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)
        
        if df.empty:
            debug_counters['empty_df'] += 1
            continue
        
        # Check 3-month IPO wait period
        ipo_date = df.index[0]
        ipo_plus_3_months = ipo_date + timedelta(days=90)
        if insider_date < ipo_plus_3_months:
            debug_counters['ipo_wait'] += 1
            continue
        
        # Skip if entry price >= $5
        insider_date_prices = df[df.index.date == insider_date.date()]
        if insider_date_prices.empty:
            # Try to find closest date after insider trade
            future_dates = df[df.index >= insider_date]
            if future_dates.empty:
                continue
            entry_price = future_dates.iloc[0]['Close']
        else:
            entry_price = insider_date_prices.iloc[0]['Close']
        
        if entry_price >= 5:
            debug_counters['price_too_high'] += 1
            continue
        
        # Check if stock is at all-time low (within 30% of lowest historical price before insider trade)
        hist_before_insider = df[df.index < insider_date]
        if not hist_before_insider.empty:
            hist_min = hist_before_insider['Close'].min()
            if entry_price > hist_min * 1.30:
                debug_counters['not_at_low'] += 1
                continue
        
        # Identify all rise events for this stock
        rise_events = identify_rise_events(df)
        
        if not rise_events:
            debug_counters['no_rise_events'] += 1
            continue
        
        debug_counters['processed'] += 1
        
        # Find which rise event (if any) the insider trade occurred during
        active_trades = []  # Track our trades for this ticker
        previous_rise_pcts = []  # Track rise percentages we've seen
        explosion_found = False  # Have we found the explosion yet?
        
        for event_idx, rise_event in enumerate(rise_events):
            event_start = rise_event['start_date']
            event_end = rise_event['end_date']
            
            # Check if insider trade occurred during this rise event
            if event_start.date() <= insider_date.date() <= event_end.date():
                # Insider bought DURING this rise - BUY IMMEDIATELY
                # Use price on insider date or next available
                buy_dates = df[df.index >= insider_date]
                if buy_dates.empty:
                    continue
                
                buy_date = buy_dates.index[0]
                buy_price = buy_dates.iloc[0]['Close']
                
                # Determine position size
                c_level_titles = ['CEO', 'CFO', 'COO', 'CTO', 'President', 'Chief', 'Vice Chair']
                insider_info = f"{stock_trade['insider_name']} {stock_trade.get('title', '')}"
                is_c_level = any(title in insider_info for title in c_level_titles)
                position_size = 4000 if is_c_level else 2000
                
                # Exit when rise event ends
                sell_date = event_end
                sell_price = rise_event['end_price']
                
                # Calculate return
                return_pct = ((sell_price - buy_price) / buy_price) * 100
                profit_loss = position_size * (return_pct / 100)
                
                all_trades.append({
                    'ticker': ticker,
                    'insider_date': insider_date_str,
                    'insider_value': stock_trade['value'],
                    'entry_date': buy_date.strftime('%Y-%m-%d'),
                    'entry_price': round(buy_price, 2),
                    'exit_date': sell_date.strftime('%Y-%m-%d'),
                    'exit_price': round(sell_price, 2),
                    'exit_reason': 'rise_event_end',
                    'days_held': (sell_date - buy_date).days,
                    'return_pct': round(return_pct, 2),
                    'position_size': position_size,
                    'profit_loss': round(profit_loss, 2),
                    'rise_event_pct': rise_event['growth_pct'],
                    'rise_event_days': rise_event['days']
                })
                
                previous_rise_pcts.append(rise_event['growth_pct'])
                
                # Check if this was an explosion (top quartile of rises or >40%)
                if rise_event['growth_pct'] >= 40:
                    explosion_found = True
                    break  # Done with this ticker
                
            elif insider_date.date() < event_start.date() and not explosion_found:
                # Insider trade happened before this rise event
                # Check if we should enter this rise
                
                # Skip weak rises (less than 50% of best previous rise)
                if is_weak_rise(rise_event['growth_pct'], previous_rise_pcts, min_ratio=0.5):
                    # Weak rise - skip it or exit immediately if we entered
                    continue
                
                # Enter at start of rise event
                buy_date = event_start
                buy_price = rise_event['start_price']
                
                # Determine position size
                c_level_titles = ['CEO', 'CFO', 'COO', 'CTO', 'President', 'Chief', 'Vice Chair']
                insider_info = f"{stock_trade['insider_name']} {stock_trade.get('title', '')}"
                is_c_level = any(title in insider_info for title in c_level_titles)
                position_size = 4000 if is_c_level else 2000
                
                # Exit when rise event ends
                sell_date = event_end
                sell_price = rise_event['end_price']
                
                # Calculate return
                return_pct = ((sell_price - buy_price) / buy_price) * 100
                profit_loss = position_size * (return_pct / 100)
                
                all_trades.append({
                    'ticker': ticker,
                    'insider_date': insider_date_str,
                    'insider_value': stock_trade['value'],
                    'entry_date': buy_date.strftime('%Y-%m-%d'),
                    'entry_price': round(buy_price, 2),
                    'exit_date': sell_date.strftime('%Y-%m-%d'),
                    'exit_price': round(sell_price, 2),
                    'exit_reason': 'rise_event_end',
                    'days_held': (sell_date - buy_date).days,
                    'return_pct': round(return_pct, 2),
                    'position_size': position_size,
                    'profit_loss': round(profit_loss, 2),
                    'rise_event_pct': rise_event['growth_pct'],
                    'rise_event_days': rise_event['days']
                })
                
                previous_rise_pcts.append(rise_event['growth_pct'])
                
                # Check if this was an explosion
                if rise_event['growth_pct'] >= 40:
                    explosion_found = True
                    break  # Done with this ticker
        
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1}/{len(qualifying_stocks)} stocks...")
    
    print(f"\nDebug counters:")
    for key, count in debug_counters.items():
        print(f"  {key}: {count}")
    
    # Create results DataFrame
    if not all_trades:
        print("No trades generated!")
        return
    
    results_df = pd.DataFrame(all_trades)
    
    # Sort by return percentage
    results_df = results_df.sort_values('return_pct', ascending=False)
    
    # Save to CSV
    output_file = 'output CSVs/backtest_rise_event_results.csv'
    results_df.to_csv(output_file, index=False)
    
    # Calculate statistics
    total_trades = len(results_df)
    winning_trades = len(results_df[results_df['return_pct'] > 0])
    losing_trades = len(results_df[results_df['return_pct'] <= 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    total_profit = results_df['profit_loss'].sum()
    total_invested = results_df['position_size'].sum()
    roi = (total_profit / total_invested * 100) if total_invested > 0 else 0
    
    avg_return = results_df['return_pct'].mean()
    median_return = results_df['return_pct'].median()
    avg_days_held = results_df['days_held'].mean()
    
    print("\n" + "="*80)
    print("RISE EVENT STRATEGY BACKTEST RESULTS")
    print("="*80)
    print(f"\nTotal Trades: {total_trades}")
    print(f"Winning Trades: {winning_trades} ({win_rate:.1f}%)")
    print(f"Losing Trades: {losing_trades}")
    print(f"\nTotal Profit/Loss: ${total_profit:,.2f}")
    print(f"Total Invested: ${total_invested:,.2f}")
    print(f"ROI: {roi:.2f}%")
    print(f"\nAverage Return: {avg_return:.2f}%")
    print(f"Median Return: {median_return:.2f}%")
    print(f"Average Days Held: {avg_days_held:.1f}")
    
    print(f"\nTop 10 Best Trades:")
    for idx, row in results_df.head(10).iterrows():
        print(f"{row['ticker']}: {row['return_pct']:.1f}% (${row['profit_loss']:.0f}) | "
              f"Rise event: {row['rise_event_pct']:.1f}% in {row['rise_event_days']} days")
    
    print(f"\nTop 10 Worst Trades:")
    for idx, row in results_df.tail(10).iterrows():
        print(f"{row['ticker']}: {row['return_pct']:.1f}% (${row['profit_loss']:.0f}) | "
              f"Rise event: {row['rise_event_pct']:.1f}% in {row['rise_event_days']} days")
    
    print(f"\nResults saved to: {output_file}")
    print("="*80)

if __name__ == "__main__":
    backtest_rise_event_strategy()
