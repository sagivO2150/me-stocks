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


# SEC EDGAR Rate limits: 10 requests/second max
RATE_LIMIT_DELAY = 0.12  # ~8 requests/sec, safely under limit

HEADERS = {
    'User-Agent': 'Stock-Insider-Tracker/1.0 sagiv.oron@example.com',
    'Accept-Encoding': 'gzip, deflate',
    'Host': 'www.sec.gov'
}


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


def fetch_form4_list(cik, max_count=200):
    """Get list of Form 4 filings from EDGAR"""
    time.sleep(RATE_LIMIT_DELAY)
    
    # Use HTML output instead of XML (more reliable)
    url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&count={max_count}'
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the filings table
        table = soup.find('table', {'class': 'tableFile2'})
        if not table:
            return []
        
        filings = []
        for row in table.find_all('tr')[1:]:  # Skip header
            cols = row.find_all('td')
            if len(cols) < 4:
                continue
            
            form_type = cols[0].text.strip()
            if form_type != '4':
                continue
            
            filing_date = cols[3].text.strip()
            
            # Get document link
            doc_link = cols[1].find('a', {'id': 'documentsbutton'})
            if not doc_link:
                continue
            
            # Convert to direct filing URL (.txt format)
            doc_url = 'https://www.sec.gov' + doc_link['href']
            # Change -index.htm to .txt
            doc_url = doc_url.replace('-index.htm', '.txt')
            
            filings.append({
                'date': filing_date,
                'url': doc_url
            })
        
        return filings
    
    except Exception as e:
        print(f'Error fetching Form 4 list: {e}', file=sys.stderr)
        return []


def parse_form4_xml(filing_url):
    """Parse a Form 4 filing and extract buy/sell transactions"""
    time.sleep(RATE_LIMIT_DELAY)
    
    try:
        response = requests.get(filing_url, headers=HEADERS, timeout=30)
        
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
        if reporting_owner:
            name_elem = reporting_owner.find('.//rptOwnerName')
            if name_elem is not None:
                owner_name = name_elem.text if name_elem.text else 'Unknown'
            
            relationship = reporting_owner.find('.//reportingOwnerRelationship')
            if relationship:
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


def fetch_edgar_insider_trades(ticker_symbol, max_years=10):
    """
    Fetch insider trading data from EDGAR (extends beyond OpenInsider's 2-year limit).
    Returns same format as fetch_insider_trades.py for compatibility.
    
    Args:
        ticker_symbol: Stock ticker (e.g., 'AAPL', 'GME')
        max_years: Maximum years of history to fetch (default: 10)
    
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
        
        # Step 2: Fetch Form 4 filings list
        filings = fetch_form4_list(cik, max_count=200)
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
        
        print(f'Found {len(filings)} Form 4 filings', file=sys.stderr)
        
        # Filter by date range
        cutoff_date = datetime.now() - timedelta(days=max_years * 365)
        recent_filings = [
            f for f in filings 
            if datetime.strptime(f['date'], '%Y-%m-%d') >= cutoff_date
        ]
        
        print(f'Processing {len(recent_filings)} filings within {max_years} years...', file=sys.stderr)
        
        # Step 3: Parse each Form 4 for transactions
        all_purchases = []
        all_sales = []
        
        for i, filing in enumerate(recent_filings):
            if i % 10 == 0:
                print(f'Progress: {i}/{len(recent_filings)}', file=sys.stderr)
            
            transactions = parse_form4_xml(filing['url'])
            if transactions:
                for txn in transactions:
                    if txn['type'] == 'P - Purchase':
                        all_purchases.append(txn)
                    elif txn['type'] == 'S - Sale':
                        all_sales.append(txn)
        
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
    max_years = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    result = fetch_edgar_insider_trades(ticker, max_years)
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result.get('success') else 1)


if __name__ == "__main__":
    main()
