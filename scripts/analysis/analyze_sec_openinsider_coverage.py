#!/usr/bin/env python3
"""
Analyze SEC registered companies and check OpenInsider coverage.
Query OpenInsider.com directly to see which SEC companies have insider trading data available.
"""

import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
from multiprocessing import Pool
from pathlib import Path
import random

# Paths
SEC_JSON_PATH = Path(__file__).parent.parent.parent / 'info' / 'all_SEC_filing_companies.json'
OUTPUT_PATH = Path(__file__).parent.parent.parent / 'output CSVs' / 'sec_openinsider_coverage.csv'
PROGRESS_PATH = Path(__file__).parent.parent.parent / 'output CSVs' / 'sec_openinsider_progress.json'

def load_sec_companies():
    """Load SEC company tickers from JSON file or URL."""
    if not SEC_JSON_PATH.exists():
        print(f"Downloading SEC company tickers to {SEC_JSON_PATH}...")
        import requests
        url = "https://www.sec.gov/files/company_tickers.json"
        response = requests.get(url)
        data = response.json()
        
        # Save to file
        SEC_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SEC_JSON_PATH, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved {len(data)} companies to {SEC_JSON_PATH}")
    else:
        print(f"Loading SEC companies from {SEC_JSON_PATH}...")
        with open(SEC_JSON_PATH, 'r') as f:
            data = json.load(f)
    
    # Convert to DataFrame
    companies = []
    for key, value in data.items():
        companies.append({
            'cik': value['cik_str'],
            'ticker': value['ticker'],
            'title': value['title']
        })
    
    df = pd.DataFrame(companies)
    print(f"Loaded {len(df)} SEC registered companies")
    return df

def load_openinsider_trades():
    """Check if a ticker has data on OpenInsider by querying the website."""
    # This function is no longer needed - we'll query the website directly
    pass

def check_openinsider_ticker(ticker):
    """Check if a ticker has insider trading data on OpenInsider.com"""
    try:
        # Use the same approach as fetch_insider_trades.py
        url = "http://openinsider.com/screener"
        params = {
            's': ticker.upper(),
            'fd': '730',  # 2 years back (faster than 4 years)
            'cnt': '100',  # Just need to know if data exists
            'page': '1'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'class': 'tinytable'})
            
            if table:
                rows = table.find_all('tr')[1:]  # Skip header
                
                # Count purchases and sales
                purchases = 0
                sales = 0
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 7:
                        trade_type = cols[6].text.strip()
                        if trade_type == 'P - Purchase':
                            purchases += 1
                        elif trade_type == 'S - Sale':
                            sales += 1
                
                has_data = (purchases > 0 or sales > 0)
                
                return {
                    'ticker': ticker,
                    'has_openinsider_data': has_data,
                    'num_purchases': purchases,
                    'num_sales': sales,
                    'total_trades': purchases + sales,
                    'error': None
                }
            else:
                return {
                    'ticker': ticker,
                    'has_openinsider_data': False,
                    'num_purchases': 0,
                    'num_sales': 0,
                    'total_trades': 0,
                    'error': None
                }
        else:
            return {
                'ticker': ticker,
                'has_openinsider_data': False,
                'num_purchases': 0,
                'num_sales': 0,
                'total_trades': 0,
                'error': f'HTTP {response.status_code}'
            }
    except Exception as e:
        return {
            'ticker': ticker,
            'has_openinsider_data': False,
            'num_purchases': 0,
            'num_sales': 0,
            'total_trades': 0,
            'error': str(e)
        }

def check_ticker_batch(ticker_batch):
    """Check a batch of tickers (for multiprocessing)."""
    results = []
    for i, ticker in enumerate(ticker_batch):
        result = check_openinsider_ticker(ticker)
        results.append(result)
        
        # Minimal rate limiting - OpenInsider can handle this (your backtest proves it)
        time.sleep(0.2)
    
    return results

def main():
    # Load SEC companies
    sec_companies = load_sec_companies()
    
    # Check ALL tickers (not sampling)
    print(f"\nChecking ALL {len(sec_companies)} tickers against OpenInsider...")
    print("This will take approximately {:.1f} minutes (~{:.1f} hours)\n".format(
        len(sec_companies) * 1.0 / 60,
        len(sec_companies) * 1.0 / 3600
    ))
    
    # Use all tickers (no sampling)
    sample = sec_companies
    
    # Use ALL CPU cores (like your backtest does!)
    from multiprocessing import cpu_count
    num_workers = cpu_count()
    
    tickers_list = sample['ticker'].tolist()
    batch_size = max(1, len(tickers_list) // num_workers)  # Divide evenly across workers
    batches = [tickers_list[i:i+batch_size] for i in range(0, len(tickers_list), batch_size)]
    
    print(f"Processing {len(batches)} batches with {num_workers} parallel workers...")
    print(f"Expected time: ~{len(tickers_list) * 0.2 / num_workers / 60:.1f} minutes\n")
    
    all_results = []
    with Pool(processes=num_workers) as pool:
        for batch_idx, batch_results in enumerate(pool.imap(check_ticker_batch, batches)):
            all_results.extend(batch_results)
            completed = (batch_idx + 1) * len(batches[batch_idx])
            total = len(tickers_list)
            pct = min(100, completed / total * 100)
            print(f"Progress: {completed:,}/{total:,} ({pct:.1f}%) - Batch {batch_idx + 1}/{len(batches)} completed")
    
    # Convert results to DataFrame
    results_df = pd.DataFrame(all_results)
    
    # Merge with sample
    sample = sample.merge(results_df, on='ticker', how='left')
    sample['has_openinsider_data'] = sample['has_openinsider_data'].fillna(False)
    
    # Save sample results
    sample.to_csv(OUTPUT_PATH, index=False)
    print(f"\n✓ Sample results saved to: {OUTPUT_PATH}")
    
    print("\n" + "="*80)
    print("OPENINSIDER COVERAGE ANALYSIS (SAMPLE)")
    print("="*80)
    print(f"Sample size: {len(sample):,} out of {len(sec_companies):,} total SEC companies")
    print(f"Has OpenInsider data: {sample['has_openinsider_data'].sum():,}")
    print(f"No OpenInsider data: {(~sample['has_openinsider_data']).sum():,}")
    print(f"Sample coverage: {sample['has_openinsider_data'].sum() / len(sample) * 100:.1f}%")
    
    # Calculate actual totals (not extrapolated)
    total_with_data = sample['has_openinsider_data'].sum()
    total_without_data = len(sample) - total_with_data
    coverage_rate = total_with_data / len(sample)
    
    print("\n" + "="*80)
    print("FINAL RESULTS - ALL SEC COMPANIES")
    print("="*80)
    print(f"Total SEC companies checked: {len(sample):,}")
    print(f"Companies WITH OpenInsider data: {total_with_data:,}")
    print(f"Companies WITHOUT OpenInsider data: {total_without_data:,}")
    print(f"Coverage rate: {coverage_rate * 100:.1f}%")
    
    # Show some examples
    print("\n" + "="*80)
    print("EXAMPLE COMPANIES WITH OPENINSIDER DATA (first 20):")
    print("="*80)
    has_data = sample[sample['has_openinsider_data']].head(20)
    for _, row in has_data.iterrows():
        purchases = row.get('num_purchases', 0)
        sales = row.get('num_sales', 0)
        print(f"  {row['ticker']:6s} - {row['title']:50s} (P:{purchases:3d} S:{sales:3d})")
    
    print("\n" + "="*80)
    print("EXAMPLE COMPANIES WITHOUT OPENINSIDER DATA (first 20):")
    print("="*80)
    no_data = sample[~sample['has_openinsider_data']].head(20)
    for _, row in no_data.iterrows():
        error = row.get('error', 'No trades found')
        print(f"  {row['ticker']:6s} - {row['title']:50s}")
    
    # Analyze ticker patterns for those without data
    print("\n" + "="*80)
    print("TICKER PATTERN ANALYSIS (No OpenInsider Data):")
    print("="*80)
    no_data_df = sample[~sample['has_openinsider_data']]
    
    if len(no_data_df) > 0:
        has_dash = no_data_df['ticker'].str.contains('-').sum()
        ends_with_w = no_data_df['ticker'].str.endswith('W').sum()
        ends_with_u = no_data_df['ticker'].str.endswith('U').sum()
        ends_with_f = no_data_df['ticker'].str.endswith('F').sum()
        ends_with_y = no_data_df['ticker'].str.endswith('Y').sum()
        
        print(f"  Tickers with '-' (preferred/warrants): {has_dash:,} ({has_dash/len(no_data_df)*100:.1f}%)")
        print(f"  Ends with 'W' (warrants): {ends_with_w:,} ({ends_with_w/len(no_data_df)*100:.1f}%)")
        print(f"  Ends with 'U' (units): {ends_with_u:,} ({ends_with_u/len(no_data_df)*100:.1f}%)")
        print(f"  Ends with 'F' (foreign ADRs): {ends_with_f:,} ({ends_with_f/len(no_data_df)*100:.1f}%)")
        print(f"  Ends with 'Y' (foreign ADRs): {ends_with_y:,} ({ends_with_y/len(no_data_df)*100:.1f}%)")
    
    print("\n" + "="*80)
    print("FINAL CONCLUSION")
    print("="*80)
    print(f"✅ OpenInsider has data for {total_with_data:,} of {len(sec_companies):,} SEC companies")
    print(f"✅ Coverage rate: {coverage_rate * 100:.1f}%")
    print(f"\n✓ Your backtest can expand from 50 to {total_with_data:,} tickers!")
    print(f"✓ This is {total_with_data / 50:.0f}x more data than your current sample")
    print(f"\n⚠️  Note: Your current 50 tickers are the TOP monthly purchases (high conviction)")
    print(f"   Expanding to all {total_with_data:,} tickers will include lower-conviction trades")
    print(f"   Consider filtering by trade value/size to maintain quality")

if __name__ == '__main__':
    main()
