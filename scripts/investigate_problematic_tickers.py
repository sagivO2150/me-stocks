#!/usr/bin/env python3
"""
Investigate why ASA and NFRX showed less data with extended URL
"""

import requests
from bs4 import BeautifulSoup
import time


def investigate_ticker(ticker):
    print(f'\n{"="*60}')
    print(f'Investigating {ticker}')
    print(f'{"="*60}')
    
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    
    # Test simple URL
    simple_url = f'http://openinsider.com/search?q={ticker}'
    print(f'\n1. Simple URL: {simple_url}')
    
    response = requests.get(simple_url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', {'class': 'tinytable'})
    
    if table:
        rows = table.find_all('tr')[1:]
        purchases = []
        sales = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 7:
                trade_type = cols[6].text.strip()
                date = cols[2].text.strip()
                if 'P - Purchase' in trade_type:
                    purchases.append(date)
                elif 'S - Sale' in trade_type:
                    sales.append(date)
        
        print(f'   Purchases: {len(purchases)}')
        print(f'   Sales: {len(sales)}')
        if purchases:
            print(f'   Purchase range: {min(purchases)} to {max(purchases)}')
    
    time.sleep(1)
    
    # Test extended URL with xs=1
    extended_url = 'http://openinsider.com/screener'
    params = {'s': ticker, 'fd': '1461', 'xp': '1', 'xs': '1', 'cnt': '1000', 'page': '1', 'grp': '0'}
    print(f'\n2. Extended URL with xs=1 (filters for sales)')
    
    response = requests.get(extended_url, params=params, headers=headers, timeout=30)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', {'class': 'tinytable'})
    
    if table:
        rows = table.find_all('tr')[1:]
        purchases = []
        sales = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 7:
                trade_type = cols[6].text.strip()
                date = cols[2].text.strip()
                if 'P - Purchase' in trade_type:
                    purchases.append(date)
                elif 'S - Sale' in trade_type:
                    sales.append(date)
        
        print(f'   Purchases: {len(purchases)}')
        print(f'   Sales: {len(sales)}')
    
    time.sleep(1)
    
    # Test extended URL WITHOUT xs=1 (should show purchases)
    params_no_xs = {'s': ticker, 'fd': '1461', 'xp': '1', 'cnt': '1000', 'page': '1', 'grp': '0'}
    print(f'\n3. Extended URL WITHOUT xs=1 (should show purchases)')
    
    response = requests.get(extended_url, params=params_no_xs, headers=headers, timeout=30)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', {'class': 'tinytable'})
    
    if table:
        rows = table.find_all('tr')[1:]
        purchases = []
        sales = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 7:
                trade_type = cols[6].text.strip()
                date = cols[2].text.strip()
                if 'P - Purchase' in trade_type:
                    purchases.append(date)
                elif 'S - Sale' in trade_type:
                    sales.append(date)
        
        print(f'   Purchases: {len(purchases)}')
        print(f'   Sales: {len(sales)}')
        if purchases:
            print(f'   Purchase range: {min(purchases)} to {max(purchases)}')


if __name__ == '__main__':
    investigate_ticker('ASA')
    investigate_ticker('NFRX')
    
    print(f'\n{"="*60}')
    print('CONCLUSION:')
    print(f'{"="*60}')
    print('The issue is that the test script had xs=1 in the extended URL,')
    print('which filters for SALES instead of PURCHASES.')
    print('\nFor fetching purchase data, we should use the extended URL')
    print('WITHOUT the xs=1 parameter.')
