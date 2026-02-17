#!/usr/bin/env python3
"""
Fetch and cache yfinance data for ALL tickers in the database.
This creates a complete local cache so backtests can run without internet.
"""

import json
import yfinance as yf
import time
from datetime import datetime
from multiprocessing import Pool
import threading

# Global progress counter with lock
progress_counter = 0
progress_lock = threading.Lock()
failed_tickers = []
failed_lock = threading.Lock()

def fetch_ticker_data(args):
    """Fetch historical data for a ticker with retry logic"""
    ticker, total = args
    global progress_counter, failed_tickers
    
    max_retries = 5
    result = None
    
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            history = stock.history(period='max')  # Get ENTIRE lifespan
            
            if not history.empty:
                # Convert to simple dict format for JSON storage
                result = {
                    'ticker': ticker,
                    'dates': [str(d.date()) for d in history.index],
                    'open': history['Open'].tolist(),
                    'high': history['High'].tolist(),
                    'low': history['Low'].tolist(),
                    'close': history['Close'].tolist(),
                    'volume': history['Volume'].tolist()
                }
                break  # Success
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(3)  # Longer wait before retry
            else:
                # Record failure
                with failed_lock:
                    failed_tickers.append({'ticker': ticker, 'error': str(e)})
    
    # Update progress
    with progress_lock:
        progress_counter += 1
        if progress_counter % 100 == 0 or progress_counter == total:
            print(f"\rProgress: {progress_counter}/{total} (Failed: {len(failed_tickers)})", end='', flush=True)
    
    return result

def main():
    """Fetch all tickers and create complete cache"""
    global progress_counter, failed_tickers
    
    print("=" * 80)
    print("YFINANCE DATA CACHING - ALL TICKERS - FULL LIFESPAN")
    print("=" * 80)
    
    # Load ALL tickers from database
    with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/expanded_insider_trades.json', 'r') as f:
        data = json.load(f)
    
    all_tickers = [item['ticker'] for item in data['data']]
    
    print(f"\n📊 Total tickers: {len(all_tickers):,}")
    print(f"📅 Date range: ENTIRE LIFESPAN (period='max')")
    print(f"⚙️  Workers: 4 (slower but more reliable)")
    print(f"⏱️  Estimated time: ~60 minutes (slow & steady wins)")
    print()
    
    # Reset counters
    progress_counter = 0
    failed_tickers = []
    
    # Fetch data
    print("🔄 Fetching all stock data (this will take a while)...")
    ticker_args = [(t, len(all_tickers)) for t in all_tickers]
    
    start_time = time.time()
    with Pool(4) as pool:  # Reduced from 8 to 4 workers
        results = pool.map(fetch_ticker_data, ticker_args)
    
    elapsed = time.time() - start_time
    print()  # New line after progress
    
    # Filter out None results
    successful_results = [r for r in results if r is not None]
    
    print(f"\n✅ Successfully fetched: {len(successful_results):,}/{len(all_tickers):,}")
    print(f"❌ Failed: {len(failed_tickers):,}")
    print(f"⏱️  Time elapsed: {elapsed/60:.1f} minutes")
    
    if failed_tickers:
        print(f"\n⚠️  Failed tickers ({len(failed_tickers)}):")
        for item in failed_tickers[:20]:
            print(f"  - {item['ticker']}: {item['error'][:60]}")
        if len(failed_tickers) > 20:
            print(f"  ... and {len(failed_tickers) - 20} more")
    
    # Save to file
    output_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/yfinance_cache_full.json'
    
    cache_data = {
        'metadata': {
            'created': datetime.now().isoformat(),
            'total_tickers': len(all_tickers),
            'successful': len(successful_results),
            'failed': len(failed_tickers),
            'date_range': 'entire_lifespan',
            'fetch_time_minutes': elapsed / 60
        },
        'data': {item['ticker']: item for item in successful_results}
    }
    
    print(f"\n💾 Saving to: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(cache_data, f)
    
    print(f"📦 File contains {len(successful_results):,} stocks")
    
    # Calculate success rate
    success_rate = (len(successful_results) / len(all_tickers)) * 100
    print(f"\n📊 Success rate: {success_rate:.1f}%")
    
    if success_rate > 95:
        print("✅ SUCCESS! Cache is complete and ready for backtesting!")
    elif success_rate > 90:
        print("⚠️  Cache is mostly complete - review failures but can proceed")
    else:
        print("❌ Too many failures - investigate before using cache")

if __name__ == "__main__":
    main()
