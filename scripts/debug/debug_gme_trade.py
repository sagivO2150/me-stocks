#!/usr/bin/env python3
"""Debug GME trade from July 9, 2024 - Test new dip detection logic"""

import yfinance as yf
import pandas as pd

# Fetch GME data
gme = yf.Ticker('GME')
df = gme.history(start='2024-07-01', end='2024-08-15')

entry_price = 24.60
entry_date = pd.Timestamp('2024-07-09').tz_localize('America/New_York')

print('\n' + '='*120)
print('GME TRADE ANALYSIS - Testing New Dip Detection Logic')
print('='*120)
print(f"{'Date':<12} {'Close':>8} {'From Peak':>10} {'Recent 3d':>10} {'Dip#':>5} {'Action':<50}")
print('-'*120)

peak = entry_price
peak_date = entry_date
violent_dip_count = 0
in_violent_dip = False
failed_recovery = False
price_history = []

for date, row in df.iterrows():
    if date < entry_date:
        continue
    
    close = row['Close']
    high = row['High']
    price_history.append((date, close))
    
    action = ""
    
    # Track peak
    if high > peak * 1.02:  # New high
        peak = high
        peak_date = date
        violent_dip_count = 0
        in_violent_dip = False
        failed_recovery = False
        action = f"⬆️ NEW PEAK ${peak:.2f}"
    
    # Calculate drawdowns
    drawdown_pct = ((close - peak) / peak) * 100
    
    # Look at recent drop (last 3 days)
    current_idx = len(price_history) - 1
    lookback = min(3, current_idx)
    if lookback > 0:
        lookback_idx = current_idx - lookback
        recent_prices = price_history[lookback_idx:current_idx + 1]
        recent_high = max([p for _, p in recent_prices])
        recent_drop_pct = ((close - recent_high) / recent_high) * 100
    else:
        recent_drop_pct = 0
    
    # Detect violent dip
    if drawdown_pct < -3.0 and not in_violent_dip:
        if recent_drop_pct < -3.0:
            # Check if violent
            is_violent = False
            if not failed_recovery:
                if abs(recent_drop_pct) > 5.0:
                    is_violent = True
                    reason = f">{abs(recent_drop_pct):.1f}% recent drop"
                elif abs(recent_drop_pct) / lookback > 1.5:
                    is_violent = True
                    reason = f">{abs(recent_drop_pct) / lookback:.1f}%/day"
            else:
                is_violent = True
                reason = f"{abs(recent_drop_pct):.1f}% after failed recovery"
            
            if is_violent:
                violent_dip_count += 1
                in_violent_dip = True
                if action:
                    action += " | "
                action += f"🔻 DIP #{violent_dip_count}: {reason}"
    
    # Check recovery
    if in_violent_dip and drawdown_pct > -1.0:
        in_violent_dip = False
        if close < peak * 0.98:
            failed_recovery = True
            if action:
                action += " | "
            action += f"↗️ Recovery but failed (peak ${peak:.2f})"
        else:
            if action:
                action += " | "
            action += f"↗️ Recovery to near peak"
    
    # Exit signal?
    if violent_dip_count >= 2 and in_violent_dip and failed_recovery:
        if action:
            action += " | "
        action += "🚨 EXIT: 2nd dip after failed recovery"
    
    print(f"{date.strftime('%Y-%m-%d'):<12} ${close:7.2f} {drawdown_pct:+9.1f}% {recent_drop_pct:+9.1f}% {violent_dip_count:>5} {action:<50}")
    
    if date >= pd.Timestamp('2024-08-07').tz_localize('America/New_York'):
        break

print('-'*120)
print(f"\nFinal: Dip count = {violent_dip_count}, Failed recovery = {failed_recovery}")
print('='*120)
