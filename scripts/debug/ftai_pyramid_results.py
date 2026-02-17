#!/usr/bin/env python3
"""
Show FTAI performance with pyramid strategy
"""

import pandas as pd

df = pd.read_csv('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_reputation_results.csv')
ftai_trades = df[df['ticker'] == 'FTAI'].sort_values('entry_date')

print('='*80)
print('FTAI TRADES WITH PYRAMID STRATEGY')
print('='*80)
print()

for idx, row in ftai_trades.iterrows():
    entry_date = row['entry_date']
    exit_date = row['exit_date']
    entry_price = row['entry_price']
    exit_price = row['exit_price']
    invested = row['amount_invested']
    returned = row['returned_amount']
    profit = row['profit_loss']
    return_pct = row['return_pct']
    days = row['days_held']
    reason = row['exit_reason']
    
    print(f'Entry: {entry_date} at ${entry_price:.2f}')
    print(f'Exit:  {exit_date} at ${exit_price:.2f}')
    print(f'Invested: ${invested:.0f} → Returned: ${returned:.0f}')
    print(f'Profit: ${profit:.0f} ({return_pct:+.1f}%)')
    print(f'Held: {int(days)} days | Exit: {reason}')
    print()

total_invested = ftai_trades['amount_invested'].sum()
total_profit = ftai_trades['profit_loss'].sum()
total_roi = (total_profit / total_invested) * 100

print('='*80)
print(f'TOTAL FTAI PERFORMANCE WITH PYRAMIDING:')
print(f'  Total Invested: ${total_invested:,.0f}')
print(f'  Total Profit: ${total_profit:,.0f}')
print(f'  Total ROI: {total_roi:+.1f}%')
print(f'  Number of positions: {len(ftai_trades)}')
print()

# Compare to single position
single_position_invested = 1000
single_position_profit = 11545.80
single_position_roi = (single_position_profit / single_position_invested) * 100

print('='*80)
print('COMPARISON:')
print('='*80)
print(f'BEFORE (single position):')
print(f'  Invested: $1,000')
print(f'  Profit: $11,546')
print(f'  ROI: +1154.6%')
print()
print(f'AFTER (pyramid strategy):')
print(f'  Invested: ${total_invested:,.0f}')
print(f'  Profit: ${total_profit:,.0f}')
print(f'  ROI: {total_roi:+.1f}%')
print()
print(f'IMPROVEMENT: ${total_profit - single_position_profit:,.0f} more profit!')
