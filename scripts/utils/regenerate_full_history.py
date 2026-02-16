#!/usr/bin/env python3
"""
Regenerate full_history_insider_trades.json with ALL 50 tickers
"""

import json
import subprocess
import sys
from pathlib import Path
from multiprocessing import Pool, cpu_count
from typing import Dict, Any

DAYS_BACK = 1825  # 5 years

def fetch_ticker_history(ticker: str) -> Dict[str, Any]:
    """Fetch full history for one ticker"""
    print(f"Fetching {ticker}...", flush=True)
    
    try:
        cmd = [
            sys.executable,
            "scripts/core/fetch_insider_trades.py",
            ticker,
            str(DAYS_BACK)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get('success') and data.get('total_purchases', 0) > 0:
                print(f"✓ {ticker}: {data['total_purchases']} purchases", flush=True)
                
                # Format to match merged structure
                return {
                    'ticker': ticker,
                    'company_name': ticker,  # Will be enriched if needed
                    'total_value': data.get('purchase_value', 0),
                    'total_purchases': data['total_purchases'],
                    'unique_insiders': len(set(p['insider_name'] for p in data['purchases'])),
                    'trades': [
                        {
                            'insider_name': p['insider_name'],
                            'title': p['title'],
                            'trade_date': p['date'],
                            'filing_date': p['filing_date'],
                            'value': f"+${p['value']:,.0f}",
                            'qty': f"+{p['shares']:,}"
                        }
                        for p in data['purchases']
                    ]
                }
            else:
                print(f"✗ {ticker}: No purchases", flush=True)
                return None
        else:
            print(f"✗ {ticker}: Failed (exit {result.returncode})", flush=True)
            return None
            
    except Exception as e:
        print(f"✗ {ticker}: Error - {e}", flush=True)
        return None


def main():
    # Load top 50 tickers from monthly file
    monthly_path = Path("output CSVs/top_monthly_insider_trades.json")
    with open(monthly_path, 'r') as f:
        monthly_data = json.load(f)
    
    tickers = [stock['ticker'] for stock in monthly_data['data'][:50]]
    print(f"Fetching full history for {len(tickers)} tickers...")
    print(f"Using {cpu_count()} parallel workers\n")
    
    # Parallel fetch
    with Pool(cpu_count()) as pool:
        results = pool.map(fetch_ticker_history, tickers)
    
    # Filter successful results
    stocks_with_data = [r for r in results if r is not None]
    
    print(f"\n✓ Successfully fetched {len(stocks_with_data)}/{len(tickers)} tickers")
    
    # Save
    output_path = Path("output CSVs/full_history_insider_trades.json")
    with open(output_path, 'w') as f:
        json.dump(stocks_with_data, f, indent=2)
    
    print(f"Saved to {output_path}")
    
    # Show stats
    total_trades = sum(s['total_purchases'] for s in stocks_with_data)
    print(f"\nTotal purchases across all stocks: {total_trades}")


if __name__ == '__main__':
    main()
