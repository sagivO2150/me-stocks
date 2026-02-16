#!/usr/bin/env python3
"""
Build expanded dataset FROM SCRATCH - Batch 1 of 4
Checks first 2,500 SEC tickers for insider PURCHASES (last 4 years)
Shows clear progress: 1/2500, 2/2500, etc.
"""

import json
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from multiprocessing import Pool, cpu_count
from threading import Lock

# Global counter and lock for progress tracking
counter = 0
counter_lock = Lock()
total_in_batch = 2500

def quick_check_has_purchases(ticker):
    """Quick check if ticker has ANY purchase trades in last 4 years"""
    global counter
    
    try:
        url = "http://openinsider.com/screener"
        params = {
            's': ticker.upper(),
            'fd': '1461',  # 4 YEARS - exactly like fetch_insider_trades.py
            'cnt': '10'    # Just check if ANY exist
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        result = None
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'class': 'tinytable'})
            
            if table:
                rows = table.find_all('tr')[1:]
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 7:
                        trade_type = cols[6].text.strip()
                        if trade_type == 'P - Purchase':  # PURCHASES ONLY
                            result = ticker
                            break
        
        # Update progress counter
        with counter_lock:
            counter += 1
            if result:
                print(f"{counter}/{total_in_batch} - ✓ {ticker}")
            elif counter % 50 == 0:  # Show progress every 50 tickers
                print(f"{counter}/{total_in_batch}")
        
        return result
        
    except Exception as e:
        with counter_lock:
            counter += 1
        return None

def check_batch(ticker_batch):
    """Check a batch of tickers with 0.3s delays"""
    tickers_with_purchases = []
    for ticker in ticker_batch:
        result = quick_check_has_purchases(ticker)
        if result:
            tickers_with_purchases.append(ticker)
        time.sleep(0.3)  # Rate limiting
    return tickers_with_purchases

def main():
    global counter, total_in_batch
    
    print("\n" + "="*80)
    print("BUILD EXPANDED DATASET - STARTING FROM SCRATCH")
    print("BATCH 1 OF 4: First 2,500 tickers")
    print("="*80)
    
    # Load ALL SEC tickers
    print("\n📂 Loading SEC company list...")
    with open('info/all_SEC_filing_companies.json', 'r') as f:
        sec_data = json.load(f)
        all_tickers = [item['ticker'] for item in sec_data.values()]
    print(f"   Total SEC companies: {len(all_tickers)}")
    
    # Take first 2,500 for batch 1
    batch_tickers = all_tickers[:2500]
    total_in_batch = len(batch_tickers)
    
    print(f"\n⚙️  Batch 1 setup:")
    print(f"   Checking: {total_in_batch} tickers")
    print(f"   Time range: 4 years (fd=1461)")
    print(f"   Filter: Purchases only (P - Purchase)")
    
    num_workers = cpu_count()
    print(f"   Workers: {num_workers}")
    
    time_estimate = total_in_batch / num_workers * 0.3 / 60
    print(f"   Estimated time: ~{time_estimate:.1f} minutes")
    
    print(f"\n🔍 Checking tickers (showing progress every 50)...")
    print(f"0/{total_in_batch}")
    
    # Split into worker chunks
    chunk_size = total_in_batch // num_workers + 1
    chunks = [batch_tickers[i:i+chunk_size] for i in range(0, total_in_batch, chunk_size)]
    
    # Process in parallel
    counter = 0
    with Pool(num_workers) as pool:
        chunk_results = pool.map(check_batch, chunks)
    
    # Flatten results
    found_tickers = []
    for chunk_result in chunk_results:
        found_tickers.extend(chunk_result)
    
    print(f"\n{'='*80}")
    print(f"✅ BATCH 1 COMPLETE!")
    print(f"{'='*80}")
    print(f"\n📊 Results:")
    print(f"   Tickers checked: {total_in_batch}")
    print(f"   Tickers with purchases: {len(found_tickers)}")
    print(f"   Coverage: {len(found_tickers)/total_in_batch*100:.1f}%")
    
    # Save results
    checkpoint_file = "/tmp/batch_1_tickers.txt"
    with open(checkpoint_file, 'w') as f:
        f.write('\n'.join(found_tickers))
    print(f"\n💾 Saved to: {checkpoint_file}")
    
    # Show some examples
    if found_tickers:
        print(f"\n📋 Examples found: {', '.join(found_tickers[:10])}")
        if len(found_tickers) > 10:
            print(f"   ... and {len(found_tickers) - 10} more")
    
    print(f"\n✋ STOPPED - Review results before running batch 2")
    print("\n")

if __name__ == '__main__':
    main()
