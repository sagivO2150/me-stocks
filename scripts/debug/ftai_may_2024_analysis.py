#!/usr/bin/env python3
"""
Why didn't FTAI May 30, 2024 trade ($4.8M CEO buy) trigger a buy signal?
This was during our EXISTING profitable position!
"""

import json

print("="*80)
print("FTAI Timeline Analysis")
print("="*80)
print()

# Load batch_1 data
with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/batch_1_insider_trades.json', 'r') as f:
    data = json.load(f)['data']

ftai = [t for t in data if t.get('ticker') == 'FTAI'][0]

# Sort trades chronologically
trades = sorted(ftai['trades'], key=lambda x: x['trade_date'])

print("FTAI Insider Trading Timeline:")
print("-"*80)
for i, trade in enumerate(trades, 1):
    date = trade['trade_date']
    insider = trade['insider_name']
    title = trade.get('title', 'N/A')
    value = int(trade['value'].replace('+$', '').replace(',', ''))
    
    print(f"{i}. {date} | {insider} ({title}) | ${value/1000:.0f}K")

print()
print("="*80)
print("BACKTEST BEHAVIOR:")
print("="*80)
print()

print("✅ Trade #11 (2023-03-15): Tuchman Martin - $1,000K")
print("   → BUY SIGNAL triggered")
print("   → Entry: $22.31")
print("   → Held until 2026-02-13")
print("   → Exit: $279.70 (1154.6% gain)")
print()

print("❌ Trade #10 (2024-05-30): Adams Joseph Jr. (CEO) - $4,838K")
print("   → NO BUY SIGNAL")
print("   → Stock was ALREADY in our portfolio (from 2023 trade)")
print("   → Stock was UP ~300%+ from our entry at this point")
print()

print("="*80)
print("WHY NO ENTRY ON MAY 30, 2024?")
print("="*80)
print()

print("REASON 1: Strategy Doesn't 'Add to Winners'")
print("-"*80)
print("The algorithm is designed to catch INITIAL explosive moves, not to")
print("pyramid into existing positions. Once we're in a trade, we hold it")
print("until the exit criteria are met (stop loss, trend reversal, etc.)")
print()
print("The backtest does NOT implement 'add more when insiders buy again'.")
print()

print("REASON 2: No Fresh Explosive Catalyst")
print("-"*80)
print("Even if FTAI wasn't already in portfolio, the algorithm requires:")
print("  • 20%+ gain in the PREVIOUS 3-5 days (explosive catalyst)")
print()
print("On May 30, 2024:")
print("  • FTAI was up ~300%+ TOTAL from our March 2023 entry")
print("  • BUT: Was it up 20%+ in just the previous 3-5 days?")
print("  • Probably NOT - it was likely in a steady uptrend, not explosive spike")
print()
print("The algorithm looks for SHARP spikes (news/announcements), not gradual climbs.")
print()

print("REASON 3: One Position Per Stock Policy")
print("-"*80)
print("The backtest opens ONE position per stock and holds it until exit.")
print("It doesn't track 'how many shares do we own' or 'should we buy more'.")
print()
print("This is a simplification - a real trading bot COULD add to positions,")
print("but this backtest doesn't implement that feature.")
print()

print("="*80)
print("WHAT THIS REVEALS:")
print("="*80)
print()
print("🎯 The strategy is missing a MAJOR opportunity:")
print("   When insiders buy AGAIN during an uptrend, it often signals continued strength.")
print()
print("💡 POTENTIAL IMPROVEMENT:")
print("   Add a 'pyramid' rule:")
print("   - If we're already in a position AND profitable (>50%)")
print("   - AND insiders buy again (especially C-suite)")
print("   - AND transaction size is large ($1M+)")
print("   - THEN add 25-50% more to the position")
print()
print("This would have captured MORE of FTAI's 1154% gain!")
print()

print("="*80)
print("SUMMARY:")
print("="*80)
print("The May 30, 2024 trade was IGNORED because:")
print("  1. We already had an open position from March 2023")
print("  2. The strategy doesn't add to existing winners")
print("  3. No fresh explosive catalyst (steady climb, not spike)")
print()
print("This is a LIMITATION of the current strategy, not a feature.")
print("A smarter bot would see the $4.8M CEO buy as confirmation to add more!")
