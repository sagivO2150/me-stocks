#!/usr/bin/env python3
"""
Build Expanded Insider Trading Dataset - ALL SEC Companies
===========================================================
Two-pass approach:
1. Check ALL 10,388 SEC tickers for insider purchases (quick check)
2. Fetch full trade data ONLY for tickers with purchases
3. Store in JSON format for repeated backtesting

This ensures we get complete coverage without wasting time on empty tickers.
"""

import json
import requests
from bs4 import BeautifulSoup
from multiprocessing import Pool, cpu_count
from pathlib import Path
from datetime import datetime
import time

# Paths
SEC_JSON_PATH = Path('/Users/sagiv.oron/Documents/scripts_playground/stocks/info/all_SEC_filing_companies.json')
OUTPUT_JSON = Path('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/expanded_insider_trades.json')

def quick_check_has_purchases(ticker):
    """
    Quick check: Does this ticker have ANY purchases on OpenInsider?
    Returns ticker if yes, None if no.
    """
    try:
        url = "http://openinsider.com/screener"
        params = {
            's': ticker.upper(),
            'fd': '730',  # 2 years (faster)
            'cnt': '10',   # Just need to know if purchases exist
            'page': '1'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'class': 'tinytable'})
            
            if table:
                rows = table.find_all('tr')[1:]
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 7:
                        trade_type = cols[6].text.strip()
                        if trade_type == 'P - Purchase':
                            return ticker  # Found at least one purchase!
        
        return None
        
    except Exception as e:
        return None

def quick_check_batch(ticker_batch):
    """Quick check batch with minimal delay"""
    tickers_with_purchases = []
    for ticker in ticker_batch:
        if quick_check_has_purchases(ticker):
            tickers_with_purchases.append(ticker)
            print(f"  ✓ {ticker} has purchases")
        time.sleep(0.15)  # Fast check
    return tickers_with_purchases

def fetch_insider_trades_for_ticker(ticker):
    """
    Fetch full insider trades for a single ticker (PURCHASES ONLY).
    Returns same format as merged_insider_trades.json
    """
    try:
        url = "http://openinsider.com/screener"
        params = {
            's': ticker.upper(),
            'fd': '1461',  # Last 4 years
            'cnt': '1000',
            'page': '1'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'class': 'tinytable'})
        
        if not table:
            return None
        
        rows = table.find_all('tr')[1:]  # Skip header
        
        if not rows:
            return None
        
        purchases = []
        total_value = 0
        unique_insiders = set()
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 11:
                continue
            
            # Check if it's a purchase
            trade_type = cols[6].text.strip()
            if trade_type != 'P - Purchase':
                continue  # Skip sales
            
            # Extract trade details
            try:
                filing_date = cols[1].text.strip()
                trade_date = cols[2].text.strip()
                insider_name = cols[4].text.strip()
                title = cols[5].text.strip()
                shares = cols[8].text.strip().replace(',', '')
                price = cols[7].text.strip().replace('$', '').replace(',', '')
                value = cols[11].text.strip().replace('$', '').replace(',', '').replace('+', '')
                
                # Parse value
                try:
                    value_float = float(value) if value else 0
                except:
                    value_float = 0
                
                purchases.append({
                    'filing_date': filing_date,
                    'trade_date': trade_date,
                    'insider_name': insider_name,
                    'title': title,
                    'shares': shares,
                    'price': price,
                    'value': f'+${value}',  # Match format
                    'role': title
                })
                
                total_value += value_float
                unique_insiders.add(insider_name)
                
            except Exception as e:
                continue
        
        if not purchases:
            return None
        
        # Get company name from the page
        company_name = ticker  # Default
        try:
            company_header = soup.find('h3')
            if company_header:
                company_name = company_header.text.strip()
        except:
            pass
        
        result = {
            'ticker': ticker,
            'company_name': company_name,
            'total_value': total_value,
            'total_purchases': len(purchases),
            'unique_insiders': len(unique_insiders),
            'trades': purchases
        }
        
        print(f"  ✓ {ticker}: {len(purchases)} purchases, ${total_value:,.0f} total value")
        return result
        
    except Exception as e:
        print(f"  ✗ {ticker}: Error - {e}")
        return None

def fetch_batch(ticker_batch):
    """Fetch a batch of tickers with rate limiting"""
    results = []
    for ticker in ticker_batch:
        result = fetch_insider_trades_for_ticker(ticker)
        if result:
            results.append(result)
        time.sleep(0.2)  # Rate limiting
    return results

def main():
    print("\n" + "="*80)
    print("BUILDING EXPANDED INSIDER TRADING DATASET - ALL SEC COMPANIES")
    print("="*80 + "\n")
    
    # Step 1: Load ALL SEC tickers
    print("📂 Loading ALL SEC company tickers...")
    with open(SEC_JSON_PATH, 'r') as f:
        sec_data = json.load(f)
    
    all_tickers = [entry['ticker'] for entry in sec_data.values()]
    print(f"   Loaded {len(all_tickers)} SEC tickers\n")
    
    # Step 2: PASS 1 - Quick check which tickers have purchases
    print("🔍 PASS 1: Quick check for tickers with purchases...")
    num_workers = cpu_count()
    batch_size = max(1, len(all_tickers) // num_workers)
    batches = [all_tickers[i:i+batch_size] for i in range(0, len(all_tickers), batch_size)]
    
    print(f"   Using {num_workers} workers to check {len(all_tickers)} tickers")
    print(f"   Estimated time: ~{len(all_tickers) * 0.15 / num_workers / 60:.1f} minutes\n")
    
    tickers_with_purchases = []
    with Pool(processes=num_workers) as pool:
        for batch_idx, batch_results in enumerate(pool.imap(quick_check_batch, batches)):
            tickers_with_purchases.extend(batch_results)
            completed = (batch_idx + 1) * len(batches[batch_idx])
            pct = min(100, completed / len(all_tickers) * 100)
            print(f"\nBatch {batch_idx + 1}/{len(batches)} completed ({completed}/{len(all_tickers)}, {pct:.1f}%)")
            print(f"Found {len(tickers_with_purchases)} with purchases so far")
    
    print(f"\n✅ PASS 1 COMPLETE: Found {len(tickers_with_purchases)} tickers with purchases out of {len(all_tickers)} total")
    print(f"   Coverage: {len(tickers_with_purchases) / len(all_tickers) * 100:.1f}%\n")
    
    # Step 3: PASS 2 - Fetch full trade data for tickers with purchases
    print("🔄 PASS 2: Fetching full insider trade data (PURCHASES ONLY)...")
    batch_size = max(1, len(tickers_with_purchases) // num_workers)
    batches = [tickers_with_purchases[i:i+batch_size] for i in range(0, len(tickers_with_purchases), batch_size)]
    
    print(f"   Using {num_workers} workers to process {len(batches)} batches")
    print(f"   Estimated time: ~{len(tickers_with_purchases) * 0.2 / num_workers / 60:.1f} minutes\n")
    
    all_results = []
    with Pool(processes=num_workers) as pool:
        for batch_idx, batch_results in enumerate(pool.imap(fetch_batch, batches)):
            all_results.extend(batch_results)
            completed = (batch_idx + 1) * len(batches[batch_idx])
            pct = min(100, completed / len(tickers_with_purchases) * 100)
            print(f"\nBatch {batch_idx + 1}/{len(batches)} completed ({completed}/{len(tickers_with_purchases)}, {pct:.1f}%)")
    
    # Step 4: Save to JSON
    print(f"\n{'='*80}")
    print("SAVING RESULTS")
    print(f"{'='*80}\n")
    
    output_data = {
        'data': all_results,
        'metadata': {
            'total_tickers': len(all_results),
            'total_purchases': sum(t['total_purchases'] for t in all_results),
            'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'OpenInsider',
            'filter': 'Purchases only (last 4 years)',
            'sec_companies_checked': len(all_tickers),
            'tickers_with_data': len(tickers_with_purchases),
            'coverage_rate': f"{len(tickers_with_purchases) / len(all_tickers) * 100:.1f}%"
        }
    }
    
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✅ Saved {len(all_results)} tickers to: {OUTPUT_JSON}")
    
    # Step 5: Summary
    total_purchases = sum(t['total_purchases'] for t in all_results)
    total_value = sum(t['total_value'] for t in all_results)
    
    print(f"\n{'='*80}")
    print("FINAL DATASET SUMMARY")
    print(f"{'='*80}")
    print(f"SEC companies checked: {len(all_tickers):,}")
    print(f"Tickers with purchases: {len(tickers_with_purchases):,}")
    print(f"Coverage rate: {len(tickers_with_purchases) / len(all_tickers) * 100:.1f}%")
    print(f"\nTotal tickers in dataset: {len(all_results):,}")
    print(f"Total purchases: {total_purchases:,}")
    print(f"Total value: ${total_value:,.0f}")
    print(f"Average purchases per ticker: {total_purchases / len(all_results):.1f}")
    print(f"\n✓ Dataset ready for backtesting!")
    print(f"✓ Run your backtest pointing to: {OUTPUT_JSON}")
    print(f"✓ No need to re-fetch - data is cached!\n")
    
    # Show top 10 by purchase count
    sorted_by_purchases = sorted(all_results, key=lambda x: x['total_purchases'], reverse=True)
    print("\n📊 Top 10 tickers by purchase count:")
    for i, stock in enumerate(sorted_by_purchases[:10], 1):
        print(f"   {i:2d}. {stock['ticker']:6s} - {stock['total_purchases']:3d} purchases (${stock['total_value']:,.0f})")

if __name__ == '__main__':
    main()
