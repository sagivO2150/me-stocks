#!/usr/bin/env python3
"""
Run simple backtest using FULL historical data from webapp API
This captures ALL insider trades going back in time, not just recent ones
"""
import requests
import json
import sys
import subprocess
sys.path.append('/Users/sagiv.oron/Documents/scripts_playground/stocks/scripts/tests')
from backtest_simple_strategy import backtest_simple_strategy

def fetch_all_insider_trades(tickers):
    """Fetch ALL historical insider trades from the webapp API"""
    all_stocks = []
    
    for ticker in tickers:
        print(f"Fetching full history for {ticker}...")
        try:
            response = requests.get(f'http://localhost:3001/api/insider-trades/{ticker}', timeout=10)
            data = response.json()
            
            if not data['success'] or not data['purchases']:
                print(f"  ⚠️  No purchases found")
                continue
            
            purchases = data['purchases']
            
            # Convert to the format expected by backtest
            trades = []
            total_value = 0
            
            for purchase in purchases:
                value_formatted = f"+${purchase['value']:,.0f}"
                trade = {
                    'trade_date': purchase['date'],
                    'filing_date': purchase.get('filing_date'),  # Include filing date
                    'insider_name': purchase['insider_name'],
                    'title': purchase.get('title', ''),
                    'value': value_formatted,
                    'qty': f"+{purchase['shares']:,}"
                }
                trades.append(trade)
                total_value += purchase['value']
            
            stock_data = {
                'ticker': ticker,
                'company_name': f"{ticker} Company",
                'total_value': total_value,
                'total_purchases': len(trades),
                'unique_insiders': len(set(t['insider_name'] for t in trades)),
                'trades': sorted(trades, key=lambda x: x['trade_date'])
            }
            
            all_stocks.append(stock_data)
            print(f"  ✅ Found {len(trades)} trades dating back to {purchases[-1]['date']}")
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
    
    return all_stocks

# Get list of top 20 tickers from the monthly file
json_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/top_monthly_insider_trades.json'
with open(json_path, 'r') as f:
    monthly_data = json.load(f)

tickers = [stock['ticker'] for stock in monthly_data['data'][:20]]

print(f'📊 Fetching FULL historical data for {len(tickers)} stocks...\n')

# Fetch complete historical data from API
stocks = fetch_all_insider_trades(tickers)

if not stocks:
    print("❌ No data found!")
    sys.exit(1)

# Create JSON in format expected by backtest
json_data = {
    'updated_at': '2026-02-13',
    'total_tickers': len(stocks),
    'total_trades': sum(s['total_purchases'] for s in stocks),
    'data': stocks
}

# Save to temp file
temp_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/full_history_insider_trades.json'
with open(temp_path, 'w') as f:
    json.dump(json_data, f, indent=2)

print(f'\n✅ Created JSON with {json_data["total_tickers"]} stocks and {json_data["total_trades"]} historical trades')

# Run backtest
print("\n" + "=" * 80)
print("RUNNING BACKTEST ON FULL HISTORICAL DATA...")
print("=" * 80 + "\n")

results = backtest_simple_strategy(
    json_file=temp_path,
    position_size=1000,
    stop_loss_pct=5.0
)

# Save results
if results:
    import csv
    output_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_simple_results.csv'
    
    all_fields = set()
    for result in results:
        all_fields.update(result.keys())
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sorted(all_fields))
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n✅ Backtest results saved")
    print(f"📊 Total trades executed: {len(results)}")
    
    # Generate PDF
    print("\n" + "=" * 80)
    print("GENERATING PDF REPORT...")
    print("=" * 80 + "\n")
    
    pdf_script = '/Users/sagiv.oron/Documents/scripts_playground/stocks/scripts/generate_backtest_pdf.py'
    result = subprocess.run([
        sys.executable,
        pdf_script,
        '--strategy', 'simple',
        '--period', '1y'
    ])
    
    if result.returncode == 0:
        print("\n✅ PDF generation complete!")
        print("📁 Opening PDF...")
        subprocess.run(['open', '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_simple_visual_report.pdf'])
