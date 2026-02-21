#!/usr/bin/env python3
"""Quick analysis of exit reasons from backtest results."""

import json

with open('output CSVs/insider_conviction_all_stocks_results.json') as f:
    data = json.load(f)

exit_reasons = {}
total_return_by_reason = {}

for stock in data['all_results']:
    if 'trades' not in stock:
        continue
    for trade in stock['trades']:
        reason = trade['sell_reason']
        ret = trade['return_pct']
        
        if reason not in exit_reasons:
            exit_reasons[reason] = 0
            total_return_by_reason[reason] = 0
        
        exit_reasons[reason] += 1
        total_return_by_reason[reason] += ret

print('\nEXIT REASONS BREAKDOWN (500-stock test):')
print('=' * 80)
print(f"{'Exit Reason':<35} {'Count':<8} {'% Trades':<12} {'Avg Return'}")
print('=' * 80)

total = sum(exit_reasons.values())
for reason in sorted(exit_reasons.keys(), key=lambda x: exit_reasons[x], reverse=True):
    count = exit_reasons[reason]
    avg_ret = total_return_by_reason[reason] / count
    pct = count / total * 100
    print(f'{reason:<35} {count:<8} {pct:>6.1f}%      {avg_ret:+8.2f}%')

print('=' * 80)
print(f'Total trades: {total}')
print(f'Overall ROI: {data["overall_stats"]["overall_roi"]}%')
print()
