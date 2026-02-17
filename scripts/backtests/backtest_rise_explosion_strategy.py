#!/usr/bin/env python3
"""
Rise Explosion Strategy

Rules:
1. 3-month IPO wait + $20K minimum insider purchase
2. Don't buy during DOWN events
3. Buy during RISE when insider buys, sell when RISE ends
4. Keep buying/selling each RISE until we get EXPLOSION
5. Explosion = top 25% of rises for that stock
6. Track each insider purchase separately
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List

def load_data():
    """Load insider trades and yfinance cache."""
    with open('output CSVs/expanded_insider_trades.json', 'r') as f:
        insider_data = json.load(f).get('data', [])
    
    with open('output CSVs/yfinance_cache_full.json', 'r') as f:
        yfinance_cache = json.load(f)
    
    return insider_data, yfinance_cache

def identify_rise_fall_events(df: pd.DataFrame, min_days: int = 4, min_growth_pct: float = 2.0, 
                               min_decline_pct: float = 1.5, min_recovery_pct: float = 2.0) -> List[Dict]:
    """Identify rise and fall events. Returns list with 'type', 'start_date', 'end_date', 'pct'."""
    events = []
    
    if len(df) < 3:
        return events
    
    in_rise = False
    start_idx = None
    start_price = None
    peak_idx = None
    peak_price = None
    consecutive_dips = 0
    
    hunting_bottom = True
    bottom_idx = 0
    bottom_price = df['Close'].iloc[0]
    
    for i in range(len(df)):
        current_price = df['Close'].iloc[i]
        
        if hunting_bottom:
            if current_price <= bottom_price:
                bottom_idx = i
                bottom_price = current_price
            
            if i > 0 and current_price > df['Close'].iloc[i - 1]:
                in_rise = True
                hunting_bottom = False
                start_idx = bottom_idx
                start_price = bottom_price
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
            
            if consecutive_dips >= 2 and peak_idx > start_idx:
                growth_pct = ((peak_price - start_price) / start_price) * 100
                days_duration = peak_idx - start_idx + 1
                
                if days_duration >= min_days and growth_pct >= min_growth_pct:
                    events.append({
                        'type': 'RISE',
                        'start_date': df.index[start_idx],
                        'end_date': df.index[peak_idx],
                        'start_price': start_price,
                        'end_price': peak_price,
                        'pct': round(growth_pct, 2),
                        'days': days_duration
                    })
                
                in_rise = False
                hunting_bottom = True
                bottom_idx = i
                bottom_price = current_price
                consecutive_dips = 0
    
    # Handle last rise
    if in_rise and peak_idx is not None and peak_idx > start_idx:
        growth_pct = ((peak_price - start_price) / start_price) * 100
        days_duration = peak_idx - start_idx + 1
        
        if days_duration >= min_days and growth_pct >= min_growth_pct:
            events.append({
                'type': 'RISE',
                'start_date': df.index[start_idx],
                'end_date': df.index[peak_idx],
                'start_price': start_price,
                'end_price': peak_price,
                'pct': round(growth_pct, 2),
                'days': days_duration
            })
    
    return events

def is_explosion(rise_pct: float, all_rises_so_far: List[float]) -> bool:
    """Check if this rise is an explosion (top 25% of all rises so far)."""
    if not all_rises_so_far:
        return False
    
    # Need at least 2 rises to determine if something is top tier
    if len(all_rises_so_far) < 2:
        return False
    
    # Top 25% threshold
    sorted_rises = sorted(all_rises_so_far, reverse=True)
    top_25_idx = max(1, len(sorted_rises) // 4)
    threshold = sorted_rises[top_25_idx - 1]
    
    return rise_pct >= threshold

def backtest():
    """Run the rise explosion strategy."""
    print("Loading data...")
    insider_data, yfinance_cache = load_data()
    
    # Parse all insider purchases
    all_insider_purchases = []
    for stock in insider_data:
        ticker = stock.get('ticker')
        for trade in stock.get('trades', []):
            shares_str = trade.get('shares', '')
            value_str = trade.get('value', '')
            
            if isinstance(shares_str, str) and '+' in shares_str:
                try:
                    value = float(value_str.replace('+$', '').replace('$', '').replace(',', ''))
                    if value >= 20000:
                        all_insider_purchases.append({
                            'ticker': ticker,
                            'date': datetime.strptime(trade.get('trade_date'), '%Y-%m-%d'),
                            'value': value,
                            'insider': trade.get('insider_name', 'Unknown'),
                            'title': trade.get('title', '')
                        })
                except:
                    continue
    
    print(f"Found {len(all_insider_purchases)} insider purchases >= $20K")
    
    all_trades = []
    
    # Group by ticker
    tickers_with_purchases = {}
    for purchase in all_insider_purchases:
        ticker = purchase['ticker']
        if ticker not in tickers_with_purchases:
            tickers_with_purchases[ticker] = []
        tickers_with_purchases[ticker].append(purchase)
    
    print(f"Processing {len(tickers_with_purchases)} unique tickers...")
    
    for ticker_idx, (ticker, purchases) in enumerate(tickers_with_purchases.items()):
        if ticker not in yfinance_cache:
            continue
        
        # Get price data
        price_data = yfinance_cache[ticker]
        df = pd.DataFrame(price_data)
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)
        
        if df.empty or len(df) < 10:
            continue
        
        # Check 3-month IPO wait
        ipo_date = df.index[0]
        ipo_plus_3_months = ipo_date + timedelta(days=90)
        
        # Identify all rise events
        rise_events = identify_rise_fall_events(df)
        if not rise_events:
            continue
        
        # Track all rise percentages for explosion detection
        all_rise_pcts = [event['pct'] for event in rise_events]
        
        # Process each insider purchase
        for purchase in purchases:
            insider_date = purchase['date']
            
            # Skip if before IPO wait period
            if insider_date < ipo_plus_3_months:
                continue
            
            # Find which events this insider purchase affects
            explosion_found = False
            rises_seen_so_far = []
            
            for event in rise_events:
                event_start = event['start_date']
                event_end = event['end_date']
                
                # Only consider events on or after insider purchase
                if event_end.date() < insider_date.date():
                    # This rise happened before insider purchase, add to history
                    rises_seen_so_far.append(event['pct'])
                    continue
                
                if explosion_found:
                    # Already got explosion for this insider, skip rest
                    break
                
                # Insider bought during this rise OR we're in subsequent rises waiting for explosion
                if event_start.date() <= insider_date.date() <= event_end.date():
                    # Insider bought DURING this rise - enter immediately
                    # Use price on or after insider date
                    buy_dates = df[(df.index >= insider_date) & (df.index <= event_end)]
                    if buy_dates.empty:
                        rises_seen_so_far.append(event['pct'])
                        continue
                    
                    buy_date = buy_dates.index[0]
                    buy_price = buy_dates.iloc[0]['Close']
                    
                elif insider_date.date() < event_start.date():
                    # Insider bought before this rise - enter at start of rise
                    buy_date = event_start
                    buy_price = event['start_price']
                else:
                    rises_seen_so_far.append(event['pct'])
                    continue
                
                # Exit at end of rise
                sell_date = event_end
                sell_price = event['end_price']
                
                # Position size
                c_level_titles = ['CEO', 'CFO', 'COO', 'CTO', 'President', 'Chief', 'Vice Chair']
                insider_info = f"{purchase['insider']} {purchase['title']}"
                is_c_level = any(title in insider_info for title in c_level_titles)
                position_size = 4000 if is_c_level else 2000
                
                # Calculate return
                return_pct = ((sell_price - buy_price) / buy_price) * 100
                profit_loss = position_size * (return_pct / 100)
                
                all_trades.append({
                    'ticker': ticker,
                    'insider_date': insider_date.strftime('%Y-%m-%d'),
                    'insider_value': purchase['value'],
                    'insider_name': purchase['insider'],
                    'entry_date': buy_date.strftime('%Y-%m-%d'),
                    'entry_price': round(buy_price, 2),
                    'exit_date': sell_date.strftime('%Y-%m-%d'),
                    'exit_price': round(sell_price, 2),
                    'days_held': (sell_date - buy_date).days,
                    'return_pct': round(return_pct, 2),
                    'position_size': position_size,
                    'profit_loss': round(profit_loss, 2),
                    'rise_pct': event['pct'],
                    'is_explosion': False
                })
                
                # Check if this was an explosion
                if is_explosion(event['pct'], rises_seen_so_far):
                    all_trades[-1]['is_explosion'] = True
                    explosion_found = True
                
                rises_seen_so_far.append(event['pct'])
        
        if (ticker_idx + 1) % 100 == 0:
            print(f"Processed {ticker_idx + 1}/{len(tickers_with_purchases)} tickers...")
    
    if not all_trades:
        print("No trades generated!")
        return
    
    # Create results
    results_df = pd.DataFrame(all_trades)
    results_df = results_df.sort_values('return_pct', ascending=False)
    
    # Save
    output_file = 'output CSVs/backtest_rise_explosion_results.csv'
    results_df.to_csv(output_file, index=False)
    
    # Statistics
    total_trades = len(results_df)
    winning_trades = len(results_df[results_df['return_pct'] > 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    total_profit = results_df['profit_loss'].sum()
    total_invested = results_df['position_size'].sum()
    roi = (total_profit / total_invested * 100) if total_invested > 0 else 0
    
    avg_return = results_df['return_pct'].mean()
    median_return = results_df['return_pct'].median()
    avg_days = results_df['days_held'].mean()
    
    explosions = results_df[results_df['is_explosion'] == True]
    
    print("\n" + "="*80)
    print("RISE EXPLOSION STRATEGY RESULTS")
    print("="*80)
    print(f"\nTotal Trades: {total_trades}")
    print(f"Explosions Caught: {len(explosions)}")
    print(f"Winning Trades: {winning_trades} ({win_rate:.1f}%)")
    print(f"\nTotal Profit: ${total_profit:,.2f}")
    print(f"Total Invested: ${total_invested:,.2f}")
    print(f"ROI: {roi:.2f}%")
    print(f"\nAverage Return: {avg_return:.2f}%")
    print(f"Median Return: {median_return:.2f}%")
    print(f"Average Days Held: {avg_days:.1f}")
    
    print(f"\nTop 10 Trades:")
    for idx, row in results_df.head(10).iterrows():
        exp_mark = " 💥 EXPLOSION" if row['is_explosion'] else ""
        print(f"{row['ticker']}: {row['return_pct']:.1f}% | Rise: {row['rise_pct']:.1f}%{exp_mark}")
    
    print(f"\nResults saved to: {output_file}")
    print("="*80)

if __name__ == "__main__":
    backtest()
