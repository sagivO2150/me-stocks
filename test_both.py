#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

def test_request(trade_type):
    url = "http://openinsider.com/screener"
    td_value = '0' if trade_type == 'purchase' else '1'
    
    params = {
        's': '', 'o': '', 'pl': '5', 'ph': '',
        'll': '', 'lh': '', 'fd': '30', 'fdr': '',
        'td': td_value, 'tdr': '', 'fdlyl': '', 'fdlyh': '',
        'daysago': '', 'xp': '1', 'xs': '1' if trade_type == 'sale' else '', 'vl': '', 'vh': '',
        'ocl': '', 'och': '', 'sic1': '-1', 'sicl': '100', 'sich': '9999',
        'isofficer': '1', 'iscob': '1', 'isceo': '1', 'ispres': '1', 'iscoo': '1', 'iscfo': '1',
        'isgc': '1', 'isvp': '1', 'isdirector': '1', 'istenpercent': '1', 'isother': '1',
        'grp': '2',
        'nfl': '', 'nfh': '', 'nil': '3', 'nih': '',
        'nol': '', 'noh': '',
        'v2l': '150', 'v2h': '',
        'oc2l': '0', 'oc2h': '',
        'sortcol': '0', 'cnt': '100', 'page': '1'
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    print(f"\n{'='*60}")
    print(f"Testing {trade_type.upper()}")
    print(f"{'='*60}")
    print(f"td={td_value}, xs={'1' if trade_type=='sale' else ''}")
    
    response = requests.get(url, params=params, headers=headers, timeout=30)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', {'class': 'tinytable'})

    if table:
        rows = table.find_all('tr')
        print(f"✅ FOUND TABLE with {len(rows)} rows")
        if len(rows) > 1:
            cols = rows[1].find_all('td')
            print(f"   First data row has {len(cols)} columns")
            if len(cols) >= 8:
                print(f"   Trade Type column: {cols[7].text.strip()}")
    else:
        print(f"❌ NO TABLE FOUND")

test_request('purchase')
test_request('sale')

# Try sale WITHOUT xs=1
print(f"\n{'='*60}")
print(f"Testing SALE WITHOUT xs=1")
print(f"{'='*60}")

url = "http://openinsider.com/screener"
params = {
    's': '', 'o': '', 'pl': '5', 'ph': '',
    'll': '', 'lh': '', 'fd': '30', 'fdr': '',
    'td': '1', 'tdr': '', 'fdlyl': '', 'fdlyh': '',
    'daysago': '', 'xp': '1', 'vl': '', 'vh': '',
    'ocl': '', 'och': '', 'sic1': '-1', 'sicl': '100', 'sich': '9999',
    'isofficer': '1', 'iscob': '1', 'isceo': '1', 'ispres': '1', 'iscoo': '1', 'iscfo': '1',
    'isgc': '1', 'isvp': '1', 'isdirector': '1', 'istenpercent': '1', 'isother': '1',
    'grp': '2',
    'nfl': '', 'nfh': '', 'nil': '3', 'nih': '',
    'nol': '', 'noh': '',
    'v2l': '150', 'v2h': '',
    'oc2l': '0', 'oc2h': '',
    'sortcol': '0', 'cnt': '100', 'page': '1'
}
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}
response = requests.get(url, params=params, headers=headers, timeout=30)
soup = BeautifulSoup(response.content, 'html.parser')
table = soup.find('table', {'class': 'tinytable'})

if table:
    rows = table.find_all('tr')
    print(f"✅ FOUND TABLE with {len(rows)} rows")
else:
    print(f"❌ NO TABLE FOUND")

# Try sale with grp=0 (ungrouped)
print(f"\n{'='*60}")
print(f"Testing SALE with grp=0 (ungrouped)")
print(f"{'='*60}")

params['grp'] = '0'
params.pop('xs', None)
response = requests.get(url, params=params, headers=headers, timeout=30)
soup = BeautifulSoup(response.content, 'html.parser')
table = soup.find('table', {'class': 'tinytable'})

if table:
    rows = table.find_all('tr')
    print(f"✅ FOUND TABLE with {len(rows)} rows")
    if len(rows) > 1:
        cols = rows[1].find_all('td')
        print(f"   First data row has {len(cols)} columns")
        if len(cols) >= 7:
            print(f"   Ticker: {cols[3].text.strip()}")
            print(f"   Trade Type: {cols[6].text.strip()}")
else:
    print(f"❌ NO TABLE FOUND")
