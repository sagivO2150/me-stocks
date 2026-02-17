#!/usr/bin/env python3
"""Test the rise explosion strategy on GROV only."""

import pandas as pd
from datetime import datetime
from scripts.analysis.analyze_grov_rise_events import identify_rise_events, load_grov_insider_trades
import json

# Load GROV price data
with open('output CSVs/yfinance_cache_full.json', 'r') as f:
    cache = json.load(f)

price_data = cache['GROV']
df = pd.DataFrame(price_data)
df['Date'] = pd.to_datetime(df['Date'])
df.set_index('Date', inplace=True)
df.sort_index(inplace=True)

print(f"GROV data: {len(df)} days from {df.index[0].date()} to {df.index[-1].date()}")

# Get insider trades
insider_trades = load_grov_insider_trades()
print(f"\nFound {len(insider_trades)} insider trades")

# Get rise events
rise_events = identify_rise_events(df)
print(f"Found {len(rise_events)} rise events\n")

# Focus on June 2022 insider buy
target_date = datetime(2022, 6, 16)
print(f"=== Analyzing insider buy on {target_date.date()} ===\n")

# Find which rise event it's in
for i, event in enumerate(rise_events, 1):
    if event['start_date'] <= target_date <= event['end_date']:
        print(f"Insider bought DURING rise event #{i}:")
        print(f"  Rise: {event['start_date'].date()} → {event['end_date'].date()}")
        print(f"  Growth: +{event['growth_pct']}% in {event['days']} days")
        print(f"  Start price: ${event['start_price']:.2f}")
        print(f"  End price: ${event['end_price']:.2f}")
        print(f"\n  → BUY on {target_date.date()} at ~${df.loc[target_date]['Close']:.2f}")
        print(f"  → SELL on {event['end_date'].date()} at ${event['end_price']:.2f}")
        
        buy_price = df.loc[target_date]['Close']
        sell_price = event['end_price']
        return_pct = ((sell_price - buy_price) / buy_price) * 100
        print(f"  → Return: {return_pct:.2f}%")
        
        print(f"\n  Continue buying/selling on future rises until explosion...\n")
        
        # Show next few rises
        rises_after = [e for e in rise_events if e['start_date'] > event['end_date']]
        all_rise_pcts_so_far = [event['growth_pct']]
        
        for j, next_rise in enumerate(rises_after[:5], 2):
            print(f"Rise event #{i+j-1}:")
            print(f"  {next_rise['start_date'].date()} → {next_rise['end_date'].date()}")
            print(f"  Growth: +{next_rise['growth_pct']}% in {next_rise['days']} days")
            
            # Check if explosion
            sorted_rises = sorted(all_rise_pcts_so_far, reverse=True)
            top_25_idx = max(1, len(sorted_rises) // 4)
            threshold = sorted_rises[top_25_idx - 1] if len(sorted_rises) >= 2 else 999
            
            is_explosion = next_rise['growth_pct'] >= threshold and len(all_rise_pcts_so_far) >= 2
            
            if is_explosion:
                print(f"  💥 EXPLOSION! (threshold was {threshold:.1f}%)")
                print(f"  → SELL and DONE tracking this insider\n")
                break
            else:
                print(f"  → Buy and sell (threshold: {threshold:.1f}%)\n")
            
            all_rise_pcts_so_far.append(next_rise['growth_pct'])
        
        break
