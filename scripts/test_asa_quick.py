#!/usr/bin/env python3
"""Quick test of ASA ticker with both URLs"""

import requests
from bs4 import BeautifulSoup
import time

ticker = 'ASA'
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

# Simple URL
print(f"Testing {ticker} with SIMPLE URL...")
simple_url = f'http://openinsider.com/search?q={ticker}'
resp = requests.get(simple_url, headers=headers, timeout=30)
soup = BeautifulSoup(resp.content, 'html.parser')
table = soup.find('table', {'class': 'tinytable'})
simple_purchases = 0
if table:
    rows = table.find_all('tr')[1:]
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 7 and 'P - Purchase' in cols[6].text:
            simple_purchases += 1

print(f"Simple URL purchases: {simple_purchases}")

time.sleep(1)

# Extended URL
print(f"\nTesting {ticker} with EXTENDED URL (no xs parameter)...")
extended_url = 'http://openinsider.com/screener'
params = {
    's': ticker,
    'fd': '1461',
    'xp': '1',
    'cnt': '1000',
    'page': '1',
    'grp': '0',
    'o': '', 'pl': '', 'ph': '', 'll': '', 'lh': '',
    'fdr': '', 'td': '0', 'tdr': '', 'fdlyl': '', 'fdlyh': '',
    'daysago': '', 'vl': '', 'vh': '', 'ocl': '', 'och': '',
    'sic1': '-1', 'sicl': '100', 'sich': '9999',
    'nfl': '', 'nfh': '', 'nil': '', 'nih': '',
    'nol': '', 'noh': '', 'v2l': '', 'v2h': '',
    'oc2l': '', 'oc2h': '', 'sortcol': '0'
}

print(f"URL: {extended_url}")
print(f"Params: {params}")

resp = requests.get(extended_url, params=params, headers=headers, timeout=30)
print(f"Final URL: {resp.url}")

soup = BeautifulSoup(resp.content, 'html.parser')
table = soup.find('table', {'class': 'tinytable'})
extended_purchases = 0
if table:
    rows = table.find_all('tr')[1:]
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 7 and 'P - Purchase' in cols[6].text:
            extended_purchases += 1

print(f"Extended URL purchases: {extended_purchases}")
print(f"\nDifference: {extended_purchases - simple_purchases}")
