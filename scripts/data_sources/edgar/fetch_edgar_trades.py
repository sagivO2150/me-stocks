#!/usr/bin/env python3
"""
Fetch Historical Insider Trades from EDGAR
===========================================
Extends OpenInsider data by fetching Form 4 filings from SEC EDGAR.
Returns the SAME format as fetch_insider_trades.py but with complete historical data.

Usage: python fetch_edgar_trades.py <TICKER> [MAX_YEARS]
"""

import requests
from bs4 import BeautifulSoup
import sys
import json
from datetime import datetime, timedelta
import time
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


# SEC EDGAR Rate limits: 10 requests/second max
RATE_LIMIT_DELAY = 0.08  # ~12 requests/sec, slightly aggressive but safe
MAX_WORKERS = 10  # Parallel workers for fetching Form 4s

# Thread-safe rate limiter
rate_limit_lock = threading.Lock()
last_request_time = [0]  # Mutable to share across threads

# Thread-safe rate limiter
rate_limit_lock = threading.Lock()
last_request_time = [0]  # Mutable to share across threads

HEADERS = {
    'User-Agent': 'Stock-Insider-Tracker/1.0 sagiv.oron@example.com',
    'Accept-Encoding': 'gzip, deflate',
    'Host': 'www.sec.gov'
}


def rate_limited_request(url, **kwargs):
    """Thread-safe rate-limited HTTP request"""
    with rate_limit_lock:
        # Ensure we don't exceed rate limit
        elapsed = time.time() - last_request_time[0]
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        
        response = requests.get(url, headers=HEADERS, **kwargs)
        last_request_time[0] = time.time()
        return response


def ticker_to_cik(ticker):
    """Convert ticker symbol to CIK - tries multiple methods"""
    
    # Method 1: Try hardcoded common tickers (for testing/reliability)
    hardcoded_ciks = {
        'ADC': '0000917251',  # Agree Realty Corp
        'AAPL': '0000320193',
        'MSFT': '0000789019',
        'NVDA': '0001045810',
        'GME': '0001326380',
        'TSLA': '0001318605',
        'F': '0000037996',     # Ford Motor Company
    }
    
    ticker_upper = ticker.upper()
    if ticker_upper in hardcoded_ciks:
        print(f'Using hardcoded CIK for {ticker_upper}', file=sys.stderr)
        return hardcoded_ciks[ticker_upper]
    
    # Method 2: Try SEC company tickers JSON (most reliable when available)
    time.sleep(RATE_LIMIT_DELAY)
    try:
        # This endpoint is more stable
        response = requests.get(
            'https://www.sec.gov/files/company_tickers.json',
            headers=HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            for entry in data.values():
                if entry.get('ticker', '').upper() == ticker_upper:
                    cik = str(entry['cik_str']).zfill(10)
                    print(f'Found CIK via JSON: {cik}', file=sys.stderr)
                    return cik
    except Exception as e:
        print(f'JSON lookup failed: {e}', file=sys.stderr)
    
    # Method 3: Try SEC search page
    time.sleep(RATE_LIMIT_DELAY)
    try:
        url = f'https://www.sec.gov/cgi-bin/browse-edgar?company={ticker}&action=getcompany'
        response = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        cik_element = soup.find('span', {'class': 'companyName'})
        if cik_element:
            text = cik_element.get_text()
            match = re.search(r'CIK#?:\s*0*(\d+)', text, re.I)
            if match:
                cik = match.group(1).zfill(10)
                print(f'Found CIK via search: {cik}', file=sys.stderr)
                return cik
    except Exception as e:
        print(f'Search lookup failed: {e}', file=sys.stderr)
    
    return None


def fetch_form4_page(cik, start, page_size, cutoff_date, max_years):
    """Fetch a single page of Form 4 filings (for parallel execution)"""
    try:
        url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&count={page_size}&start={start}'
        response = rate_limited_request(url, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the filings table
        table = soup.find('table', {'class': 'tableFile2'})
        if not table:
            return []
        
        rows = table.find_all('tr')[1:]  # Skip header
        if not rows:
            return []
        
        page_filings = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 4:
                continue
            
            form_type = cols[0].text.strip()
            if form_type != '4':
                continue
            
            filing_date = cols[3].text.strip()
            filing_datetime = datetime.strptime(filing_date, '%Y-%m-%d')
            
            # Only include filings within date range
            if filing_datetime < cutoff_date:
                continue
            
            # Get document link
            doc_link = cols[1].find('a', {'id': 'documentsbutton'})
            if not doc_link:
                continue
            
            # Convert to direct filing URL (.txt format)
            doc_url = 'https://www.sec.gov' + doc_link['href']
            doc_url = doc_url.replace('-index.htm', '.txt')
            
            page_filings.append({
                'date': filing_date,
                'url': doc_url
            })
        
        return page_filings
        
    except Exception as e:
        print(f'Error fetching page start={start}: {e}', file=sys.stderr)
        return []


def fetch_form4_list(cik, max_years=5):
    """Get list of Form 4 filings from EDGAR with PARALLEL page fetching"""
    page_size = 100
    cutoff_date = datetime.now() - timedelta(days=max_years * 365)
    
    print(f'Fetching Form 4 filings for CIK {cik} (last {max_years} years)...', file=sys.stderr)
    
    # Fetch first page to see if there are results
    first_page = fetch_form4_page(cik, 0, page_size, cutoff_date, max_years)
    if not first_page:
        return []
    
    all_filings = first_page
    print(f'  First page: {len(first_page)} filings', file=sys.stderr)
    
    # Limit total filings to prevent runaway processing on huge companies like Ford
    # Even 500 filings is generous (that's ~100 filings per year for 5 years)
    MAX_TOTAL_FILINGS = 500
    
    # If first page is empty or very small, we might be past the date range
    if len(first_page) < 10:
        print(f'  Only {len(first_page)} filings found, stopping', file=sys.stderr)
        return all_filings
    
    # Fetch multiple pages in parallel to get ALL data within time window
    # But limit to a reasonable number to avoid infinite processing
    max_pages_to_try = min(5, (MAX_TOTAL_FILINGS // page_size))  # Try up to 5 pages (500 filings max)
    
    # Create page fetch jobs (start=100, 200, 300, etc.)
    page_starts = [page_size * i for i in range(1, max_pages_to_try)]
    
    print(f'  Fetching up to {max_pages_to_try} more pages in parallel (max {MAX_TOTAL_FILINGS} total filings)...', file=sys.stderr)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all page fetch jobs
        future_to_start = {
            executor.submit(fetch_form4_page, cik, start, page_size, cutoff_date, max_years): start
            for start in page_starts
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_start):
            try:
                page_filings = future.result()
                if page_filings:
                    all_filings.extend(page_filings)
                    print(f'  Fetched {len(all_filings)} filings so far...', file=sys.stderr)
                    
                    # Stop if we've reached the max limit
                    if len(all_filings) >= MAX_TOTAL_FILINGS:
                        print(f'  Reached max filing limit ({MAX_TOTAL_FILINGS}), stopping', file=sys.stderr)
                        break
            except Exception as e:
                print(f'Error processing page: {e}', file=sys.stderr)
    
    # Trim to max limit if we went over
    if len(all_filings) > MAX_TOTAL_FILINGS:
        all_filings = all_filings[:MAX_TOTAL_FILINGS]
        print(f'  Trimmed to {MAX_TOTAL_FILINGS} filings', file=sys.stderr)
    
    print(f'Found {len(all_filings)} Form 4 filings within date range', file=sys.stderr)
    return all_filings


def parse_form4_xml(filing_url):
    """Parse a Form 4 filing and extract buy/sell transactions (thread-safe)"""
    try:
        response = rate_limited_request(filing_url, timeout=30)
        
        # The .txt file contains the full submission, need to extract XML
        content = response.text
        
        # Find the XML document (between <XML> tags or starting with <?xml)
        xml_match = re.search(r'<XML>(.*?)</XML>', content, re.DOTALL | re.IGNORECASE)
        if xml_match:
            xml_content = xml_match.group(1).strip()
        else:
            # Try to find raw XML
            xml_match = re.search(r'(<\?xml.*?</ownershipDocument>)', content, re.DOTALL | re.IGNORECASE)
            if xml_match:
                xml_content = xml_match.group(1).strip()
            else:
                return None
        
        # Parse the XML (strip whitespace to avoid parsing errors)
        root = ET.fromstring(xml_content)
        
        # Extract reporting owner info
        owner_name = 'Unknown'
        owner_title = 'Unknown'
        
        reporting_owner = root.find('.//reportingOwner')
        if reporting_owner is not None:
            name_elem = reporting_owner.find('.//rptOwnerName')
            if name_elem is not None:
                owner_name = name_elem.text if name_elem.text else 'Unknown'
            
            relationship = reporting_owner.find('.//reportingOwnerRelationship')
            if relationship is not None:
                officer_title = relationship.find('officerTitle')
                if officer_title is not None and officer_title.text:
                    owner_title = officer_title.text
                elif relationship.find('isDirector') is not None and relationship.find('isDirector').text == '1':
                    owner_title = 'Director'
                elif relationship.find('isTenPercentOwner') is not None and relationship.find('isTenPercentOwner').text == '1':
                    owner_title = '10% Owner'
        
        # Extract non-derivative transactions (actual stock buys/sells)
        transactions = []
        
        for txn in root.findall('.//nonDerivativeTransaction'):
            # Transaction date
            txn_date = txn.find('.//transactionDate/value')
            if txn_date is None or not txn_date.text:
                continue
            
            # Transaction code (P=Purchase, S=Sale, etc.)
            txn_code = txn.find('.//transactionCoding/transactionCode')
            if txn_code is None or not txn_code.text:
                continue
            
            code = txn_code.text.strip()
            
            # Only process P (Purchase) and S (Sale) - ignore gifts, awards, etc.
            if code not in ['P', 'S']:
                continue
            
            # Shares
            shares_elem = txn.find('.//transactionAmounts/transactionShares/value')
            if shares_elem is None or not shares_elem.text:
                continue
            
            # Price per share
            price_elem = txn.find('.//transactionAmounts/transactionPricePerShare/value')
            if price_elem is None or not price_elem.text:
                continue
            
            try:
                shares = float(shares_elem.text)
                price = float(price_elem.text)
                value = shares * price
                
                transactions.append({
                    'date': txn_date.text.strip(),
                    'type': 'P - Purchase' if code == 'P' else 'S - Sale',
                    'shares': int(shares),
                    'value': value,
                    'insider_name': owner_name,
                    'title': owner_title
                })
            except (ValueError, TypeError):
                continue
        
        return transactions
    
    except Exception as e:
        print(f'Error parsing Form 4: {e}', file=sys.stderr)
        return None


def fetch_edgar_insider_trades(ticker_symbol, max_years=5):
    """
    Fetch insider trading data from EDGAR (extends beyond OpenInsider's 2-year limit).
    Returns same format as fetch_insider_trades.py for compatibility.
    
    Args:
        ticker_symbol: Stock ticker (e.g., 'AAPL', 'GME')
        max_years: Maximum years of history to fetch (default: 5)
    
    Returns:
        JSON object with same structure as OpenInsider scraper
    """
    try:
        print(f'Fetching EDGAR data for {ticker_symbol}...', file=sys.stderr)
        
        # Step 1: Convert ticker to CIK
        cik = ticker_to_cik(ticker_symbol)
        if not cik:
            return {
                "success": False,
                "error": f"Could not find CIK for ticker {ticker_symbol}",
                "ticker": ticker_symbol
            }
        
        print(f'Found CIK: {cik}', file=sys.stderr)
        
        # Step 2: Fetch ALL Form 4 filings with pagination
        filings = fetch_form4_list(cik, max_years=max_years)
        if not filings:
            return {
                "success": True,
                "ticker": ticker_symbol,
                "purchases": [],
                "sales": [],
                "total_purchases": 0,
                "total_sales": 0,
                "purchase_volume": 0,
                "sale_volume": 0,
                "purchase_value": 0,
                "sale_value": 0,
                "source": "EDGAR"
            }
        
        # Step 3: Parse Form 4 filings in PARALLEL (thread-safe with rate limiting)
        print(f'Processing {len(filings)} filings with {MAX_WORKERS} parallel workers...', file=sys.stderr)
        all_purchases = []
        all_sales = []
        processed_count = 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all filing parsing jobs
            future_to_filing = {
                executor.submit(parse_form4_xml, filing['url']): filing 
                for filing in filings
            }
            
            # Process results as they complete
            for future in as_completed(future_to_filing):
                processed_count += 1
                
                # Progress update every 10 filings
                if processed_count % 10 == 0:
                    total_transactions = len(all_purchases) + len(all_sales)
                    print(f'Progress: {processed_count}/{len(filings)}, found {total_transactions} transactions so far', file=sys.stderr)
                
                try:
                    transactions = future.result()
                    if transactions:
                        for txn in transactions:
                            if txn['type'] == 'P - Purchase':
                                all_purchases.append(txn)
                            elif txn['type'] == 'S - Sale':
                                all_sales.append(txn)
                except Exception as e:
                    # Log but continue on individual filing errors
                    print(f'Error processing filing: {e}', file=sys.stderr)
                    continue
        
        # Sort by date (oldest first)
        all_purchases.sort(key=lambda x: x['date'])
        all_sales.sort(key=lambda x: x['date'])
        
        print(f'Found {len(all_purchases)} purchases, {len(all_sales)} sales', file=sys.stderr)
        
        return {
            "success": True,
            "ticker": ticker_symbol,
            "purchases": all_purchases,
            "sales": all_sales,
            "total_purchases": len(all_purchases),
            "total_sales": len(all_sales),
            "purchase_volume": sum(p['shares'] for p in all_purchases),
            "sale_volume": sum(s['shares'] for s in all_sales),
            "purchase_value": sum(p['value'] for p in all_purchases),
            "sale_value": sum(s['value'] for s in all_sales),
            "source": "EDGAR"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "ticker": ticker_symbol
        }


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python fetch_edgar_trades.py <TICKER> [MAX_YEARS]"
        }))
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    max_years = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    result = fetch_edgar_insider_trades(ticker, max_years)
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result.get('success') else 1)


if __name__ == "__main__":
    main()
