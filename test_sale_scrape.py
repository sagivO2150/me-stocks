#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

url = "http://openinsider.com/screener"
params = {
    's': '', 'o': '', 'pl': '5', 'ph': '',
    'll': '', 'lh': '', 'fd': '30', 'fdr': '',
    'td': '1', 'tdr': '', 'fdlyl': '', 'fdlyh': '',
    'daysago': '', 'xp': '1', 'xs': '1', 'vl': '', 'vh': '',
    'ocl': '', 'och': '', 'sic1': '-1', 'sicl': '100', 'sich': '9999',
    'isofficer': '1', 'iscob': '1', 'isceo': '1', 'ispres': '1', 'iscoo': '1', 'iscfo': '1',
    'isgc': '1', 'isvp': '1', 'isdirector': '1', 'istenpercent': '1', 'isother': '1',
    'grp': '2',
    'nfl': '', 'nfh': '', 'nil': '3', 'nih': '',
    'nol': '', 'noh': '',
    'v2l': '1000', 'v2h': '',
    'oc2l': '10', 'oc2h': '',
    'sortcol': '0', 'cnt': '10', 'page': '1'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

print("Making request to OpenInsider...")
response = requests.get(url, params=params, headers=headers, timeout=30)
print(f"Status code: {response.status_code}")
print(f"Response length: {len(response.content)} bytes")

soup = BeautifulSoup(response.content, 'html.parser')

# Save HTML for inspection
with open('/tmp/openinsider_response.html', 'w') as f:
    f.write(response.text)
print("Saved HTML to /tmp/openinsider_response.html")

# Look for the results text
if 'no results' in response.text.lower():
    print("\n❌ 'No results' found in response")
if 'cluster' in response.text.lower():
    print("\n'cluster' found in response")

tables = soup.find_all('table')
print(f"\nFound {len(tables)} tables total")

table = soup.find('table', {'class': 'tinytable'})

if not table:
    print("❌ No table found!")
    # Check if there's any error message
    print("\nSearching for 'no results' or error messages...")
    if 'no results' in response.text.lower():
        print("Found 'no results' in response")
else:
    print(f"✅ Found table!")
    rows = table.find_all('tr')
    print(f"Total rows: {len(rows)}")
    if len(rows) > 1:
        print("\nFirst data row:")
        cols = rows[1].find_all('td')
        print(f"Columns: {len(cols)}")
        for i, col in enumerate(cols[:15]):
            print(f"  Col {i}: {col.text.strip()}")
