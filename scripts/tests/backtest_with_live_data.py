#!/usr/bin/env python3
"""
Re-run backtest using LIVE OpenInsider data from the webapp
This ensures we capture ALL insider trades, not just what's in the monthly JSON
"""

import requests
import pandas as pd
from datetime import datetime
import sys
sys.path.append('/Users/sagiv.oron/Documents/scripts_playground/stocks/scripts/tests')
from backtest_card_counting_strategy import backtest_card_counting_strategy

def fetch_insider_trades_for_ticker(ticker):
    """Fetch insider trades from the webapp API"""
    try:
        response = requests.get(f'http://localhost:3001/api/insider-trades/{ticker}')
        data = response.json()
        if data['success']:
            return data['purchases']
        return []
    except:
        return []

def create_json_format_for_backtest(tickers):
    """Create the JSON structure expected by the backtest script"""
    all_stocks = []
    
    for ticker in tickers:
        print(f"Fetching insider data for {ticker}...")
        purchases = fetch_insider_trades_for_ticker(ticker)
        
        if not purchases:
            print(f"  ⚠️  No purchases found for {ticker}")
            continue
        
        # Convert to the format expected by backtest
        trades = []
        total_value = 0
        
        for purchase in purchases:
            # Format value as string with + prefix like OpenInsider data
            value_formatted = f"+${purchase['value']:,.0f}"
            trade = {
                'trade_date': purchase['date'],
                'insider_name': purchase['insider_name'],
                'title': purchase.get('title', ''),
                'shares': purchase['shares'],
                'value': value_formatted
            }
            trades.append(trade)
            total_value += purchase['value']
        
        stock_data = {
            'ticker': ticker,
            'company_name': f"{ticker} Company",  # We'd need to fetch this separately
            'total_value': total_value,
            'total_purchases': len(trades),
            'unique_insiders': len(set(t['insider_name'] for t in trades)),
            'trades': sorted(trades, key=lambda x: x['trade_date'])
        }
        
        all_stocks.append(stock_data)
        print(f"  ✅ Found {len(trades)} trades totaling ${total_value:,.0f}")
    
    return all_stocks

def run_backtest_on_ticker(ticker, initial_position_size=1000):
    """Run the card counting backtest on a single ticker with live data"""
    print(f"\n{'='*80}")
    print(f"BACKTESTING {ticker} WITH LIVE OPENINSIDER DATA")
    print(f"{'='*80}\n")
    
    # Fetch live data
    stocks = create_json_format_for_backtest([ticker])
    
    if not stocks:
        print(f"❌ No data found for {ticker}")
        return
    
    # Create temporary JSON file in the format expected by backtest
    import json
    import tempfile
    
    json_data = {
        'updated_at': datetime.now().isoformat(),
        'total_tickers': len(stocks),
        'total_trades': sum(s['total_purchases'] for s in stocks),
        'data': stocks
    }
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(json_data, temp_file)
    temp_file.close()
    
    # Run backtest
    results = backtest_card_counting_strategy(
        json_file=temp_file.name,
        initial_position_size=initial_position_size,
        base_adjustment=0.10
    )
    
    # Clean up
    import os
    os.unlink(temp_file.name)
    
    return results

if __name__ == '__main__':
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'UAA'
    initial_size = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    
    results = run_backtest_on_ticker(ticker, initial_size)
    
    if results:
        # Save results
        import csv
        output_file = f'/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_{ticker}_live_results.csv'
        
        all_fields = set()
        for result in results:
            all_fields.update(result.keys())
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(all_fields))
            writer.writeheader()
            writer.writerows(results)
        
        print(f"\n✅ Results saved to: {output_file}")
        print(f"📊 Total trades: {len(results)}")
