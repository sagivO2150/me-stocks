import json

# Load the insider trades data
with open('output CSVs/merged_insider_trades.json', 'r') as f:
    data = json.load(f)

# Check the structure
print(f'Data type: {type(data)}')
if isinstance(data, dict):
    print(f'Keys: {list(data.keys())}')
    # Likely trades are under a key
    if 'trades' in data:
        trades = data['trades']
    else:
        trades = list(data.values())[0] if data else []
else:
    trades = data

print(f'Number of trades: {len(trades)}')

# Find BSAI trades
bsai_trades = [t for t in trades if t.get('ticker') == 'BSAI']

print(f'\nFound {len(bsai_trades)} BSAI trades\n')

for i, trade in enumerate(bsai_trades, 1):
    print(f'Trade {i}:')
    print(f'  Date: {trade.get("date")}')
    print(f'  Insider: {trade.get("insider_name")}')
    print(f'  Title: {trade.get("insider_title")}')
    print(f'  Transaction: {trade.get("transaction_type")}')
    print(f'  Value: ${trade.get("value", 0):,.0f}')
    print(f'  Shares: {trade.get("shares", 0):,}')
    print(f'  Price: ${trade.get("price", 0):.2f}')
    print()
