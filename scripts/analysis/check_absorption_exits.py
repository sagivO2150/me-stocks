#!/usr/bin/env python3
"""
Analyze ALL trades to understand exit reason distribution and ROI discrepancy.
"""
import json

with open('output CSVs/insider_conviction_all_stocks_results.json') as f:
    data = json.load(f)

# Count ALL trades by exit reason
exit_reasons = {}
for stock in data['all_results']:
    if 'trades' not in stock:
        continue
    for trade in stock['trades']:
        reason = trade.get('sell_reason', 'unknown')
        if reason not in exit_reasons:
            exit_reasons[reason] = {'count': 0, 'returns': []}
        exit_reasons[reason]['count'] += 1
        exit_reasons[reason]['returns'].append(trade['return_pct'])

print("ALL 979 TRADES - EXIT REASON BREAKDOWN:")
print("=" * 80)
total_trades = sum(r['count'] for r in exit_reasons.values())
for reason, data_dict in sorted(exit_reasons.items(), key=lambda x: x[1]['count'], reverse=True):
    avg_return = sum(data_dict['returns']) / len(data_dict['returns'])
    pct_of_total = (data_dict['count'] / total_trades) * 100
    print(f"{reason:30s}: {data_dict['count']:4d} ({pct_of_total:5.1f}%)  Avg: {avg_return:+7.2f}%")

print()
print("EXAMPLE: ECG (Best Performer, +58% ROI)")
print("=" * 80)
for stock in data['top_25_best']:
    if stock['ticker'] == 'ECG':
        print(f"Total trades: {stock['total_trades']}, Win rate: {stock['win_rate']}%")
        print()
        for i, trade in enumerate(stock['trades'], 1):
            print(f"Trade {i}:")
            print(f"  Entry: {trade['entry_date']} @ ${trade['entry_price']}")
            print(f"  Exit:  {trade['exit_date']} @ ${trade['exit_price']}")
            print(f"  Return: {trade['return_pct']:+.2f}% ({trade['days_held']} days)")
            print(f"  Reason: {trade['sell_reason']}")
            print(f"  Peak gain: {trade['peak_gain']:+.2f}%")
            print()
        break

print()
print("EXAMPLE: PODD (Worst Performer, -35% ROI)")
print("=" * 80)
for stock in data['top_25_worst']:
    if stock['ticker'] == 'PODD':
        print(f"Total trades: {stock['total_trades']}, Win rate: {stock['win_rate']}%")
        print()
        for i, trade in enumerate(stock['trades'], 1):
            print(f"Trade {i}:")
            print(f"  Entry: {trade['entry_date']} @ ${trade['entry_price']}")
            print(f"  Exit:  {trade['exit_date']} @ ${trade['exit_price']}")
            print(f"  Return: {trade['return_pct']:+.2f}% ({trade['days_held']} days)")
            print(f"  Reason: {trade['sell_reason']}")
            print(f"  Peak gain: {trade['peak_gain']:+.2f}%")
            print()
        break
