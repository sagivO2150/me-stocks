#!/usr/bin/env python3
"""
Debug THM trade from Feb 2025 - trace Oct 2025 spike and dips
"""

import yfinance as yf
import pandas as pd

# Fetch THM data
thm = yf.Ticker('THM')
history = thm.history(start='2025-02-01', end='2025-12-01')

# Entry was Feb 28, 2025 at $0.47
entry_date = pd.Timestamp('2025-02-28')
entry_price = 0.47

print("\n" + "="*80)
print("THM PRICE ACTION - Oct 2025 (Around the spike)")
print("="*80)
print(f"Entry: {entry_date.date()} at ${entry_price:.2f}\n")

# Focus on Sept-Nov 2025
oct_data = history.loc['2025-09-01':'2025-11-30']

print("\nDaily prices (Sept-Nov 2025):")
print("-" * 80)

peak_price = 0
peak_date = None

for date, row in oct_data.iterrows():
    close = row['Close']
    high = row['High']
    
    gain_from_entry = ((close - entry_price) / entry_price) * 100
    
    if high > peak_price:
        peak_price = high
        peak_date = date
    
    # Check for explosive moves (5-day window)
    data_up_to_date = oct_data.loc[:date]
    if len(data_up_to_date) >= 6:
        five_days_ago = data_up_to_date.iloc[-6]['Close']
        five_day_gain = ((high - five_days_ago) / five_days_ago) * 100
        explosive_marker = " 🚀 EXPLOSIVE!" if five_day_gain > 20 else ""
    else:
        explosive_marker = ""
        five_day_gain = 0
    
    # Mark significant dates
    marker = ""
    if date.date() == pd.Timestamp('2025-10-14').date():
        marker = " ⭐ SPIKE DAY"
    elif date.date() == pd.Timestamp('2025-10-17').date():
        marker = " 🔻 FIRST DIP?"
    elif date.date() == pd.Timestamp('2025-10-20').date():
        marker = " ↗️ RECOVERY?"
    elif date.date() == pd.Timestamp('2025-10-21').date():
        marker = " 🚨 SECOND DIP?"
    
    print(f"{date.date()} | Close: ${close:.2f} | High: ${high:.2f} | "
          f"From entry: {gain_from_entry:+6.1f}% | 5-day: {five_day_gain:+5.1f}%{explosive_marker}{marker}")

print(f"\n📊 Peak: ${peak_price:.2f} on {peak_date.date()}")
print(f"   Peak gain from entry: {((peak_price - entry_price) / entry_price) * 100:.1f}%")

# Now analyze the dips around Oct 17 and Oct 21
print("\n" + "="*80)
print("DIP ANALYSIS - Testing slope-based detection")
print("="*80)

# Get Oct 14-24 window
dip_window = history.loc['2025-10-14':'2025-10-24']
prices = [(date, row['Close']) for date, row in dip_window.iterrows()]

print("\nPrice sequence:")
for i, (date, price) in enumerate(prices):
    print(f"{i}: {date.date()} - ${price:.2f}")

# Calculate slopes for suspected dips
print("\n🔍 Slope calculations:")

# First dip: Oct 14-17 (or 15-17)
if len(prices) >= 4:
    oct14_price = prices[0][1]  # Oct 14
    oct17_idx = 3  # Oct 17 is 3 days later
    oct17_price = prices[oct17_idx][1]
    
    # Slope over full 3 days
    slope_14_17 = (oct17_price - oct14_price) / 3
    print(f"\nFirst dip (Oct 14→17, 3 days):")
    print(f"  ${oct14_price:.2f} → ${oct17_price:.2f}")
    print(f"  Slope: ${slope_14_17:.2f}/day (${abs(slope_14_17):.2f}/day absolute)")
    print(f"  Would trigger first dip? {abs(slope_14_17) > 0.50}")
    
    # But the strategy uses 2-day lookback!
    if oct17_idx >= 2:
        two_days_before_17 = prices[oct17_idx - 2][1]  # Oct 15
        slope_15_17 = (oct17_price - two_days_before_17) / 2
        print(f"\nFirst dip (2-day lookback: Oct 15→17):")
        print(f"  ${two_days_before_17:.2f} → ${oct17_price:.2f}")
        print(f"  Slope: ${slope_15_17:.2f}/day (${abs(slope_15_17):.2f}/day absolute)")
        print(f"  Would trigger first dip? {abs(slope_15_17) > 0.50}")

# Second dip: Oct 20-21
oct20_idx = next(i for i, (d, _) in enumerate(prices) if d.date() == pd.Timestamp('2025-10-20').date())
oct21_idx = next(i for i, (d, _) in enumerate(prices) if d.date() == pd.Timestamp('2025-10-21').date())

oct20_price = prices[oct20_idx][1]
oct21_price = prices[oct21_idx][1]

slope_20_21 = (oct21_price - oct20_price) / 1
print(f"\nSecond dip (Oct 20→21, 1 day):")
print(f"  ${oct20_price:.2f} → ${oct21_price:.2f}")
print(f"  Slope: ${slope_20_21:.2f}/day (${abs(slope_20_21):.2f}/day absolute)")
print(f"  Would trigger second dip? {abs(slope_20_21) > 0.30}")

# Check if 2-day lookback would work
if oct21_idx >= 2:
    two_days_before_21 = prices[oct21_idx - 2][1]
    slope_19_21 = (oct21_price - two_days_before_21) / 2
    print(f"\nSecond dip (2-day lookback: Oct 19→21):")
    print(f"  ${two_days_before_21:.2f} → ${oct21_price:.2f}")
    print(f"  Slope: ${slope_19_21:.2f}/day (${abs(slope_19_21):.2f}/day absolute)")
    print(f"  Would trigger second dip? {abs(slope_19_21) > 0.30}")

print("\n" + "="*80)
