import json
import pandas as pd
from datetime import datetime, timedelta

# Load data
with open('output CSVs/expanded_insider_trades.json', 'r') as f:
    insider_data = json.load(f).get('data', [])

with open('output CSVs/yfinance_cache_full.json', 'r') as f:
    yfinance_cache = json.load(f)

# Test with GROV
for stock in insider_data:
    if stock.get('ticker') == 'GROV':
        print('GROV insider trades:')
        for i, trade in enumerate(stock.get('trades', [])[:5]):
            shares = trade.get('shares', '')
            value = trade.get('value', '')
            if '+' in str(shares):
                try:
                    val_num = float(value.replace('+$', '').replace('$', '').replace(',', ''))
                    print(f"  {i+1}. {trade.get('trade_date')}: {shares} shares, {value} = ${val_num:,.0f}")
                except:
                    print(f"  {i+1}. {trade.get('trade_date')}: {shares} shares, {value}")
        
        # Check cache
        if 'GROV' in yfinance_cache:
            price_data = yfinance_cache['GROV']
            df = pd.DataFrame(price_data)
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            print(f'\nGROV price data: {len(df)} days')
            print(f'First date: {df.index[0]}')
            print(f'Last date: {df.index[-1]}')
            
            ipo_plus_3m = df.index[0] + timedelta(days=90)
            print(f'3-month wait ends: {ipo_plus_3m}')
            
            # Check specific insider date
            insider_date_str = '2022-06-16'
            insider_date = datetime.strptime(insider_date_str, '%Y-%m-%d')
            print(f'\nInsider date: {insider_date}')
            print(f'After 3-month wait? {insider_date >= ipo_plus_3m}')
        break
