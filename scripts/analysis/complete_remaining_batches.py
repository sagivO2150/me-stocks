#!/usr/bin/env python3
"""
Complete the remaining batches 2-4 and fetch full data
Shows clear progress: Batch X/4, Ticker Y/Z
"""

import json
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from multiprocessing import Pool, cpu_count
from threading import Lock

# Global progress tracking
counter = 0
counter_lock = Lock()
total_tickers = 0
current_batch = 0

def quick_check_has_purchases(ticker):
    """Quick check if ticker has ANY purchase trades in last 4 years"""
    global counter
    
    try:
        url = "http://openinsider.com/screener"
        params = {
            's': ticker.upper(),
            'fd': '1461',  # 4 YEARS
            'cnt': '10'
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
                        if trade_type == 'P - Purchase':
                            result = ticker
                            break
        
        with counter_lock:
            counter += 1
            if result:
                print(f"[Batch {current_batch}/4] {counter}/{total_tickers} - ✓ {ticker}")
            elif counter % 50 == 0:
                print(f"[Batch {current_batch}/4] {counter}/{total_tickers}")
        
        return result
        
    except Exception as e:
        with counter_lock:
            counter += 1
        return None

def check_batch(ticker_batch):
    """Check batch with 0.3s delays"""
    tickers_with_purchases = []
    for ticker in ticker_batch:
        result = quick_check_has_purchases(ticker)
        if result:
            tickers_with_purchases.append(ticker)
        time.sleep(0.3)
    return tickers_with_purchases

def fetch_insider_trades_for_ticker(ticker):
    """Fetch full 4-year purchase data"""
    global counter
    
    try:
        url = "http://openinsider.com/screener"
        params = {
            's': ticker.upper(),
            'fd': '1461',  # 4 YEARS
            'cnt': '1000',
            'page': '1'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            with counter_lock:
                counter += 1
                if counter % 50 == 0:
                    print(f"[Batch {current_batch}/4 - FETCH] {counter}/{total_tickers}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'class': 'tinytable'})
        
        if not table:
            with counter_lock:
                counter += 1
                if counter % 50 == 0:
                    print(f"[Batch {current_batch}/4 - FETCH] {counter}/{total_tickers}")
            return None
        
        rows = table.find_all('tr')[1:]
        
        if not rows:
            with counter_lock:
                counter += 1
                if counter % 50 == 0:
                    print(f"[Batch {current_batch}/4 - FETCH] {counter}/{total_tickers}")
            return None
        
        purchases = []
        total_value = 0
        unique_insiders = set()
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 12:
                continue
            
            trade_type = cols[6].text.strip()
            if trade_type != 'P - Purchase':
                continue
            
            try:
                filing_date = cols[1].text.strip()
                trade_date = cols[2].text.strip()
                insider_name = cols[4].text.strip()
                title = cols[5].text.strip()
                shares = cols[8].text.strip().replace(',', '')
                price = cols[7].text.strip().replace('$', '').replace(',', '')
                value = cols[11].text.strip().replace('$', '').replace(',', '').replace('+', '')
                
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
                    'value': f'+${value}',
                    'role': title
                })
                
                total_value += value_float
                unique_insiders.add(insider_name)
                
            except Exception as e:
                continue
        
        if not purchases:
            with counter_lock:
                counter += 1
                if counter % 50 == 0:
                    print(f"[Batch {current_batch}/4 - FETCH] {counter}/{total_tickers}")
            return None
        
        company_name = ticker
        try:
            company_header = soup.find('h3')
            if company_header:
                company_name = company_header.text.strip()
        except:
            pass
        
        with counter_lock:
            counter += 1
            print(f"[Batch {current_batch}/4 - FETCH] {counter}/{total_tickers} - ✓ {ticker}: {len(purchases)} purchases, ${total_value:,.0f}")
        
        return {
            'ticker': ticker.upper(),
            'company_name': company_name,
            'total_value': int(total_value),
            'total_purchases': len(purchases),
            'unique_insiders': len(unique_insiders),
            'trades': purchases
        }
        
    except Exception as e:
        with counter_lock:
            counter += 1
            if counter % 50 == 0:
                print(f"[Batch {current_batch}/4 - FETCH] {counter}/{total_tickers}")
        return None

def fetch_batch(ticker_batch):
    """Fetch batch with rate limiting"""
    results = []
    for ticker in ticker_batch:
        result = fetch_insider_trades_for_ticker(ticker)
        if result:
            results.append(result)
        time.sleep(0.2)
    return results

def main():
    global counter, total_tickers, current_batch
    
    print("\n" + "="*80)
    print("COMPLETE BATCHES 2-4: FIND TICKERS + FETCH FULL DATA")
    print("="*80)
    
    # Load ALL SEC tickers
    print("\n📂 Loading SEC company list...")
    with open('info/all_SEC_filing_companies.json', 'r') as f:
        all_tickers = [item['ticker'] for item in json.load(f).values()]
    print(f"   Total SEC companies: {len(all_tickers)}")
    
    # Define batches
    batches = [
        (2, 2500, 5000),
        (3, 5000, 7500),
        (4, 7500, len(all_tickers))
    ]
    
    num_workers = cpu_count()
    
    for batch_num, start_idx, end_idx in batches:
        current_batch = batch_num
        batch_tickers = all_tickers[start_idx:end_idx]
        
        print(f"\n{'='*80}")
        print(f"BATCH {batch_num}/4: Tickers {start_idx}-{end_idx} ({len(batch_tickers)} tickers)")
        print(f"{'='*80}")
        
        # PHASE 1: Quick check for purchases
        print(f"\n🔍 PHASE 1: Checking for purchases...")
        total_tickers = len(batch_tickers)
        counter = 0
        print(f"[Batch {batch_num}/4] 0/{total_tickers}")
        
        chunk_size = total_tickers // num_workers + 1
        chunks = [batch_tickers[i:i+chunk_size] for i in range(0, total_tickers, chunk_size)]
        
        with Pool(num_workers) as pool:
            chunk_results = pool.map(check_batch, chunks)
        
        found_tickers = []
        for chunk_result in chunk_results:
            found_tickers.extend(chunk_result)
        
        print(f"\n   Found: {len(found_tickers)} tickers with purchases")
        
        # Save checkpoint
        checkpoint_file = f"/tmp/batch_{batch_num}_tickers.txt"
        with open(checkpoint_file, 'w') as f:
            f.write('\n'.join(found_tickers))
        print(f"   Saved to: {checkpoint_file}")
        
        # PHASE 2: Fetch full data
        print(f"\n📥 PHASE 2: Fetching full 4-year data...")
        total_tickers = len(found_tickers)
        counter = 0
        print(f"[Batch {batch_num}/4 - FETCH] 0/{total_tickers}")
        
        chunk_size = total_tickers // num_workers + 1
        chunks = [found_tickers[i:i+chunk_size] for i in range(0, total_tickers, chunk_size)]
        
        with Pool(num_workers) as pool:
            batch_results = pool.map(fetch_batch, chunks)
        
        all_results = []
        for batch in batch_results:
            all_results.extend(batch)
        
        # Save results
        total_purchases = sum(r['total_purchases'] for r in all_results)
        total_value = sum(r['total_value'] for r in all_results)
        
        output_file = f"output CSVs/batch_{batch_num}_insider_trades.json"
        output_data = {
            'data': all_results,
            'metadata': {
                'batch': batch_num,
                'total_tickers': len(all_results),
                'total_purchases': total_purchases,
                'total_value': total_value,
                'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'OpenInsider',
                'filter': 'Purchases only (last 4 years)'
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n✅ Batch {batch_num} complete!")
        print(f"   Tickers: {len(all_results)}")
        print(f"   Purchases: {total_purchases:,}")
        print(f"   Value: ${total_value:,}")
        print(f"   Saved to: {output_file}\n")
    
    print("\n" + "="*80)
    print("✅ ALL BATCHES COMPLETE!")
    print("="*80)
    print("\nNext: Merge all 4 batches into final dataset\n")

if __name__ == '__main__':
    main()
