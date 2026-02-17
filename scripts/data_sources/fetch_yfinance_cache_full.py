#!/usr/bin/env python3
"""
Fetch and cache yfinance data for ALL remaining tickers (batches 2-5)
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
    
    max_retries = 3
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
                time.sleep(1)  # Wait before retry
            else:
                # Record failure
                with failed_lock:
                    failed_tickers.append({'ticker': ticker, 'error': str(e)})
    
    # Update progress
    with progress_lock:
        progress_counter += 1
        if progress_counter % 50 == 0 or progress_counter == total:
            print(f"\rProgress: {progress_counter}/{total} (Failed: {len(failed_tickers)})", end='', flush=True)
    
    return result

def main():
    """Main function to fetch remaining 80% and merge with batch 1"""
    global progress_counter, failed_tickers
    
    print("=" * 80)
    print("YFINANCE DATA CACHING - REMAINING 60% - FULL LIFESPAN")
    print("=" * 80)
    
    # Load ticker list
    with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/expanded_insider_trades.json', 'r') as f:
        data = json.load(f)
    
    all_tickers = [item['ticker'] for item in data['data']]
    
    # Load existing cache to find what's already done
    with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/yfinance_cache_full.json', 'r') as f:
        existing_cache = json.load(f)
    
    cached_tickers = set(existing_cache['data'].keys())
    remaining_tickers = [t for t in all_tickers if t not in cached_tickers]
    
    print(f"\n📊 Total tickers: {len(all_tickers)}")
    print(f"✅ Already cached: {len(cached_tickers)} tickers (40%)")
    print(f"📦 Remaining to fetch: {len(remaining_tickers)} tickers (60%)")
    print(f"📅 Date range: ENTIRE LIFESPAN (period='max')")
    print(f"⚙️  Workers: 8")
    print()
    
    # Reset counters
    progress_counter = 0
    failed_tickers = []
    
    # Fetch data
    print("🔄 Fetching remaining stock data...")
    ticker_args = [(t, len(remaining_tickers)) for t in remaining_tickers]
    
    with Pool(8) as pool:
        results = pool.map(fetch_ticker_data, ticker_args)
    
    print()  # New line after progress
    
    # Filter out None results
    successful_results = [r for r in results if r is not None]
    
    print(f"\n✅ Successfully fetched: {len(successful_results)}/{len(remaining_tickers)}")
    print(f"❌ Failed: {len(failed_tickers)}")
    
    if failed_tickers:
        print("\nFailed tickers:")
        for item in failed_tickers[:20]:
            print(f"  - {item['ticker']}: {item['error'][:50]}")
        if len(failed_tickers) > 20:
            print(f"  ... and {len(failed_tickers) - 20} more")
    
    # Load existing cache
    print("\n🔄 Merging with existing cache...")
    
    # Merge all data
    merged_data = existing_cache['data'].copy()
    for item in successful_results:
        merged_data[item['ticker']] = item
    
    # Save merged file
    output_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/yfinance_cache_full.json'
    
    cache_data = {
        'metadata': {
            'created': datetime.now().isoformat(),
            'total_tickers': len(all_tickers),
            'successful': len(merged_data),
            'failed': len(all_tickers) - len(merged_data),
            'date_range': 'entire_lifespan'
        },
        'data': merged_data
    }
    
    with open(output_file, 'w') as f:
        json.dump(cache_data, f)
    
    print(f"\n💾 Saved full cache to: {output_file}")
    print(f"📦 Total stocks in cache: {len(merged_data)}")
    
    # Calculate success rate
    success_rate = (len(merged_data) / len(all_tickers)) * 100
    print(f"\n📊 Overall success rate: {success_rate:.1f}%")
    print(f"✅ Cache is ready for local backtesting!")

if __name__ == "__main__":
    main()
