#!/usr/bin/env python3
"""
Fetch full 4-year purchase data for batch 1 tickers (980 tickers)
Shows progress and saves to JSON with correct column parsing
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
total_tickers = 0

def fetch_insider_trades_for_ticker(ticker):
    """
    Fetch full 4-year insider purchase trades for a single ticker.
    Returns same format as merged_insider_trades.json
    """
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
                    print(f"{counter}/{total_tickers}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'class': 'tinytable'})
        
        if not table:
            with counter_lock:
                counter += 1
                if counter % 50 == 0:
                    print(f"{counter}/{total_tickers}")
            return None
        
        rows = table.find_all('tr')[1:]  # Skip header
        
        if not rows:
            with counter_lock:
                counter += 1
                if counter % 50 == 0:
                    print(f"{counter}/{total_tickers}")
            return None
        
        purchases = []
        total_value = 0
        unique_insiders = set()
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 12:
                continue
            
            # Check if it's a purchase
            trade_type = cols[6].text.strip()
            if trade_type != 'P - Purchase':
                continue  # Skip sales
            
            # Extract trade details (FIXED COLUMNS)
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
                    print(f"{counter}/{total_tickers}")
            return None
        
        # Get company name from the page
        company_name = ticker  # Default
        try:
            company_header = soup.find('h3')
            if company_header:
                company_name = company_header.text.strip()
        except:
            pass
        
        # Update progress
        with counter_lock:
            counter += 1
            print(f"{counter}/{total_tickers} - ✓ {ticker}: {len(purchases)} purchases, ${total_value:,.0f}")
        
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
                print(f"{counter}/{total_tickers}")
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
    global counter, total_tickers
    
    print("\n" + "="*80)
    print("FETCH FULL 4-YEAR PURCHASE DATA - BATCH 1")
    print("="*80)
    
    # Load batch 1 tickers
    print("\n📂 Loading batch 1 tickers...")
    with open('/tmp/batch_1_tickers.txt', 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
    total_tickers = len(tickers)
    print(f"   Total tickers: {total_tickers}")
    
    num_workers = cpu_count()
    print(f"   Workers: {num_workers}")
    
    time_estimate = total_tickers / num_workers * 0.2 / 60
    print(f"   Estimated time: ~{time_estimate:.1f} minutes")
    
    print(f"\n📥 Fetching full 4-year purchase data...")
    print(f"0/{total_tickers}")
    
    # Split into batches
    batch_size = total_tickers // num_workers + 1
    batches = [tickers[i:i+batch_size] for i in range(0, total_tickers, batch_size)]
    
    # Process in parallel
    counter = 0
    with Pool(num_workers) as pool:
        batch_results = pool.map(fetch_batch, batches)
    
    # Flatten results
    all_results = []
    for batch in batch_results:
        all_results.extend(batch)
    
    # Count stats
    total_purchases = sum(r['total_purchases'] for r in all_results)
    total_value = sum(r['total_value'] for r in all_results)
    
    print(f"\n{'='*80}")
    print(f"✅ BATCH 1 DATA FETCH COMPLETE!")
    print(f"{'='*80}")
    print(f"\n📊 Results:")
    print(f"   Tickers with data: {len(all_results)}/{total_tickers}")
    print(f"   Total purchases: {total_purchases:,}")
    print(f"   Total value: ${total_value:,}")
    
    # Save to JSON
    output_file = "output CSVs/batch_1_insider_trades.json"
    output_data = {
        'data': all_results,
        'metadata': {
            'batch': 1,
            'total_tickers': len(all_results),
            'total_purchases': total_purchases,
            'total_value': total_value,
            'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'OpenInsider',
            'filter': 'Purchases only (last 4 years)',
            'tickers_in_batch': total_tickers,
            'tickers_with_data': len(all_results)
        }
    }
    
    print(f"\n💾 Saving to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✅ Saved successfully!")
    print(f"\nFile: {output_file}")
    print(f"Tickers: {len(all_results)}")
    print(f"Purchases: {total_purchases:,}")
    print(f"Total Value: ${total_value:,}")
    print("\n")

if __name__ == '__main__':
    main()
