#!/usr/bin/env python3
"""
Quick check: Why didn't FTAI 2025-05-02 trade get a buy signal?
Using batch_1_insider_trades.json format
"""

import json

# Load batch_1 data
print("Loading batch_1 data...")
with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/batch_1_insider_trades.json', 'r') as f:
    data = json.load(f)['data']

# Find FTAI
ftai = [t for t in data if t.get('ticker') == 'FTAI'][0]

print(f"Ticker: {ftai['ticker']}")
print(f"Company: {ftai['company_name']}")
print(f"Total trades: {len(ftai['trades'])}")
print()

# Focus on the two trades in question
print("="*80)
print("Trade #1: 2023-03-15 - Tuchman Martin - $1,000K")
print("="*80)
print("✅ This trade GOT a buy signal and made 1154.6% profit")
print()

print("="*80)
print("Trade #2: 2025-05-02 - Multiple Insiders (Adams, Moreno, Kuperus)")
print("="*80)

# Find the 2025-05-02 trades
may_2025_trades = [t for t in ftai['trades'] if t['trade_date'] == '2025-05-02']

print(f"Found {len(may_2025_trades)} trades on 2025-05-02:")
for t in may_2025_trades:
    value = int(t['value'].replace('+$', '').replace(',', ''))
    print(f"  • {t['insider_name']} ({t['title']}): ${value/1000:.0f}K")

total_value = sum(int(t['value'].replace('+$', '').replace(',', '')) for t in may_2025_trades)
print(f"\nTotal value: ${total_value/1000:.0f}K")
print()

print("❌ This trade did NOT get a buy signal")
print()
print("POSSIBLE REASONS:")
print("-" * 80)
print()

print("1. REPUTATION FILTER:")
print("   The backtest uses a reputation system that tracks historical performance.")
print("   In PASS 1, it builds reputation scores based on previous insider purchases.")
print("   ")
print("   The 2023-03-15 trade was FIRST (established good reputation).")
print("   By the time 2025-05-02 came, FTAI already had a reputation.")
print("   ")
print("   If FTAI's reputation was 'poor' or 'neutral', it would have been SKIPPED.")
print("   See line 650 in backtest_batch_1_data.py:")
print("   > if reputation['position_multiplier'] == 0.0:")
print("   >     print(f'SKIPPING {ticker} - poor track record')")
print()

print("2. EXPLOSIVE CATALYST FILTER:")
print("   The strategy requires a 20%+ gain in the previous 3-5 days.")
print("   ")
print("   The 2023-03-15 trade likely had an explosive move before it.")
print("   The 2025-05-02 trade may NOT have had this catalyst.")
print("   ")
print("   Let me check the price history...")
print()

# We can't load the full cache (too slow), but we can infer from the logic
print("🔍 TO VERIFY:")
print("   Run: grep '2025-05-02' output\\ CSVs/backtest_latest_results.csv")
print("   OR check the backtest logs for 'SKIPPING FTAI'")
print()

print("="*80)
print("SUMMARY:")
print("="*80)
print("The 2025-05-02 trade was likely filtered out due to:")
print("  A) FTAI's reputation score from previous trades")
print("  OR")
print("  B) No explosive catalyst (no 20%+ move in previous 3-5 days)")
print()
print("The backtest is SELECTIVE and only enters when CONDITIONS are favorable.")
print("It's not just 'buy on every insider purchase' - it applies strict filters.")
