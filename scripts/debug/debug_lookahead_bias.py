#!/usr/bin/env python3
"""
Debug script to show lookahead bias in rise/fall detection.
Shows WHEN we would actually know about a rise/fall event ending.
"""

import json
import pandas as pd
from datetime import datetime

def load_grov_data():
    """Load GROV price data from cache."""
    cache_path = 'output CSVs/yfinance_cache_full.json'
    
    with open(cache_path, 'r') as f:
        cache = json.load(f)
    
    ticker = 'GROV'
    if ticker not in cache['data']:
        raise ValueError(f'{ticker} not found in cache')
    
    ticker_data = cache['data'][ticker]
    
    # Build DataFrame from the new structure
    # ticker_data has keys: 'ticker', 'dates', 'open', 'high', 'low', 'close', 'volume'
    dates = [pd.to_datetime(d) for d in ticker_data['dates']]
    closes = ticker_data['close']
    
    df = pd.DataFrame({'Close': closes}, index=dates)
    df = df.sort_index()
    
    return df

def simulate_realtime_detection():
    """
    Simulate real-time detection of rise/fall events.
    Show when we would ACTUALLY know an event ended.
    """
    df = load_grov_data()
    print(f"GROV data: {len(df)} days from {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}\n")
    
    # Key parameters
    min_decline_pct = 1.5
    consecutive_dips_needed = 2
    
    # Focus on the period around Sept-Oct 2022 downfall
    start_date = '2022-08-15'
    end_date = '2022-10-20'
    
    period_df = df.loc[start_date:end_date]
    
    print("=" * 80)
    print("SIMULATING REAL-TIME DETECTION")
    print("=" * 80)
    print(f"Period: {start_date} to {end_date}")
    print(f"Rule: Rise ends after {consecutive_dips_needed} consecutive declines of {min_decline_pct}%+\n")
    
    # Track state
    peak_idx = None
    peak_price = None
    peak_date = None
    consecutive_dips = 0
    
    for i in range(len(period_df)):
        current_date = period_df.index[i]
        current_price = period_df['Close'].iloc[i]
        
        # Initialize peak at first day
        if peak_idx is None:
            peak_idx = i
            peak_price = current_price
            peak_date = current_date
            print(f"{current_date.strftime('%Y-%m-%d')}: Starting peak at ${current_price:.2f}")
            continue
        
        prev_price = period_df['Close'].iloc[i - 1]
        
        if current_price > peak_price:
            # New peak
            peak_idx = i
            peak_price = current_price
            peak_date = current_date
            consecutive_dips = 0
            print(f"{current_date.strftime('%Y-%m-%d')}: NEW PEAK ${current_price:.2f} (dips reset to 0)")
            
        elif current_price < prev_price:
            # Decline
            decline_pct = ((prev_price - current_price) / prev_price) * 100
            
            if decline_pct >= min_decline_pct:
                consecutive_dips += 1
                drawdown_pct = ((peak_price - current_price) / peak_price) * 100
                print(f"{current_date.strftime('%Y-%m-%d')}: Decline -{decline_pct:.1f}% (${current_price:.2f}) | "
                      f"Dips: {consecutive_dips}/{consecutive_dips_needed} | "
                      f"Drawdown from peak: -{drawdown_pct:.1f}%")
                
                if consecutive_dips >= consecutive_dips_needed:
                    days_since_peak = (current_date - peak_date).days
                    print(f"\n{'=' * 80}")
                    print(f"🚨 RISE EVENT ENDED - DETECTED ON {current_date.strftime('%Y-%m-%d')}")
                    print(f"{'=' * 80}")
                    print(f"Peak was on: {peak_date.strftime('%Y-%m-%d')} at ${peak_price:.2f}")
                    print(f"Detected {days_since_peak} calendar days after peak")
                    print(f"Current price: ${current_price:.2f}")
                    print(f"Loss from peak: -{drawdown_pct:.1f}%")
                    print(f"{'=' * 80}\n")
                    
                    # In real-time, we would SELL HERE, not at the peak
                    # Reset for next rise
                    peak_idx = None
                    peak_price = None
                    peak_date = None
                    consecutive_dips = 0
            else:
                print(f"{current_date.strftime('%Y-%m-%d')}: Small decline -{decline_pct:.1f}% (${current_price:.2f}) | "
                      f"Dips: {consecutive_dips}/{consecutive_dips_needed} (unchanged)")
        else:
            # Unchanged
            print(f"{current_date.strftime('%Y-%m-%d')}: Unchanged ${current_price:.2f} | "
                  f"Dips: {consecutive_dips}/{consecutive_dips_needed}")

if __name__ == '__main__':
    simulate_realtime_detection()
