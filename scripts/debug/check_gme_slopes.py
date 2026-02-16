#!/usr/bin/env python3
import yfinance as yf
import pandas as pd

gme = yf.Ticker('GME')
df = gme.history(start='2024-07-01', end='2024-08-15')

# Key dates
dates = [
    ('2024-07-17', '2024-07-18', 'Dip #1 start'),
    ('2024-07-18', '2024-07-19', 'Dip #1 continues'),
    ('2024-07-23', '2024-07-24', 'Dip #2 (should be detected)'),
]

print('\nGME Slope Analysis')
print('='*80)
for start_date, end_date, label in dates:
    start_ts = pd.Timestamp(start_date, tz='America/New_York')
    end_ts = pd.Timestamp(end_date, tz='America/New_York')
    
    if start_ts in df.index and end_ts in df.index:
        start_price = df.loc[start_ts, 'Close']
        end_price = df.loc[end_ts, 'Close']
        drop = end_price - start_price
        slope = abs(drop)  # Per day (1 day)
        pct = (drop / start_price) * 100
        
        print(f'{label}:')
        print(f'  {start_date}: ${start_price:.2f}')
        print(f'  {end_date}: ${end_price:.2f}')
        print(f'  Drop: ${drop:.2f} ({pct:.1f}%)')
        print(f'  Slope: ${slope:.2f}/day')
        print()

# Now check 2-day slopes
print('\n2-Day Slope Comparison:')
print('='*80)
dip1_start = pd.Timestamp('2024-07-17', tz='America/New_York')
dip1_end = pd.Timestamp('2024-07-19', tz='America/New_York')
dip1_slope = abs(df.loc[dip1_end, 'Close'] - df.loc[dip1_start, 'Close']) / 2

print(f'Dip #1 (July 17-19, 2 days): ${dip1_slope:.2f}/day')
print(f'First dip slope stored: ${dip1_slope:.2f}/day')
print()

dip2_start = pd.Timestamp('2024-07-23', tz='America/New_York')
dip2_end = pd.Timestamp('2024-07-24', tz='America/New_York')
dip2_slope = abs(df.loc[dip2_end, 'Close'] - df.loc[dip2_start, 'Close'])

print(f'Dip #2 (July 23-24, 1 day): ${dip2_slope:.2f}/day')
print(f'Ratio: {dip2_slope / dip1_slope:.1%} of first dip')
print()

if dip2_slope / dip1_slope >= 0.5:
    print('✅ Should trigger as 2nd violent dip (>50% of first dip slope)')
else:
    print('❌ Would NOT trigger (<50% of first dip slope)')
