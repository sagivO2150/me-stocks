#!/usr/bin/env python3
"""
Run simple backtest on first 20 stocks and generate PDF
"""
import json
import sys
sys.path.append('/Users/sagiv.oron/Documents/scripts_playground/stocks/scripts/tests')
from backtest_simple_strategy import backtest_simple_strategy
import subprocess

# Load full data
json_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/top_monthly_insider_trades.json'
with open(json_path, 'r') as f:
    data = json.load(f)

# Keep only first 20 stocks
data['data'] = data['data'][:20]
data['total_tickers'] = 20
data['total_trades'] = sum(s['total_purchases'] for s in data['data'])

# Save to temp file
temp_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/top_20_insider_trades.json'
with open(temp_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f'✅ Created JSON with 20 stocks')
print(f'📊 Total tickers: {data["total_tickers"]}')
print(f'📈 Total trades: {data["total_trades"]}\n')

# Run backtest
results = backtest_simple_strategy(
    json_file=temp_path,
    position_size=1000,
    stop_loss_pct=5.0
)

# Save results to the simple results file
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
