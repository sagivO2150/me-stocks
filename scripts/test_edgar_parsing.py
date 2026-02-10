#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&owner=include&count=10'
headers = {'User-Agent': 'Stock-Insider-Tracker/1.0 sagiv.oron@example.com'}
response = requests.get(url, headers=headers, timeout=30)
soup = BeautifulSoup(response.text, 'html.parser')

# Find table with Form column header
for table in soup.find_all('table'):
    ths = table.find_all('th')
    if ths and any('Form' in th.text for th in ths):
        print('Found Forms table!')
        print('Headers:', [th.text.strip() for th in ths])
        
        # Get first few rows - need to handle the strange structure
        all_rows = table.find_all('tr')
        print(f'\nTotal rows: {len(all_rows)}')
        
        form4_count = 0
        for idx, row in enumerate(all_rows[1:20]):  # Skip header, check first 20
            # Look for rows with "4" in first td
            tds = row.find_all('td', recursive=False)
            if tds and tds[0].text.strip() == '4':
                form4_count += 1
                print(f'\n=== Form 4 #{form4_count} ===')
                print(f'Row has {len(tds)} direct child tds')
                
                # Get the formats column (should have [html] [text] links)
                if len(tds) > 1:
                    links = tds[1].find_all('a')
                    print(f'Formats links: {[a.text.strip() for a in links]}')
                    for link in links:
                        if '[text]' in link.text:
                            txt_url = 'https://www.sec.gov' + link.get('href', '')
                            print(f'Text URL: {txt_url}')
                
                # Get filing date
                if len(tds) > 4:
                    print(f'Filing Date: {tds[4].text.strip()}')
                    
                if form4_count >= 3:
                    break
        
        print(f'\nTotal Form 4s found: {form4_count}')
        break
