#!/usr/bin/env python3
"""
Fetch and cache yfinance data locally for all tickers
This eliminates rate limit issues during backtesting
"""

import json
import yfinance as yf
import time
from datetime import datetime
from multiprocessing import Pool, cpu_count
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
        if progress_counter % 10 == 0 or progress_counter == total:
            print(f"\rProgress: {progress_counter}/{total} (Failed: {len(failed_tickers)})", end='', flush=True)
    
    return result

def main():
    """Main function to fetch and cache yfinance data"""
    global progress_counter, failed_tickers
    
    print("=" * 80)
    print("YFINANCE DATA CACHING - BATCH 1 (10%) - FULL LIFESPAN")
    print("=" * 80)
    
    # Load ticker list
    with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/expanded_insider_trades.json', 'r') as f:
        data = json.load(f)
    
    all_tickers = [item['ticker'] for item in data['data']]
    
    # Take first 10% for batch 1
    batch_size = int(len(all_tickers) * 0.1)
    batch_tickers = all_tickers[:batch_size]
    
    print(f"\n📊 Total tickers: {len(all_tickers)}")
    print(f"📦 Batch 1 size: {len(batch_tickers)} tickers (10%)")
    print(f"📅 Date range: ENTIRE LIFESPAN (period='max')")
    print(f"⚙️  Workers: 8")
    print()
    
    # Reset counters
    progress_counter = 0
    failed_tickers = []
    
    # Fetch data
    print("🔄 Fetching stock data...")
    ticker_args = [(t, len(batch_tickers)) for t in batch_tickers]
    
    with Pool(8) as pool:
        results = pool.map(fetch_ticker_data, ticker_args)
    
    print()  # New line after progress
    
    # Filter out None results
    successful_results = [r for r in results if r is not None]
    
    print(f"\n✅ Successfully fetched: {len(successful_results)}/{len(batch_tickers)}")
    print(f"❌ Failed: {len(failed_tickers)}")
    
    if failed_tickers:
        print("\nFailed tickers:")
        for item in failed_tickers[:20]:  # Show first 20
            print(f"  - {item['ticker']}: {item['error'][:50]}")
        if len(failed_tickers) > 20:
            print(f"  ... and {len(failed_tickers) - 20} more")
    
    # Save to file
    output_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/yfinance_cache_batch1.json'
    
    cache_data = {
        'metadata': {
            'created': datetime.now().isoformat(),
            'total_tickers': len(batch_tickers),
            'successful': len(successful_results),
            'failed': len(failed_tickers),
            'date_range': 'entire_lifespan'
        },
        'data': {item['ticker']: item for item in successful_results}
    }
    
    with open(output_file, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"\n💾 Saved to: {output_file}")
    print(f"📦 File contains {len(successful_results)} stocks")
    
    # Calculate success rate
    success_rate = (len(successful_results) / len(batch_tickers)) * 100
    print(f"\n📊 Success rate: {success_rate:.1f}%")
    
    if success_rate > 95:
        print("✅ Success rate is excellent! Ready to fetch remaining 80%")
    elif success_rate > 90:
        print("⚠️  Success rate is good, but review failures before proceeding")
    else:
        print("❌ Success rate is low - investigate failures before continuing")

if __name__ == "__main__":
    main()
