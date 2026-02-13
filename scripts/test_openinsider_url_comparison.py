#!/usr/bin/env python3
"""
Test script to compare OpenInsider URL approaches:
1. Simple search URL: http://openinsider.com/search?q={ticker}
2. Extended screener URL with more parameters

Goal: Determine which approach provides more insider trading data
"""

import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime, timedelta
from collections import defaultdict


def fetch_simple_url(ticker):
    """Fetch using the simple search URL (current approach)"""
    url = f"http://openinsider.com/search?q={ticker}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        time.sleep(0.5)  # Rate limiting
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'class': 'tinytable'})
        
        if not table:
            return {'success': False, 'trades': 0, 'date_range': None}
        
        rows = table.find_all('tr')[1:]  # Skip header
        trades = []
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 8:
                continue
            
            try:
                trade_date_str = cols[2].text.strip()
                trade_type = cols[6].text.strip()
                
                # Only count purchases
                if 'P - Purchase' in trade_type:
                    trades.append(trade_date_str)
            except:
                continue
        
        date_range = None
        if trades:
            dates = sorted(trades)
            date_range = f"{dates[-1]} to {dates[0]}"
        
        return {
            'success': True,
            'trades': len(trades),
            'date_range': date_range,
            'earliest': dates[-1] if trades else None,
            'latest': dates[0] if trades else None
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e), 'trades': 0}


def fetch_extended_url(ticker, days_back=1461):
    """Fetch using the extended screener URL with more parameters
    
    Parameters:
    - ticker: Stock symbol
    - days_back: How many days to look back (1461 = ~4 years, default on extended URL)
    """
    url = f"http://openinsider.com/screener"
    params = {
        's': ticker,
        'fd': str(days_back),  # Filing days back
        'xp': '1',  # Exclude certain types
        # NOTE: removed 'xs': '1' which was filtering for sales instead of purchases
        # NOTE: removed SIC filters (sicl=100) which exclude funds like ASA
        'cnt': '1000',  # Max results
        'page': '1'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        time.sleep(0.5)  # Rate limiting
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'class': 'tinytable'})
        
        if not table:
            return {'success': False, 'trades': 0, 'date_range': None}
        
        rows = table.find_all('tr')[1:]  # Skip header
        trades = []
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 8:
                continue
            
            try:
                trade_date_str = cols[2].text.strip()
                trade_type = cols[6].text.strip()
                
                # Only count purchases
                if 'P - Purchase' in trade_type:
                    trades.append(trade_date_str)
            except:
                continue
        
        date_range = None
        if trades:
            dates = sorted(trades)
            date_range = f"{dates[-1]} to {dates[0]}"
        
        return {
            'success': True,
            'trades': len(trades),
            'date_range': date_range,
            'earliest': dates[-1] if trades else None,
            'latest': dates[0] if trades else None
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e), 'trades': 0}


def run_comparison_test():
    """Run comparison test on top monthly stocks"""
    
    # Load top monthly stocks
    with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/webapp-stocks/public/top_monthly_insider_trades.json', 'r') as f:
        data = json.load(f)
    
    # Get all tickers
    tickers = [item['ticker'] for item in data['data']]
    total_tickers = len(tickers)
    
    print(f"{'='*80}")
    print(f"OPENINSIDER URL COMPARISON TEST")
    print(f"{'='*80}")
    print(f"Testing {total_tickers} tickers from Top Monthly Insider Trades")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    results = {
        'simple': {'success': 0, 'failed': 0, 'total_trades': 0, 'details': []},
        'extended': {'success': 0, 'failed': 0, 'total_trades': 0, 'details': []}
    }
    
    comparison_data = []
    
    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{total_tickers}] Testing {ticker}...", end=' ')
        
        # Test simple URL
        simple_result = fetch_simple_url(ticker)
        
        # Test extended URL
        extended_result = fetch_extended_url(ticker)
        
        # Record results
        if simple_result['success']:
            results['simple']['success'] += 1
            results['simple']['total_trades'] += simple_result['trades']
        else:
            results['simple']['failed'] += 1
        
        if extended_result['success']:
            results['extended']['success'] += 1
            results['extended']['total_trades'] += extended_result['trades']
        else:
            results['extended']['failed'] += 1
        
        # Compare
        diff = extended_result['trades'] - simple_result['trades']
        comparison_data.append({
            'ticker': ticker,
            'simple_trades': simple_result['trades'],
            'extended_trades': extended_result['trades'],
            'difference': diff,
            'simple_date_range': simple_result.get('date_range'),
            'extended_date_range': extended_result.get('date_range')
        })
        
        status = "✓" if diff >= 0 else "⚠"
        print(f"{status} Simple: {simple_result['trades']} | Extended: {extended_result['trades']} | Diff: {diff:+d}")
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"SUMMARY RESULTS")
    print(f"{'='*80}\n")
    
    print(f"BASELINE (Simple URL):")
    print(f"  • Success: {results['simple']['success']}/{total_tickers} ({results['simple']['success']/total_tickers*100:.1f}%)")
    print(f"  • Failed: {results['simple']['failed']}/{total_tickers}")
    print(f"  • Total trades found: {results['simple']['total_trades']}")
    print(f"  • Avg trades per stock: {results['simple']['total_trades']/results['simple']['success']:.1f}")
    
    print(f"\nEXTENDED URL:")
    print(f"  • Success: {results['extended']['success']}/{total_tickers} ({results['extended']['success']/total_tickers*100:.1f}%)")
    print(f"  • Failed: {results['extended']['failed']}/{total_tickers}")
    print(f"  • Total trades found: {results['extended']['total_trades']}")
    print(f"  • Avg trades per stock: {results['extended']['total_trades']/results['extended']['success']:.1f}")
    
    print(f"\nCOMPARISON:")
    gained = sum(1 for c in comparison_data if c['difference'] > 0)
    lost = sum(1 for c in comparison_data if c['difference'] < 0)
    same = sum(1 for c in comparison_data if c['difference'] == 0)
    total_diff = results['extended']['total_trades'] - results['simple']['total_trades']
    
    print(f"  • Stocks with MORE data: {gained} ({gained/total_tickers*100:.1f}%)")
    print(f"  • Stocks with SAME data: {same} ({same/total_tickers*100:.1f}%)")
    print(f"  • Stocks with LESS data: {lost} ({lost/total_tickers*100:.1f}%)")
    print(f"  • Net difference: {total_diff:+d} trades ({total_diff/results['simple']['total_trades']*100:+.1f}%)")
    
    # Show biggest gainers
    print(f"\n{'='*80}")
    print(f"TOP 10 BIGGEST GAINERS (Extended URL found more data):")
    print(f"{'='*80}")
    gainers = sorted([c for c in comparison_data if c['difference'] > 0], 
                     key=lambda x: x['difference'], reverse=True)[:10]
    
    for item in gainers:
        print(f"  {item['ticker']:6s}: +{item['difference']:3d} trades "
              f"(Simple: {item['simple_trades']:3d} → Extended: {item['extended_trades']:3d})")
        if item['simple_date_range'] and item['extended_date_range']:
            print(f"           Simple range:   {item['simple_date_range']}")
            print(f"           Extended range: {item['extended_date_range']}")
    
    # Show biggest losers
    if lost > 0:
        print(f"\n{'='*80}")
        print(f"STOCKS WITH LESS DATA (Extended URL found less):")
        print(f"{'='*80}")
        losers = sorted([c for c in comparison_data if c['difference'] < 0], 
                       key=lambda x: x['difference'])[:10]
        
        for item in losers:
            print(f"  {item['ticker']:6s}: {item['difference']:3d} trades "
                  f"(Simple: {item['simple_trades']:3d} → Extended: {item['extended_trades']:3d})")
    
    # Recommendation
    print(f"\n{'='*80}")
    print(f"RECOMMENDATION:")
    print(f"{'='*80}")
    
    if total_diff > 0 and lost == 0:
        print(f"✓ SWITCH TO EXTENDED URL")
        print(f"  The extended URL provides {total_diff} MORE trades ({total_diff/results['simple']['total_trades']*100:+.1f}%)")
        print(f"  and NO data loss for any stocks.")
    elif total_diff > 0 and lost < 5:
        print(f"✓ CONSIDER EXTENDED URL")
        print(f"  The extended URL provides {total_diff} MORE trades overall ({total_diff/results['simple']['total_trades']*100:+.1f}%)")
        print(f"  but {lost} stocks have slightly less data. Review those cases.")
    elif total_diff > 0:
        print(f"⚠ MIXED RESULTS")
        print(f"  Extended URL has {total_diff} more trades overall but {lost} stocks lost data.")
        print(f"  Consider hybrid approach or investigate why some stocks have less data.")
    else:
        print(f"✗ STICK WITH SIMPLE URL")
        print(f"  Extended URL doesn't provide significant improvement.")
    
    print(f"\n{'='*80}\n")
    
    # Save detailed results
    output_file = f"/Users/sagiv.oron/Documents/scripts_playground/stocks/logs/url_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': results,
            'comparison': comparison_data
        }, f, indent=2)
    
    print(f"Detailed results saved to: {output_file}\n")


if __name__ == '__main__':
    run_comparison_test()
