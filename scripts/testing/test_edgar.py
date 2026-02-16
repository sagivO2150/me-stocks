#!/usr/bin/env python3
"""
Test EDGAR Form 4 data fetching
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def fetch_edgar_form4_filings(cik, count=100):
    """Fetch Form 4 filings from EDGAR for a specific CIK"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    # Fetch Form 4 filings (insider transactions)
    # NOTE: Use type=4 for insider transactions
    url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&count={count}'
    
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the results table
    table = soup.find('table', {'class': 'tableFile2'})
    if not table:
        print('No filings table found')
        return []
    
    rows = table.find_all('tr')[1:]  # Skip header
    filings = []
    
    print(f'\nFound {len(rows)} Form 4 filings\n')
    print('Filing Date\tForm\tDescription')
    print('-' * 100)
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 4:
            form_type = cols[0].text.strip()
            description = cols[2].text.strip()
            filing_date = cols[3].text.strip()
            
            # Get the document link
            doc_link = cols[1].find('a', {'id': 'documentsbutton'})
            if doc_link:
                doc_url = 'https://www.sec.gov' + doc_link['href']
            else:
                doc_url = None
            
            filings.append({
                'form_type': form_type,
                'description': description,
                'filing_date': filing_date,
                'document_url': doc_url
            })
            
            print(f'{filing_date}\t{form_type}\t{description[:60]}')
    
    return filings


def fetch_openinsider_trades(ticker):
    """Fetch trades from OpenInsider for comparison"""
    url = f"http://openinsider.com/{ticker}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    table = soup.find('table', {'class': 'tinytable'})
    if not table:
        print(f'\nNo OpenInsider data found for {ticker}')
        return []
    
    rows = table.find_all('tr')[1:]
    trades = []
    
    print(f'\n\nOpenInsider trades for {ticker}:')
    print('-' * 100)
    print('Trade Date\tType\tInsider\tTitle\tShares\tValue')
    print('-' * 100)
    
    for row in rows[:20]:  # Show first 20
        cols = row.find_all('td')
        if len(cols) < 12:
            continue
        
        trade_date = cols[2].text.strip()
        trade_type = cols[6].text.strip()
        insider_name = cols[4].text.strip()
        title = cols[5].text.strip()
        shares = cols[8].text.strip()
        value = cols[11].text.strip()
        
        trades.append({
            'trade_date': trade_date,
            'trade_type': trade_type,
            'insider_name': insider_name,
            'title': title,
            'shares': shares,
            'value': value
        })
        
        print(f'{trade_date}\t{trade_type[:15]}\t{insider_name[:20]}\t{title[:15]}\t{shares}\t{value}')
    
    return trades


if __name__ == '__main__':
    # ADC example - CIK 917251
    ticker = 'ADC'
    cik = '917251'
    
    print(f'\n{"="*100}')
    print(f'Comparing EDGAR vs OpenInsider for {ticker} (CIK: {cik})')
    print(f'{"="*100}')
    
    # Fetch EDGAR filings
    edgar_filings = fetch_edgar_form4_filings(cik, count=40)
    
    # Fetch OpenInsider trades
    openinsider_trades = fetch_openinsider_trades(ticker)
    
    # Summary
    print(f'\n\n{"="*100}')
    print(f'SUMMARY')
    print(f'{"="*100}')
    print(f'EDGAR Form 4 filings found: {len(edgar_filings)}')
    print(f'OpenInsider trades found: {len(openinsider_trades)}')
    
    if edgar_filings:
        print(f'\nEarliest EDGAR filing: {edgar_filings[-1]["filing_date"]}')
        print(f'Latest EDGAR filing: {edgar_filings[0]["filing_date"]}')
    
    if openinsider_trades:
        earliest_oi = min(t['trade_date'] for t in openinsider_trades)
        latest_oi = max(t['trade_date'] for t in openinsider_trades)
        print(f'\nEarliest OpenInsider trade: {earliest_oi}')
        print(f'Latest OpenInsider trade: {latest_oi}')
