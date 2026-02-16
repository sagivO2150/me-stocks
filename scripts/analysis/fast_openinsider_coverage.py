#!/usr/bin/env python3
"""
Fast OpenInsider Coverage Check
================================
Instead of checking each ticker individually (slow), scrape OpenInsider's 
paginated screener to get ALL tickers with recent insider activity.

Strategy:
1. Fetch latest insider trades page by page (no ticker filter)
2. Extract all unique tickers that appear
3. Those are the tickers with OpenInsider data!

This is 1000x faster than individual ticker checks.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path

# Paths
SEC_JSON_PATH = Path(__file__).parent.parent.parent / 'info' / 'all_SEC_filing_companies.json'
OUTPUT_PATH = Path(__file__).parent.parent.parent / 'output CSVs' / 'openinsider_tickers_fast.json'

def fetch_openinsider_tickers(max_pages=500):
    """
    Fetch all tickers from OpenInsider by paginating through latest trades.
    OpenInsider shows ~50 trades per page, so 500 pages = ~25,000 trades.
    """
    url = "http://openinsider.com/screener"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    all_tickers = set()
    
    print(f"Fetching OpenInsider tickers (max {max_pages} pages)...")
    print("This will take approximately {:.1f} minutes\n".format(max_pages * 1.5 / 60))
    
    for page in range(1, max_pages + 1):
        try:
            params = {
                'fd': '1461',  # Last 4 years
                'cnt': '1000',  # Try to get max per page
                'page': str(page)
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                table = soup.find('table', {'class': 'tinytable'})
                
                if table:
                    rows = table.find_all('tr')[1:]  # Skip header
                    
                    if not rows:
                        print(f"\nPage {page}: No more data - stopping")
                        break
                    
                    page_tickers = set()
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 4:
                            # Ticker is usually in column 3 or 4
                            ticker_link = cols[3].find('a')
                            if ticker_link:
                                ticker = ticker_link.text.strip()
                                if ticker:
                                    page_tickers.add(ticker)
                    
                    all_tickers.update(page_tickers)
                    
                    if page % 10 == 0:
                        print(f"Page {page}/{max_pages}: Found {len(page_tickers)} tickers this page, {len(all_tickers)} unique total")
                else:
                    print(f"\nPage {page}: No table found - stopping")
                    break
            else:
                print(f"\nPage {page}: HTTP {response.status_code} - stopping")
                break
            
            # Rate limiting
            time.sleep(1.5)
            
        except Exception as e:
            print(f"\nPage {page}: Error - {e}")
            break
    
    print(f"\n✓ Found {len(all_tickers)} unique tickers with OpenInsider data")
    return list(all_tickers)

def main():
    # Step 1: Load SEC companies
    print(f"Loading SEC companies from {SEC_JSON_PATH}...")
    with open(SEC_JSON_PATH, 'r') as f:
        sec_data = json.load(f)
    
    sec_companies = {entry['ticker']: entry for entry in sec_data.values()}
    print(f"Loaded {len(sec_companies)} SEC companies")
    
    # Step 2: Fetch all OpenInsider tickers (fast!)
    openinsider_tickers = fetch_openinsider_tickers(max_pages=500)
    
    # Step 3: Match against SEC list
    print("\n" + "="*80)
    print("MATCHING AGAINST SEC DATABASE")
    print("="*80)
    
    matched = []
    unmatched_openinsider = []
    
    for ticker in openinsider_tickers:
        if ticker.upper() in sec_companies:
            matched.append(ticker.upper())
        else:
            unmatched_openinsider.append(ticker)
    
    print(f"OpenInsider tickers found: {len(openinsider_tickers)}")
    print(f"Matched to SEC database: {len(matched)}")
    print(f"OpenInsider tickers NOT in SEC database: {len(unmatched_openinsider)}")
    
    # Step 4: Calculate coverage
    coverage_rate = len(matched) / len(sec_companies) * 100
    
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    print(f"Total SEC companies: {len(sec_companies):,}")
    print(f"SEC companies with OpenInsider data: {len(matched):,}")
    print(f"Coverage rate: {coverage_rate:.1f}%")
    
    # Save results
    results = {
        'total_sec_companies': len(sec_companies),
        'openinsider_tickers_found': len(openinsider_tickers),
        'matched_tickers': len(matched),
        'coverage_rate': coverage_rate,
        'tickers_with_data': sorted(matched),
        'unmatched_openinsider_tickers': sorted(unmatched_openinsider)
    }
    
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to: {OUTPUT_PATH}")
    
    # Show examples
    print("\n" + "="*80)
    print("EXAMPLE TICKERS WITH DATA (first 50):")
    print("="*80)
    for ticker in sorted(matched)[:50]:
        company = sec_companies[ticker]
        print(f"  {ticker:6s} - {company['title']}")
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print(f"✅ Found {len(matched):,} SEC companies with OpenInsider data")
    print(f"✅ Your backtest can expand from 50 to {len(matched):,} tickers!")
    print(f"✅ This is {len(matched) / 50:.0f}x more data")

if __name__ == '__main__':
    main()
