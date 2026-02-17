import yfinance as yf
import json
from datetime import datetime, timedelta

# Fetch stock history for BSAI
ticker = yf.Ticker('BSAI')
hist = ticker.history(period='max')

print("=== BSAI Stock History Sample ===")
print(f"Total days: {len(hist)}")
print(f"\nFirst 5 days:")
for idx, (date, row) in enumerate(list(hist.iterrows())[:5]):
    print(f"  {date.strftime('%Y-%m-%d')}: ${row['Close']:.2f}")

print(f"\nLast 5 days:")
for idx, (date, row) in enumerate(list(hist.iterrows())[-5:]):
    print(f"  {date.strftime('%Y-%m-%d')}: ${row['Close']:.2f}")

# Check insider trade dates
insider_dates = ["2024-04-15", "2025-04-21", "2025-05-15"]

print("\n=== Checking Insider Trade Dates ===")
for trade_date in insider_dates:
    # Convert to datetime with timezone awareness
    import pandas as pd
    dt = pd.Timestamp(trade_date).tz_localize('America/New_York')
    
    # Check if date exists in history
    if dt in hist.index:
        price = hist.loc[dt, 'Close']
        print(f"✓ {trade_date}: Found! Price = ${price:.2f}")
    else:
        print(f"✗ {trade_date}: NOT FOUND in stock history")
        
        # Find nearest date
        hist_dates = hist.index.tolist()
        nearest_before = None
        nearest_after = None
        
        for hdate in hist_dates:
            if hdate < dt:
                nearest_before = hdate
            elif hdate > dt and nearest_after is None:
                nearest_after = hdate
                break
        
        if nearest_before:
            print(f"    Nearest before: {nearest_before.strftime('%Y-%m-%d')} (${hist.loc[nearest_before, 'Close']:.2f})")
        if nearest_after:
            print(f"    Nearest after: {nearest_after.strftime('%Y-%m-%d')} (${hist.loc[nearest_after, 'Close']:.2f})")

# Check what dates exist around 2025-04-21
print("\n=== Dates around 2025-04-21 ===")
import pandas as pd
target = pd.Timestamp('2025-04-21').tz_localize('America/New_York')
week_before = target - timedelta(days=7)
week_after = target + timedelta(days=7)

dates_in_range = [d for d in hist.index if week_before <= d <= week_after]
if dates_in_range:
    for date in dates_in_range:
        print(f"  {date.strftime('%Y-%m-%d (%A)')}: ${hist.loc[date, 'Close']:.2f}")
else:
    print("  No dates found in this range!")
