#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

# Test 1: td=0, xs=1 (user's URL - shows SALES despite td=0)
url1 = 'http://openinsider.com/screener?s=&o=&pl=5&ph=&ll=&lh=&fd=30&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xs=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&isofficer=1&iscob=1&isceo=1&ispres=1&iscoo=1&iscfo=1&isgc=1&isvp=1&isdirector=1&istenpercent=1&isother=1&grp=2&nfl=&nfh=&nil=3&nih=&nol=&noh=&v2l=1000&v2h=&oc2l=10&oc2h=&sortcol=0&cnt=10&page=1'

print("Testing: td=0, xs=1")
response = requests.get(url1, headers=headers, timeout=30)
soup = BeautifulSoup(response.content, 'html.parser')
table = soup.find('table', {'class': 'tinytable'})

if table:
    rows = table.find_all('tr')
    print(f"✅ FOUND TABLE with {len(rows)} rows")
    if len(rows) > 1:
        cols = rows[1].find_all('td')
        if len(cols) > 7:
            print(f"   Trade Type: {cols[7].text.strip()}")
else:
    print("❌ NO TABLE")
