#!/usr/bin/env python3
"""
EDGAR Form 4 Scraper - Prototype
Fetches insider trading data directly from SEC EDGAR with full historical depth
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import re

class EDGARScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'InsiderTracker/1.0 (educational use)',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        }
        self.rate_limit_delay = 0.15  # 6-7 requests per second, under SEC's 10/sec limit
    
    def ticker_to_cik(self, ticker):
        """Convert ticker symbol to CIK number"""
        # Try search method - more reliable
        time.sleep(self.rate_limit_delay)
        
        url = f'https://www.sec.gov/cgi-bin/browse-edgar?company={ticker}&action=getcompany'
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find CIK in the page
            cik_element = soup.find('span', {'class': 'companyName'})
            if cik_element:
                # Extract CIK from text like "AGREE REALTY CORP (CIK#: 0000917251)"
                text = cik_element.get_text()
                match = re.search(r'CIK#?:\s*(\d+)', text, re.I)
                if match:
                    cik = match.group(1).zfill(10)
                    return cik
            
            # Alternative: look for CIK in input field
            cik_input = soup.find('input', {'name': 'CIK'})
            if cik_input and cik_input.get('value'):
                return cik_input['value'].zfill(10)
            
            return None
        except Exception as e:
            print(f'Error converting ticker to CIK: {e}')
            return None
    
    def fetch_form4_filings_list(self, cik, count=100):
        """Get list of Form 4 filings for a CIK"""
        time.sleep(self.rate_limit_delay)
        
        url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&count={count}'
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            table = soup.find('table', {'class': 'tableFile2'})
            if not table:
                return []
            
            filings = []
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 4:
                    continue
                
                form_type = cols[0].text.strip()
                if form_type != '4':  # Only Form 4
                    continue
                
                filing_date = cols[3].text.strip()
                description = cols[2].text.strip()
                
                # Get document link
                doc_link = cols[1].find('a', {'id': 'documentsbutton'})
                if doc_link:
                    doc_url = 'https://www.sec.gov' + doc_link['href']
                else:
                    continue
                
                filings.append({
                    'filing_date': filing_date,
                    'description': description,
                    'document_url': doc_url
                })
            
            return filings
        
        except Exception as e:
            print(f'Error fetching Form 4 list: {e}')
            return []
    
    def parse_form4_html(self, document_url):
        """Parse Form 4 from HTML page (fallback when XML not available)"""
        time.sleep(self.rate_limit_delay)
        
        try:
            response = requests.get(document_url, headers=self.headers, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the primary document link (usually .xml or .html)
            table = soup.find('table', {'class': 'tableFile'})
            if not table:
                return None
            
            # Look for the primary document (first data file)
            primary_doc = None
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) >= 3:
                    # Check if this is a primary document (look for .xml or form4.html)
                    doc_link = cols[2].find('a')
                    if doc_link:
                        href = doc_link.get('href', '')
                        file_name = cols[2].text.strip()
                        
                        # Prefer .xml, but accept .html
                        if '.xml' in file_name or 'xslF345X' in href or 'form4' in file_name.lower():
                            primary_doc = 'https://www.sec.gov' + href
                            break
            
            if not primary_doc:
                return None
            
            # Fetch and parse the actual Form 4 document
            time.sleep(self.rate_limit_delay)
            response = requests.get(primary_doc, headers=self.headers, timeout=30)
            
            # Try to extract data from the rendered HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Basic extraction (this is a simplified version)
            # In practice, you'd need more robust parsing
            
            data = {
                'source_url': primary_doc,
                'raw_html_length': len(response.text),
                'parsed': False
            }
            
            # Try to find reporting owner
            owner_section = soup.find(text=re.compile('Reporting Owner', re.I))
            if owner_section:
                # Navigate to find owner name
                parent = owner_section.find_parent()
                if parent:
                    data['owner_hint'] = parent.get_text()[:200]
            
            return data
            
        except Exception as e:
            print(f'Error parsing Form 4: {e}')
            return None
    
    def fetch_all_insider_trades(self, ticker, max_filings=50):
        """Fetch all insider trades for a ticker from EDGAR"""
        print(f'\n{"="*80}')
        print(f'Fetching EDGAR Form 4 data for {ticker}')
        print(f'{"="*80}\n')
        
        # Convert ticker to CIK
        print(f'Step 1: Converting {ticker} to CIK...')
        cik = self.ticker_to_cik(ticker)
        if not cik:
            print(f'  ❌ Could not find CIK for {ticker}')
            return None
        
        print(f'  ✓ CIK: {cik}')
        
        # Fetch Form 4 filings list
        print(f'\nStep 2: Fetching Form 4 filings list...')
        filings = self.fetch_form4_filings_list(cik, count=max_filings)
        print(f'  ✓ Found {len(filings)} Form 4 filings')
        
        if not filings:
            return {
                'ticker': ticker,
                'cik': cik,
                'filings_found': 0,
                'transactions': []
            }
        
        # Show date range
        dates = [f['filing_date'] for f in filings]
        print(f'  📅 Date range: {min(dates)} to {max(dates)}')
        
        # Parse a sample filing (just the first one for now)
        print(f'\nStep 3: Parsing sample Form 4...')
        sample_filing = filings[0]
        print(f'  Filing date: {sample_filing["filing_date"]}')
        print(f'  URL: {sample_filing["document_url"]}')
        
        sample_data = self.parse_form4_html(sample_filing['document_url'])
        
        return {
            'ticker': ticker,
            'cik': cik,
            'filings_found': len(filings),
            'earliest_filing': min(dates),
            'latest_filing': max(dates),
            'sample_filing': sample_filing,
            'sample_parsed_data': sample_data,
            'all_filings': filings
        }


def main():
    scraper = EDGARScraper()
    
    # Test with ADC - use known CIK to bypass lookup issues
    ticker = 'ADC'
    cik = '0000917251'  # Known CIK for ADC (Agree Realty Corp)
    
    print(f'\n{"="*80}')
    print(f'Fetching EDGAR Form 4 data for {ticker}')
    print(f'{"="*80}\n')
    print(f'Using known CIK: {cik}')
    
    # Fetch Form 4 filings list
    print(f'\nStep 1: Fetching Form 4 filings list...')
    filings = scraper.fetch_form4_filings_list(cik, count=30)
    print(f'  ✓ Found {len(filings)} Form 4 filings')
    
    if not filings:
        print('  ❌ No filings found')
        return
    
    # Show date range
    dates = [f['filing_date'] for f in filings]
    print(f'  📅 Date range: {min(dates)} to {max(dates)}')
    
    # Parse a sample filing (just the first one for now)
    print(f'\nStep 2: Parsing sample Form 4...')
    sample_filing = filings[0]
    print(f'  Filing date: {sample_filing["filing_date"]}')
    print(f'  URL: {sample_filing["document_url"]}')
    
    sample_data = scraper.parse_form4_html(sample_filing['document_url'])
    
    result = {
        'ticker': ticker,
        'cik': cik,
        'filings_found': len(filings),
        'earliest_filing': min(dates),
        'latest_filing': max(dates),
        'sample_filing': sample_filing,
        'sample_parsed_data': sample_data,
        'all_filings': filings[:10]  # First 10 for display
    }
    
    print(f'\n\n{"="*80}')
    print('RESULTS')
    print(f'{"="*80}')
    print(json.dumps(result, indent=2, default=str))
    
    print(f'\n\n{"="*80}')
    print('SUMMARY')
    print(f'{"="*80}')
    print(f'Ticker: {result["ticker"]}')
    print(f'CIK: {result["cik"]}')
    print(f'Form 4 filings found: {result["filings_found"]}')
    if result['filings_found'] > 0:
        print(f'Historical range: {result["earliest_filing"]} to {result["latest_filing"]}')
    
    print(f'\n✅ SUCCESS: EDGAR scraper can fetch Form 4 filings')
    print(f'💡 Next step: Implement full XML/HTML parsing to extract:')
    print(f'   - Insider name and title')
    print(f'   - Transaction dates and amounts')
    print(f'   - Pre/post ownership stakes')
    print(f'   - Derivative transactions (options)')
    print(f'   - Footnotes and context')


if __name__ == '__main__':
    main()
