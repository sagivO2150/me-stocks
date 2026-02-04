#!/usr/bin/env python3
"""
Top Monthly Insider Trades Scraper
Scrapes both:
- http://openinsider.com/top-officer-purchases-of-the-month
- http://openinsider.com/top-insider-purchases-of-the-month
And aggregates data by ticker to show the most actively traded stocks
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from collections import defaultdict
import time

def scrape_top_monthly_page(url):
    """
    Scrape a top monthly purchases page from OpenInsider
    
    Returns:
    - List of trades with ticker, insider info, trade count, and value
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        print(f"Fetching {url}...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'class': 'tinytable'})
        
        if not table:
            print(f"No table found on {url}")
            return []
        
        trades = []
        rows = table.find_all('tr')[1:]  # Skip header
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 11:
                continue
            
            # Parse columns
            # X | Filing Date | Trade Date | Ticker | Company | Insider Name | Title | Trade Type | Price | Qty | Owned | ΔOwn% | Value
            trade = {
                'ticker': cols[3].text.strip(),
                'company_name': cols[4].text.strip(),
                'insider_name': cols[5].text.strip(),
                'title': cols[6].text.strip(),
                'trade_type': cols[7].text.strip(),
                'trade_date': cols[2].text.strip(),
                'filing_date': cols[1].text.strip(),
                'price': cols[8].text.strip(),
                'qty': cols[9].text.strip(),
                'owned': cols[10].text.strip() if len(cols) > 10 else '',
                'delta_own': cols[11].text.strip() if len(cols) > 11 else '',
                'value': cols[12].text.strip() if len(cols) > 12 else ''
            }
            
            trades.append(trade)
        
        print(f"Found {len(trades)} trades on this page")
        return trades
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []


def classify_role(title):
    """Classify insider role from title"""
    title_lower = title.lower()
    
    if 'cob' in title_lower or 'chairman' in title_lower:
        return 'COB'
    elif 'ceo' in title_lower or 'chief executive' in title_lower:
        return 'CEO'
    elif ('pres' in title_lower or 'president' in title_lower) and 'vp' not in title_lower and 'vice' not in title_lower:
        return 'Pres'
    elif 'cfo' in title_lower or 'chief financial' in title_lower:
        return 'CFO'
    elif 'coo' in title_lower or 'chief operating' in title_lower:
        return 'COO'
    elif 'gc' in title_lower or 'general counsel' in title_lower or 'chief legal' in title_lower:
        return 'GC'
    elif 'vp' in title_lower or 'vice pres' in title_lower or 'v.p.' in title_lower:
        return 'VP'
    elif 'director' in title_lower and 'chief' not in title_lower:
        return 'Director'
    elif '10%' in title_lower or 'beneficial owner' in title_lower:
        return '10% Owner'
    else:
        return 'Other'


def parse_value(value_str):
    """Convert value string like '$1,234,567' or '$1.23M' to float"""
    try:
        # Remove $ and commas
        clean = value_str.replace('$', '').replace(',', '').strip()
        
        # Handle M (millions) and K (thousands)
        if 'M' in clean.upper():
            return float(clean.replace('M', '').replace('m', '')) * 1_000_000
        elif 'K' in clean.upper():
            return float(clean.replace('K', '').replace('k', '')) * 1_000
        elif clean:
            return float(clean)
        else:
            return 0
    except:
        return 0


def aggregate_by_ticker(all_trades):
    """
    Aggregate trades by ticker to show total activity
    
    Returns:
    - List of aggregated ticker data with counts and values
    """
    ticker_data = defaultdict(lambda: {
        'ticker': '',
        'company_name': '',
        'total_value': 0,
        'total_purchases': 0,
        'unique_insiders': set(),
        'role_counts': defaultdict(int),
        'trades': []
    })
    
    for trade in all_trades:
        ticker = trade['ticker']
        
        # Skip if no ticker
        if not ticker:
            continue
        
        # Update aggregated data
        data = ticker_data[ticker]
        data['ticker'] = ticker
        data['company_name'] = trade['company_name']
        data['total_value'] += parse_value(trade['value'])
        data['total_purchases'] += 1
        data['unique_insiders'].add(trade['insider_name'])
        
        # Classify and count role
        role = classify_role(trade['title'])
        data['role_counts'][role] += 1
        
        # Store trade details
        data['trades'].append({
            'insider_name': trade['insider_name'],
            'title': trade['title'],
            'role': role,
            'trade_date': trade['trade_date'],
            'value': trade['value'],
            'qty': trade['qty']
        })
    
    # Convert to list and sort by total value
    result = []
    for ticker, data in ticker_data.items():
        result.append({
            'ticker': data['ticker'],
            'company_name': data['company_name'],
            'total_value': data['total_value'],
            'total_value_formatted': format_value(data['total_value']),
            'total_purchases': data['total_purchases'],
            'unique_insiders': len(data['unique_insiders']),
            'role_counts': dict(data['role_counts']),
            'trades': data['trades']
        })
    
    # Sort by total value descending
    result.sort(key=lambda x: x['total_value'], reverse=True)
    
    return result


def format_value(value):
    """Format value as $XM or $XK"""
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.0f}K"
    else:
        return f"${value:.0f}"


def main():
    """Main execution"""
    print("=" * 80)
    print("🔍 SCRAPING TOP MONTHLY INSIDER TRADING ACTIVITY")
    print("=" * 80)
    
    # URLs to scrape
    urls = [
        'http://openinsider.com/top-officer-purchases-of-the-month',
        'http://openinsider.com/top-insider-purchases-of-the-month'
    ]
    
    all_trades = []
    
    # Scrape both pages
    for url in urls:
        trades = scrape_top_monthly_page(url)
        all_trades.extend(trades)
        time.sleep(1)  # Be polite to the server
    
    print(f"\n📊 Total trades collected: {len(all_trades)}")
    
    # Aggregate by ticker
    print("\n🔄 Aggregating trades by ticker...")
    aggregated = aggregate_by_ticker(all_trades)
    
    print(f"✅ Found {len(aggregated)} unique tickers with insider activity")
    
    # Save to JSON file
    import os
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output CSVs')
    output_file = os.path.join(output_dir, 'top_monthly_insider_trades.json')
    
    output_data = {
        'updated_at': datetime.now().isoformat(),
        'total_tickers': len(aggregated),
        'total_trades': len(all_trades),
        'data': aggregated[:50]  # Top 50 tickers
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n💾 Saved to {output_file}")
    
    # Print top 10
    print("\n" + "=" * 80)
    print("📈 TOP 10 STOCKS BY INSIDER TRADING VOLUME (PAST MONTH)")
    print("=" * 80)
    
    for i, stock in enumerate(aggregated[:10], 1):
        print(f"\n{i}. {stock['ticker']} - {stock['company_name']}")
        print(f"   💰 Total Value: {stock['total_value_formatted']}")
        print(f"   📊 Purchases: {stock['total_purchases']}")
        print(f"   👥 Unique Insiders: {stock['unique_insiders']}")
        
        # Show role breakdown
        roles = []
        for role, count in stock['role_counts'].items():
            roles.append(f"{count} {role}{'s' if count > 1 and role not in ['COB', 'CEO', 'Pres', 'CFO', 'COO', 'GC'] else ''}")
        print(f"   🎯 Roles: {', '.join(roles)}")
    
    print("\n" + "=" * 80)
    print("✅ COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
