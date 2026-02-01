#!/usr/bin/env python3
"""
OpenInsider Screener Data Scraper
Fetches insider trading data based on specified filters and saves to CSV
"""

import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import time


def scrape_openinsider(page=1):
    """
    Scrape OpenInsider with the specified filters
    
    Parameters:
    - page: Page number to fetch (default: 1)
    
    Returns:
    - List of dictionaries containing insider trading data
    """
    
    # Base URL and parameters from your request
    base_url = "http://openinsider.com/screener"
    
    params = {
        's': '',
        'o': '',
        'pl': '5',          # Minimum price
        'ph': '',
        'll': '',
        'lh': '',
        'fd': '30',         # Filing date within 30 days
        'fdr': '',
        'td': '0',          # Trade date
        'tdr': '',
        'fdlyl': '',
        'fdlyh': '',
        'daysago': '',
        'xp': '1',          # Filter
        'vl': '',
        'vh': '',
        'ocl': '',
        'och': '',
        'sic1': '-1',
        'sicl': '100',      # SIC code lower
        'sich': '9999',     # SIC code higher
        'isceo': '1',       # Include CEO
        'iscoo': '1',       # Include COO
        'iscfo': '1',       # Include CFO
        'isdirector': '1',  # Include Director
        'grp': '2',
        'nfl': '',
        'nfh': '',
        'nil': '3',         # Number of insiders
        'nih': '',
        'nol': '1',
        'noh': '',
        'v2l': '150',       # Volume filter
        'v2h': '',
        'oc2l': '',
        'oc2h': '',
        'sortcol': '0',
        'cnt': '100',       # Results per page
        'page': str(page)
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"Fetching page {page}...")
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the main data table
        table = soup.find('table', {'class': 'tinytable'})
        
        if not table:
            print("Warning: Could not find data table on page")
            return []
        
        data = []
        rows = table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cols = row.find_all('td')
            
            if len(cols) < 13:  # Skip rows that don't have enough columns
                continue
            
            # Extract text from each column
            record = {
                'X': cols[0].text.strip(),
                'Filing_Date': cols[1].text.strip(),
                'Trade_Date': cols[2].text.strip(),
                'Ticker': cols[3].text.strip(),
                'Company_Name': cols[4].text.strip(),
                'Industry': cols[5].text.strip(),
                'Insiders': cols[6].text.strip(),
                'Trade_Type': cols[7].text.strip(),
                'Price': cols[8].text.strip(),
                'Qty': cols[9].text.strip(),
                'Owned': cols[10].text.strip(),
                'Delta_Own': cols[11].text.strip(),
                'Value': cols[12].text.strip()
            }
            
            # Add performance columns if they exist
            if len(cols) > 13:
                record['1d'] = cols[13].text.strip() if len(cols) > 13 else ''
                record['1w'] = cols[14].text.strip() if len(cols) > 14 else ''
                record['1m'] = cols[15].text.strip() if len(cols) > 15 else ''
                record['6m'] = cols[16].text.strip() if len(cols) > 16 else ''
            
            data.append(record)
        
        print(f"Found {len(data)} records on page {page}")
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []


def save_to_csv(data, filename=None):
    """
    Save the scraped data to a CSV file
    
    Parameters:
    - data: List of dictionaries containing the data
    - filename: Output filename (default: auto-generated with timestamp)
    """
    
    if not data:
        print("No data to save")
        return
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"openinsider_data_{timestamp}.csv"
    
    # Get all possible field names
    fieldnames = list(data[0].keys())
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"\nData saved to: {filename}")
    print(f"Total records: {len(data)}")


def main():
    """Main function to scrape and save OpenInsider data"""
    
    print("OpenInsider Screener Data Scraper")
    print("=" * 50)
    print("\nFilters applied:")
    print("- Minimum price: $5")
    print("- Filing date: Last 30 days")
    print("- Insiders: CEO, COO, CFO, Director")
    print("- Minimum insiders: 3")
    print("- Minimum value: $150k+")
    print("=" * 50)
    print()
    
    # Scrape page 1 (you can modify to scrape multiple pages)
    all_data = []
    
    # To scrape multiple pages, modify this:
    num_pages = 1  # Change this to scrape more pages
    
    for page in range(1, num_pages + 1):
        data = scrape_openinsider(page=page)
        all_data.extend(data)
        
        # Be respectful to the server
        if page < num_pages:
            time.sleep(2)
    
    # Save to CSV
    if all_data:
        save_to_csv(all_data)
    else:
        print("No data was scraped. Please check the filters or website availability.")


if __name__ == "__main__":
    main()
