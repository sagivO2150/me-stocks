#!/usr/bin/env python3
"""
Test if foreign ADRs have Form 4 filings in EDGAR (2026 rule check)
"""
import json
import subprocess
import sys

# Load SEC companies
with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/info/all_SEC_filing_companies.json', 'r') as f:
    companies = json.load(f)

# Filter for foreign ADRs (ending in F or Y, AND title contains /ADR or AG or PLC or Ltd or S.A.)
foreign_tickers = [
    entry['ticker'] for entry in companies.values() 
    if (entry['ticker'].endswith('F') or entry['ticker'].endswith('Y'))
    and ('/ADR' in entry['title'] or ' AG' in entry['title'] or 'PLC' in entry['title'] 
         or 'Ltd' in entry['title'] or 'S.A.' in entry['title'] or 'Limited' in entry['title']
         or 'Corp' in entry['title'] or 'Inc' in entry['title'])
]

print(f"Found {len(foreign_tickers)} foreign ADR tickers")

# Manually add confirmed foreign companies
priority_foreign = ['DTEGY', 'HSBC', 'TELNY', 'WPPGF', 'SONY', 'CYATY', 'RTNTF', 'HTHIY',
                   'SNY', 'INFY', 'BMWKY', 'BAESY', 'IFNNY', 'MGCLY']
test_tickers = priority_foreign + [t for t in foreign_tickers[:10] if t not in priority_foreign]
test_tickers = test_tickers[:20]  # Limit to 20

print(f"\nTesting 20 foreign ADRs for Form 4 filings (including DTEGY which had 415 sales)...\n")

results = []
for ticker in test_tickers:
    print(f"Testing {ticker}...", end=" ", flush=True)
    
    # Run EDGAR fetch script
    cmd = [
        '/Users/sagiv.oron/Documents/scripts_playground/stocks/.venv/bin/python',
        '/Users/sagiv.oron/Documents/scripts_playground/stocks/scripts/data_sources/edgar/fetch_edgar_trades.py',
        ticker,
        '1'  # 1 year lookback
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout
        
        # Parse JSON output
        data = json.loads(output)
        
        has_filings = (data.get('total_purchases', 0) + data.get('total_sales', 0)) > 0
        
        if has_filings:
            print(f"✅ HAS FILINGS! Purchases: {data['total_purchases']}, Sales: {data['total_sales']}")
            results.append({
                'ticker': ticker,
                'has_data': True,
                'purchases': data['total_purchases'],
                'sales': data['total_sales']
            })
        else:
            print("❌ No filings")
            results.append({
                'ticker': ticker,
                'has_data': False
            })
    except Exception as e:
        print(f"⚠️  Error: {e}")
        results.append({
            'ticker': ticker,
            'has_data': False,
            'error': str(e)
        })

# Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
tickers_with_data = [r for r in results if r.get('has_data')]
print(f"Tickers tested: {len(results)}")
print(f"Tickers with Form 4 filings: {len(tickers_with_data)}")
print(f"Coverage rate: {len(tickers_with_data)/len(results)*100:.1f}%")

if tickers_with_data:
    print("\n✅ FOREIGN ADRs WITH FILINGS:")
    for r in tickers_with_data:
        print(f"  {r['ticker']}: {r['purchases']} purchases, {r['sales']} sales")
else:
    print("\n❌ NO foreign ADRs have Form 4 filings yet (2026 rule not active)")
