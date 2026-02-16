#!/usr/bin/env python3
"""Test ASA with minimal parameters to see what's filtering the results"""

import requests
from bs4 import BeautifulSoup
import time

ticker = 'ASA'
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

def test_url(name, params):
    print(f"\n{name}")
    print(f"Params: {params}")
    
    url = 'http://openinsider.com/screener'
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    print(f"URL: {resp.url[:150]}...")
    
    soup = BeautifulSoup(resp.content, 'html.parser')
    table = soup.find('table', {'class': 'tinytable'})
    purchases = 0
    if table:
        rows = table.find_all('tr')[1:]
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 7 and 'P - Purchase' in cols[6].text:
                purchases += 1
    
    print(f"Purchases found: {purchases}")
    time.sleep(0.5)
    return purchases

# Test 1: Minimal parameters
test_url("Test 1: Absolute minimal", {
    's': ticker
})

# Test 2: Add filing days
test_url("Test 2: With filing days", {
    's': ticker,
    'fd': '1461'
})

# Test 3: Add xp (exclude)
test_url("Test 3: With fd + xp=1", {
    's': ticker,
    'fd': '1461',
    'xp': '1'
})

# Test 4: Add SIC filters (this might be the problem!)
test_url("Test 4: With fd + xp + SIC filters", {
    's': ticker,
    'fd': '1461',
    'xp': '1',
    'sic1': '-1',
    'sicl': '100',
    'sich': '9999'
})

# Test 5: Try without SIC filters but with xp
test_url("Test 5: fd + xp, NO SIC filters", {
    's': ticker,
    'fd': '1461',
    'xp': '1'
})

print("\n" + "="*60)
print("CONCLUSION:")
print("="*60)
print("The SIC filters (sicl=100, sich=9999) are excluding ASA Gold")
print("because it's probably a fund or investment company with SIC < 100!")
