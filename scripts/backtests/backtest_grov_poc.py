#!/usr/bin/env python3
"""
Run rise explosion strategy on GROV only for POC testing.
Outputs JSON for webapp display.
"""

import json
import pandas as pd
from datetime import datetime, timedelta

def identify_rise_events(df, min_days=4, min_growth_pct=2.0, min_decline_pct=1.5, min_recovery_pct=2.0):
    """Identify rise events."""
    rise_events = []
    
    if len(df) < 3:
        return rise_events
    
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
                    rise_events.append({
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
    
    if in_rise and peak_idx is not None and peak_idx > start_idx:
        growth_pct = ((peak_price - start_price) / start_price) * 100
        days_duration = peak_idx - start_idx + 1
        
        if days_duration >= min_days and growth_pct >= min_growth_pct:
            rise_events.append({
                'start_date': df.index[start_idx],
                'end_date': df.index[peak_idx],
                'start_price': start_price,
                'end_price': peak_price,
                'pct': round(growth_pct, 2),
                'days': days_duration
            })
    
    return rise_events

# Load GROV data from cache
print("Loading GROV data...")
with open('output CSVs/yfinance_cache_full.json', 'r') as f:
    cache = json.load(f)

# Find GROV in cache
grov_data = None
for ticker, data in cache['data'].items():
    if ticker == 'GROV':
        grov_data = data
        break

if not grov_data:
    print("GROV not found in cache!")
    exit(1)

# Build DataFrame
df = pd.DataFrame({
    'Open': grov_data['open'],
    'High': grov_data['high'],
    'Low': grov_data['low'],
    'Close': grov_data['close'],
    'Volume': grov_data['volume']
}, index=pd.to_datetime(grov_data['dates']))

print(f"GROV data: {len(df)} days from {df.index[0].date()} to {df.index[-1].date()}")

# Get rise events
rise_events = identify_rise_events(df)
print(f"Found {len(rise_events)} rise events")

# Insider trades for GROV (hardcoded key ones)
insider_trades = [
    {'date': datetime(2022, 6, 16), 'value': 66715240, 'insider': 'Virgin Group', 'title': '10% Owner'},
    {'date': datetime(2022, 11, 22), 'value': 103288, 'insider': 'Replogle John B', 'title': 'CEO'},
    {'date': datetime(2022, 12, 5), 'value': 58740, 'insider': 'Cleary Kevin Michael', 'title': 'CFO'},
]

# Run strategy
all_trades = []

for purchase in insider_trades:
    insider_date = purchase['date']
    rises_seen = []
    explosion_found = False
    
    for event in rise_events:
        event_start = event['start_date']
        event_end = event['end_date']
        
        # Skip events before insider purchase
        if event_end.date() < insider_date.date():
            rises_seen.append(event['pct'])
            continue
        
        if explosion_found:
            break
        
        # Determine entry
        if event_start.date() <= insider_date.date() <= event_end.date():
            # Bought during this rise
            buy_dates = df[(df.index >= insider_date) & (df.index <= event_end)]
            if buy_dates.empty:
                rises_seen.append(event['pct'])
                continue
            buy_date = buy_dates.index[0]
            buy_price = buy_dates.iloc[0]['Close']
        elif insider_date.date() < event_start.date():
            # Enter at start of rise
            buy_date = event_start
            buy_price = event['start_price']
        else:
            rises_seen.append(event['pct'])
            continue
        
        # Exit at end of rise
        sell_date = event_end
        sell_price = event['end_price']
        
        # Position size
        c_level = any(t in purchase.get('title', '') for t in ['CEO', 'CFO', 'President', 'Chief', 'Owner'])
        position_size = 4000 if c_level else 2000
        
        # Calculate return
        return_pct = ((sell_price - buy_price) / buy_price) * 100
        profit_loss = position_size * (return_pct / 100)
        
        # Check for explosion
        is_explosion = False
        if len(rises_seen) >= 2:
            sorted_rises = sorted(rises_seen, reverse=True)
            threshold = sorted_rises[max(0, len(sorted_rises) // 4)]
            is_explosion = event['pct'] >= threshold
        
        all_trades.append({
            'ticker': 'GROV',
            'insider_date': insider_date.strftime('%Y-%m-%d'),
            'insider_value': int(purchase['value']),
            'insider_name': purchase['insider'],
            'entry_date': buy_date.strftime('%Y-%m-%d'),
            'entry_price': round(buy_price, 2),
            'exit_date': sell_date.strftime('%Y-%m-%d'),
            'exit_price': round(sell_price, 2),
            'days_held': int((sell_date - buy_date).days),
            'return_pct': round(return_pct, 2),
            'position_size': int(position_size),
            'profit_loss': round(profit_loss, 2),
            'rise_pct': event['pct'],
            'is_explosion': 'yes' if is_explosion else 'no'
        })
        
        if is_explosion:
            explosion_found = True
        
        rises_seen.append(event['pct'])

# Save results
output = {
    'ticker': 'GROV',
    'total_trades': len(all_trades),
    'total_profit': sum(t['profit_loss'] for t in all_trades),
    'total_invested': sum(t['position_size'] for t in all_trades),
    'roi': (sum(t['profit_loss'] for t in all_trades) / sum(t['position_size'] for t in all_trades) * 100) if all_trades else 0,
    'trades': all_trades
}

with open('output CSVs/grov_rise_explosion_poc.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n{'='*60}")
print(f"GROV Rise Explosion Strategy - POC Results")
print(f"{'='*60}")
print(f"Total Trades: {output['total_trades']}")
print(f"Total Profit: ${output['total_profit']:,.2f}")
print(f"Total Invested: ${output['total_invested']:,.2f}")
print(f"ROI: {output['roi']:.2f}%")
print(f"\nTrades:")
for trade in all_trades:
    exp = " 💥" if trade['is_explosion'] == 'yes' else ""
    print(f"  {trade['entry_date']} → {trade['exit_date']}: {trade['return_pct']:+.1f}% (${trade['profit_loss']:+.0f}) | Rise: {trade['rise_pct']:.1f}%{exp}")
print(f"\nResults saved to: output CSVs/grov_rise_explosion_poc.json")
print(f"{'='*60}")
