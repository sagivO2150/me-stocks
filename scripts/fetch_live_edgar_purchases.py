#!/usr/bin/env python3
"""
Live EDGAR Insider Purchases Tracker
=====================================
Fetches Form 4 filings from TODAY and identifies:
1. Large individual purchases (compared to 2-year history)
2. Shopping sprees (multiple insiders buying same stock today)

Prioritizes C-level, 10% owners, and clustered purchases.

Usage: python fetch_live_edgar_purchases.py [--days N]
"""

import requests
from bs4 import BeautifulSoup
import sys
import json
from datetime import datetime, timedelta
import time
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import subprocess

# SEC EDGAR Rate limits
RATE_LIMIT_DELAY = 0.08
MAX_WORKERS = 10

rate_limit_lock = threading.Lock()
last_request_time = [0]

HEADERS = {
    'User-Agent': 'Stock-Insider-Tracker/1.0 sagiv.oron@example.com',
    'Accept-Encoding': 'gzip, deflate',
    'Host': 'www.sec.gov'
}


def rate_limited_request(url, **kwargs):
    """Thread-safe rate-limited HTTP request"""
    with rate_limit_lock:
        elapsed = time.time() - last_request_time[0]
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        
        response = requests.get(url, headers=HEADERS, **kwargs)
        last_request_time[0] = time.time()
        return response


def get_company_info(cik):
    """Get company ticker and name from CIK"""
    try:
        # Try company tickers JSON
        response = rate_limited_request(
            'https://www.sec.gov/files/company_tickers.json',
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            cik_int = int(cik)
            for entry in data.values():
                if entry.get('cik_str') == cik_int:
                    ticker = entry.get('ticker', '')
                    # Normalize ticker (remove warrant/unit/rights suffixes)
                    ticker = normalize_ticker(ticker)
                    return ticker, entry.get('title', '')
    except Exception as e:
        print(f'Error fetching company info for CIK {cik}: {e}', file=sys.stderr)
    
    return '', ''


def normalize_ticker(ticker):
    """
    Normalize ticker by removing warrant/unit/rights suffixes.
    Examples: ENTXW -> ENTX, ABCDU -> ABCD, XYZR -> XYZ
    This matches how OpenInsider normalizes tickers.
    """
    if not ticker:
        return ticker
    
    ticker = ticker.upper()
    
    # Remove common suffixes (warrants, units, rights)
    # W = Warrants, U = Units (stock + warrant bundle), R = Rights
    if len(ticker) > 1 and ticker[-1] in ('W', 'U', 'R'):
        base_ticker = ticker[:-1]
        print(f'Normalized {ticker} -> {base_ticker}', file=sys.stderr)
        return base_ticker
    
    return ticker


def classify_role(title):
    """Classify insider role and calculate importance score"""
    title_lower = title.lower()
    
    # C-Level (highest priority)
    if 'cob' in title_lower or 'chairman' in title_lower:
        return 'COB', 10
    elif 'ceo' in title_lower or 'chief executive' in title_lower:
        return 'CEO', 10
    elif ('pres' in title_lower or 'president' in title_lower) and 'vp' not in title_lower:
        return 'Pres', 9
    elif 'cfo' in title_lower or 'chief financial' in title_lower:
        return 'CFO', 10
    elif 'coo' in title_lower or 'chief operating' in title_lower:
        return 'COO', 9
    elif 'gc' in title_lower or 'general counsel' in title_lower:
        return 'GC', 8
    
    # 10% Owner (high priority)
    elif '10%' in title_lower or 'beneficial owner' in title_lower:
        return '10% Owner', 9
    
    # Other roles
    elif 'vp' in title_lower or 'vice pres' in title_lower:
        return 'VP', 6
    elif 'director' in title_lower:
        return 'Director', 7
    else:
        return 'Other', 3


def parse_form4_xml(filing_url):
    """Parse a Form 4 filing and extract purchase transactions"""
    try:
        response = rate_limited_request(filing_url, timeout=30)
        content = response.text
        
        # Extract XML from the filing
        xml_match = re.search(r'<XML>(.*?)</XML>', content, re.DOTALL | re.IGNORECASE)
        if xml_match:
            xml_content = xml_match.group(1).strip()
        else:
            xml_match = re.search(r'(<\?xml.*?</ownershipDocument>)', content, re.DOTALL | re.IGNORECASE)
            if xml_match:
                xml_content = xml_match.group(1).strip()
            else:
                return None
        
        root = ET.fromstring(xml_content)
        
        # Extract issuer info (company being traded)
        issuer_cik = ''
        issuer = root.find('.//issuer')
        if issuer:
            cik_elem = issuer.find('issuerCik')
            if cik_elem is not None and cik_elem.text:
                issuer_cik = cik_elem.text.strip().zfill(10)
        
        if not issuer_cik:
            return None
        
        # Extract reporting owner info
        owner_name = 'Unknown'
        owner_title = 'Unknown'
        
        reporting_owner = root.find('.//reportingOwner')
        if reporting_owner:
            name_elem = reporting_owner.find('.//rptOwnerName')
            if name_elem is not None and name_elem.text:
                owner_name = name_elem.text
            
            relationship = reporting_owner.find('.//reportingOwnerRelationship')
            if relationship:
                officer_title = relationship.find('officerTitle')
                if officer_title is not None and officer_title.text:
                    owner_title = officer_title.text
                elif relationship.find('isDirector') is not None and relationship.find('isDirector').text == '1':
                    owner_title = 'Director'
                elif relationship.find('isTenPercentOwner') is not None and relationship.find('isTenPercentOwner').text == '1':
                    owner_title = '10% Owner'
        
        # Extract non-derivative purchase transactions only
        purchases = []
        
        for txn in root.findall('.//nonDerivativeTransaction'):
            txn_date_elem = txn.find('.//transactionDate/value')
            if txn_date_elem is None or not txn_date_elem.text:
                continue
            
            txn_code_elem = txn.find('.//transactionCoding/transactionCode')
            if txn_code_elem is None or not txn_code_elem.text:
                continue
            
            code = txn_code_elem.text.strip()
            
            # Only P (Purchase) transactions
            if code != 'P':
                continue
            
            shares_elem = txn.find('.//transactionAmounts/transactionShares/value')
            price_elem = txn.find('.//transactionAmounts/transactionPricePerShare/value')
            
            if shares_elem is None or price_elem is None:
                continue
            if not shares_elem.text or not price_elem.text:
                continue
            
            try:
                shares = float(shares_elem.text)
                price = float(price_elem.text)
                value = shares * price
                
                role, importance = classify_role(owner_title)
                
                purchases.append({
                    'date': txn_date_elem.text.strip(),
                    'shares': int(shares),
                    'value': value,
                    'price': price,
                    'insider_name': owner_name,
                    'title': owner_title,
                    'role': role,
                    'importance': importance,
                    'cik': issuer_cik
                })
            except (ValueError, TypeError):
                continue
        
        if purchases:
            return {
                'cik': issuer_cik,
                'purchases': purchases
            }
        
        return None
        
    except Exception as e:
        print(f'Error parsing Form 4 {filing_url}: {e}', file=sys.stderr)
        return None


def fetch_todays_form4s(days_back=0):
    """Fetch all Form 4 filings from recent days"""
    print(f'Fetching Form 4 filings from the last {days_back + 1} day(s)...', file=sys.stderr)
    
    # Calculate date range - use date only, not datetime
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    
    print(f'Date range: {start_date} to {end_date}', file=sys.stderr)
    
    all_filings = []
    
    # Fetch multiple pages sequentially (parallel caused timeouts)
    def fetch_page(start_index):
        url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&owner=include&count=100&start={start_index}'
        print(f'Fetching page starting at {start_index}...', file=sys.stderr)
        try:
            response = rate_limited_request(url, timeout=60)  # Increased timeout
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the table with "Form" header
            content_table = None
            for table in soup.find_all('table'):
                ths = table.find_all('th')
                if ths and any('Form' in th.text for th in ths):
                    content_table = table
                    break
            
            if not content_table:
                return []
            
            filings = []
            all_rows = content_table.find_all('tr')
            
            for row in all_rows[1:]:  # Skip header row
                tds = row.find_all('td', recursive=False)
                
                # Check if first column is "4" (Form 4)
                if not tds or tds[0].text.strip() != '4':
                    continue
                
                # Get filing date from column index 4 (0-indexed)
                filing_date_str = None
                if len(tds) > 4:
                    filing_date_str = tds[4].text.strip().split()[0]  # Get just date part
                elif len(tds) == 5:
                    # Sometimes the structure is slightly different
                    filing_date_str = tds[4].text.strip().split()[0]
                
                if not filing_date_str:
                    continue
                
                try:
                    filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d').date()
                    
                    # Only include filings from our date range
                    if filing_date < start_date:
                        continue
                    
                except (ValueError, IndexError):
                    continue
                
                # Get the filing URL from formats column (index 1)
                if len(tds) > 1:
                    links = tds[1].find_all('a')
                    for link in links:
                        if '[text]' in link.text.strip():
                            txt_url = 'https://www.sec.gov' + link.get('href', '')
                            if txt_url:
                                filings.append(txt_url)
                                break
            
            return filings
        except Exception as e:
            print(f'Error fetching page {start_index}: {e}', file=sys.stderr)
            return []
    
    # Fetch first 300 filings (3 pages) sequentially to avoid timeouts
    for start_index in range(0, 300, 100):
        print(f'Fetching page starting at {start_index}...', file=sys.stderr)
        page_filings = fetch_page(start_index)
        all_filings.extend(page_filings)
        time.sleep(0.5)  # Extra delay between pages
    
    print(f'Found {len(all_filings)} Form 4 filings', file=sys.stderr)
    return all_filings


def get_historical_purchases(ticker):
    """Fetch 2-year purchase history for a ticker using existing fetch_insider_trades"""
    try:
        script_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/scripts/fetch_insider_trades.py'
        result = subprocess.run(
            ['/Users/sagiv.oron/Documents/scripts_playground/stocks/.venv/bin/python', script_path, ticker],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get('success') and 'purchases' in data:
                return data['purchases']
    except Exception as e:
        print(f'Error fetching historical data for {ticker}: {e}', file=sys.stderr)
    
    return []


def calculate_purchase_score(purchase, historical_purchases):
    """
    Calculate how significant a purchase is compared to historical data
    Returns (score, percentile, is_large)
    """
    value = purchase['value']
    
    if not historical_purchases:
        # No history, use absolute value
        if value >= 1_000_000:
            return 10, 100, True
        elif value >= 500_000:
            return 8, 90, True
        elif value >= 250_000:
            return 6, 75, True
        else:
            return 3, 50, False
    
    # Compare to historical purchases
    historical_values = [p.get('value', 0) for p in historical_purchases if p.get('value')]
    if not historical_values:
        return 5, 50, False
    
    historical_values.sort()
    
    # Calculate percentile
    larger_count = sum(1 for v in historical_values if value > v)
    percentile = (larger_count / len(historical_values)) * 100
    
    # Score based on percentile and absolute value
    if percentile >= 95:
        score = 10
        is_large = True
    elif percentile >= 90:
        score = 9
        is_large = True
    elif percentile >= 75:
        score = 7
        is_large = True
    elif percentile >= 50:
        score = 5
        is_large = False
    else:
        score = 3
        is_large = False
    
    return score, percentile, is_large


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch live EDGAR insider purchases')
    parser.add_argument('--days', type=int, default=0, help='Look back N days (0 = today only)')
    args = parser.parse_args()
    
    # Fetch today's Form 4s
    filings = fetch_todays_form4s(days_back=args.days)
    
    if not filings:
        print(json.dumps({
            'success': False,
            'message': 'No Form 4 filings found'
        }))
        return
    
    # Parse all Form 4s in parallel
    print(f'Parsing {len(filings)} Form 4 filings...', file=sys.stderr)
    
    all_purchases = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(parse_form4_xml, url) for url in filings]
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    all_purchases.append(result)
            except Exception as e:
                print(f'Error processing filing: {e}', file=sys.stderr)
    
    print(f'Found {len(all_purchases)} filings with purchases', file=sys.stderr)
    
    # Group by CIK (company)
    by_company = defaultdict(lambda: {
        'cik': '',
        'ticker': '',
        'company_name': '',
        'purchases': [],
        'total_value': 0,
        'total_shares': 0,
        'unique_insiders': set(),
        'c_level_count': 0,
        'owner_count': 0
    })
    
    for filing in all_purchases:
        cik = filing['cik']
        for purchase in filing['purchases']:
            by_company[cik]['cik'] = cik
            by_company[cik]['purchases'].append(purchase)
            by_company[cik]['total_value'] += purchase['value']
            by_company[cik]['total_shares'] += purchase['shares']
            by_company[cik]['unique_insiders'].add(purchase['insider_name'])
            
            # Track high-importance roles
            if purchase['importance'] >= 9:
                if purchase['role'] in ['CEO', 'CFO', 'COB', 'COO', 'Pres']:
                    by_company[cik]['c_level_count'] += 1
                elif purchase['role'] == '10% Owner':
                    by_company[cik]['owner_count'] += 1
    
    # Get company tickers and calculate scores
    print('Enriching with company data and calculating scores...', file=sys.stderr)
    
    results = []
    
    for cik, data in by_company.items():
        # Get ticker and company name
        ticker, company_name = get_company_info(cik)
        
        if not ticker:
            continue  # Skip if we can't get ticker
        
        data['ticker'] = ticker
        data['company_name'] = company_name
        data['unique_insiders'] = len(data['unique_insiders'])
        
        # Fetch historical data for comparison
        historical = get_historical_purchases(ticker)
        
        # Score each purchase
        for purchase in data['purchases']:
            score, percentile, is_large = calculate_purchase_score(purchase, historical)
            purchase['score'] = score
            purchase['percentile'] = round(percentile, 1)
            purchase['is_large'] = is_large
        
        # Calculate cluster score (shopping spree indicator)
        cluster_score = 0
        
        # Multiple insiders = cluster
        if data['unique_insiders'] >= 5:
            cluster_score += 10
        elif data['unique_insiders'] >= 3:
            cluster_score += 8
        elif data['unique_insiders'] >= 2:
            cluster_score += 5
        
        # C-level activity
        if data['c_level_count'] >= 3:
            cluster_score += 10
        elif data['c_level_count'] >= 2:
            cluster_score += 7
        elif data['c_level_count'] >= 1:
            cluster_score += 4
        
        # 10% Owner activity
        if data['owner_count'] >= 2:
            cluster_score += 8
        elif data['owner_count'] >= 1:
            cluster_score += 5
        
        # Total value
        if data['total_value'] >= 10_000_000:
            cluster_score += 10
        elif data['total_value'] >= 5_000_000:
            cluster_score += 7
        elif data['total_value'] >= 1_000_000:
            cluster_score += 4
        
        data['cluster_score'] = min(cluster_score, 10)  # Cap at 10
        
        # Calculate priority score (overall)
        # Weighted: 60% cluster, 40% largest individual purchase
        largest_purchase_score = max([p['score'] for p in data['purchases']], default=0)
        priority_score = (data['cluster_score'] * 0.6) + (largest_purchase_score * 0.4)
        data['priority_score'] = round(priority_score, 1)
        
        # Format purchases for output
        formatted_purchases = []
        for p in data['purchases']:
            formatted_purchases.append({
                'insider_name': p['insider_name'],
                'title': p['title'],
                'role': p['role'],
                'shares': p['shares'],
                'value': p['value'],
                'price': round(p['price'], 2),
                'score': p['score'],
                'percentile': p['percentile'],
                'is_large': p['is_large'],
                'date': p['date']
            })
        
        results.append({
            'ticker': ticker,
            'company_name': company_name,
            'cik': cik,
            'total_purchases': len(data['purchases']),
            'total_value': data['total_value'],
            'total_shares': data['total_shares'],
            'unique_insiders': data['unique_insiders'],
            'c_level_count': data['c_level_count'],
            'owner_count': data['owner_count'],
            'cluster_score': data['cluster_score'],
            'priority_score': data['priority_score'],
            'purchases': formatted_purchases
        })
    
    # Sort by priority score (shopping sprees and large purchases float to top)
    results.sort(key=lambda x: x['priority_score'], reverse=True)
    
    print(f'Found {len(results)} stocks with insider purchases', file=sys.stderr)
    
    # Output JSON
    output = {
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'days_back': args.days,
        'total_companies': len(results),
        'total_filings': len(all_purchases),
        'companies': results
    }
    
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
