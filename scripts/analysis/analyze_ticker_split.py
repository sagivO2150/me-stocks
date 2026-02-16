#!/usr/bin/env python3
import pandas as pd

# Original 20 tickers from the first backtest
original_20 = ['GME', 'HYMC', 'ASA', 'NDAQ', 'WRB', 'SHCO', 'SONO', 'SGP', 'AVO', 'VANI', 
               'IMDX', 'PMN', 'MIRM', 'LEE', 'KKR', 'ABT', 'UA', 'UAA', 'FEAM', 'LW']

df = pd.read_csv('output CSVs/backtest_aggressive_daily_results.csv')

# Split by original vs new
original_trades = df[df['ticker'].isin(original_20)]
new_trades = df[~df['ticker'].isin(original_20)]

print('='*60)
print('ORIGINAL 20 TICKERS (from first backtest):')
print('='*60)
print(f'  Trades: {len(original_trades)}')
print(f'  Total invested: ${original_trades["amount_invested"].sum():,.0f}')
print(f'  Total returned: ${original_trades["returned_amount"].sum():,.0f}')
print(f'  Profit/Loss: ${original_trades["profit_loss"].sum():,.0f}')
roi_orig = (original_trades['profit_loss'].sum() / original_trades['amount_invested'].sum()) * 100
print(f'  ROI: {roi_orig:.2f}%')

print('\n' + '='*60)
print('NEW 30 TICKERS (added in second backtest):')
print('='*60)
print(f'  Trades: {len(new_trades)}')
print(f'  Total invested: ${new_trades["amount_invested"].sum():,.0f}')
print(f'  Total returned: ${new_trades["returned_amount"].sum():,.0f}')
print(f'  Profit/Loss: ${new_trades["profit_loss"].sum():,.0f}')
roi_new = (new_trades['profit_loss'].sum() / new_trades['amount_invested'].sum()) * 100
print(f'  ROI: {roi_new:.2f}%')

print('\n' + '='*60)
print('WORST NEW TICKERS (dragging us down):')
print('='*60)
new_ticker_perf = new_trades.groupby('ticker').agg({
    'profit_loss': 'sum',
    'return_pct': ['count', 'mean']
}).round(2)
new_ticker_perf.columns = ['profit_loss', 'trades', 'avg_return']
new_ticker_perf = new_ticker_perf.sort_values('profit_loss')

for idx, row in new_ticker_perf.head(10).iterrows():
    print(f"  {idx}: {int(row['trades'])} trades, avg {row['avg_return']:.1f}%, lost ${abs(row['profit_loss']):,.0f}")
