#!/usr/bin/env python3
"""
Find missing tickers in BATCHES with checkpoints.
Keeps existing 2,746 tickers and searches remaining ~7,642.
Saves progress after each batch so you can verify before continuing.
"""

import json
import requests
from bs4 import BeautifulSoup
import time
from multiprocessing import Pool, cpu_count

def quick_check_has_purchases(ticker):
    """Quick check if ticker has ANY purchase trades"""
    try:
        url = "http://openinsider.com/screener"
        params = {
            's': ticker.upper(),
            'fd': '1461',  # 4 YEARS - same as full fetch!
            'cnt': '10'
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
    """Quick check batch with 0.3s delays (more reliable than 0.15s)"""
    tickers_with_purchases = []
    for ticker in ticker_batch:
        result = quick_check_has_purchases(ticker)
        if result:
            tickers_with_purchases.append(ticker)
            print(f"  ✓ {ticker} has purchases")
        time.sleep(0.3)  # Slower to avoid rate limiting
    return tickers_with_purchases

def main():
    print("\n" + "="*80)
    print("FIND MISSING TICKERS - BATCH MODE WITH CHECKPOINTS")
    print("="*80)
    
    # Load ALL SEC tickers
    print("\n📂 Loading SEC company list...")
    with open('info/all_SEC_filing_companies.json', 'r') as f:
        sec_data = json.load(f)
        # It's a dict with numeric keys, get all values
        all_sec_tickers = [item['ticker'] for item in sec_data.values()]
    print(f"   Total SEC tickers: {len(all_sec_tickers)}")
    
    # Load tickers we already found
    print("\n📂 Loading tickers we already found...")
    with open('/tmp/tickers_with_data.txt', 'r') as f:
        found_tickers = set(line.strip() for line in f if line.strip())
    print(f"   Already found: {len(found_tickers)} tickers")
    
    # Get remaining tickers to check
    remaining = [t for t in all_sec_tickers if t not in found_tickers]
    print(f"   Remaining to check: {len(remaining)} tickers")
    
    # Ask user for batch size
    batch_size = 2500
    print(f"\n⚙️  Will process in batches of {batch_size} tickers")
    print(f"   Total batches: {len(remaining) // batch_size + 1}")
    
    num_workers = cpu_count()
    print(f"   Using {num_workers} workers")
    
    # Process FIRST BATCH ONLY
    print(f"\n{'='*80}")
    print(f"BATCH 1: Checking first {batch_size} tickers")
    print(f"{'='*80}")
    
    batch_tickers = remaining[:batch_size]
    
    # Estimate time for this batch
    time_estimate = len(batch_tickers) / num_workers * 0.3 / 60
    print(f"Estimated time: ~{time_estimate:.1f} minutes")
    
    # Split batch into worker chunks
    chunk_size = len(batch_tickers) // num_workers + 1
    chunks = [batch_tickers[i:i+chunk_size] for i in range(0, len(batch_tickers), chunk_size)]
    
    # Process in parallel
    print(f"\n🔍 Checking {len(batch_tickers)} tickers...")
    with Pool(num_workers) as pool:
        chunk_results = pool.map(quick_check_batch, chunks)
    
    # Flatten results
    batch_found = []
    for chunk_result in chunk_results:
        batch_found.extend(chunk_result)
    
    print(f"\n{'='*80}")
    print(f"✅ BATCH 1 COMPLETE!")
    print(f"{'='*80}")
    print(f"\n📊 Results:")
    print(f"   Found in this batch: {len(batch_found)} tickers")
    print(f"   Previously found: {len(found_tickers)} tickers")
    print(f"   Grand total: {len(found_tickers) + len(batch_found)} tickers")
    
    # Save checkpoint
    checkpoint_file = "/tmp/batch_checkpoint_1.txt"
    with open(checkpoint_file, 'w') as f:
        f.write('\n'.join(batch_found))
    print(f"\n💾 Checkpoint saved to {checkpoint_file}")
    
    # Update running total
    all_found = list(found_tickers) + batch_found
    with open('/tmp/tickers_with_data_updated.txt', 'w') as f:
        f.write('\n'.join(all_found))
    print(f"💾 Updated list saved to /tmp/tickers_with_data_updated.txt")
    
    print(f"\n📈 Progress:")
    print(f"   Checked: {batch_size}/{len(remaining)} remaining tickers")
    print(f"   ({batch_size/len(remaining)*100:.1f}% of remaining)")
    print(f"   Remaining: {len(remaining) - batch_size} tickers")
    
    print(f"\n✋ STOPPED after batch 1 - Review results before continuing")
    print("\n")

if __name__ == '__main__':
    main()
