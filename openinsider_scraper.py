#!/usr/bin/env python3
"""
OpenInsider Screener Data Scraper with Financial Health Check
Fetches insider trading data and validates company financial health using FMP API
"""

import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import time
import os

# API Configuration
API_KEY = "EypEpLbJcxfRpdMBFcJppxD2YIEnGD0T"
FMP_BASE_URL = "https://financialmodelingprep.com/stable"
API_CALL_DELAY = 2.5  # Delay between API calls (seconds) to stay under 250/day limit
MAX_API_CALLS = 240  # Safety buffer under 250/day limit


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


def get_financial_ratios(ticker, api_calls_made):
    """
    Fetch key financial ratios from FMP API
    Focus on: Debt-to-Equity, Current Ratio
    """
    if api_calls_made >= MAX_API_CALLS:
        print(f"  ⚠️  API call limit reached, skipping {ticker}")
        return None, api_calls_made
    
    url = f"{FMP_BASE_URL}/ratios"
    params = {'symbol': ticker, 'apikey': API_KEY, 'limit': 1}
    
    try:
        time.sleep(API_CALL_DELAY)  # Rate limiting
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        api_calls_made += 1
        
        if data and len(data) > 0:
            ratios = data[0]
            return {
                'debt_to_equity': ratios.get('debtEquityRatio', 'N/A'),
                'current_ratio': ratios.get('currentRatio', 'N/A'),
                'quick_ratio': ratios.get('quickRatio', 'N/A'),
                'roe': ratios.get('returnOnEquity', 'N/A'),
            }, api_calls_made
        return None, api_calls_made
        
    except Exception as e:
        print(f"  Error fetching ratios for {ticker}: {str(e)[:80]}")
        return None, api_calls_made


def get_key_metrics(ticker, api_calls_made):
    """
    Fetch key metrics from FMP API
    Focus on: ROIC, Free Cash Flow Yield
    """
    if api_calls_made >= MAX_API_CALLS:
        return None, api_calls_made
    
    url = f"{FMP_BASE_URL}/key-metrics"
    params = {'symbol': ticker, 'apikey': API_KEY, 'limit': 1}
    
    try:
        time.sleep(API_CALL_DELAY)  # Rate limiting
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        api_calls_made += 1
        
        if data and len(data) > 0:
            metrics = data[0]
            return {
                'roic': metrics.get('roic', 'N/A'),
                'fcf_yield': metrics.get('freeCashFlowYield', 'N/A'),
                'pe_ratio': metrics.get('peRatio', 'N/A'),
                'ev_to_ebitda': metrics.get('enterpriseValueOverEBITDA', 'N/A'),
            }, api_calls_made
        return None, api_calls_made
        
    except Exception as e:
        print(f"  Error fetching metrics for {ticker}: {str(e)[:80]}")
        return None, api_calls_made


def get_financial_scores(ticker, api_calls_made):
    """
    Fetch company profile from FMP API (free tier)
    Get: Market Cap, Beta, Sector
    """
    if api_calls_made >= MAX_API_CALLS:
        return None, api_calls_made
    
    url = f"{FMP_BASE_URL}/profile"
    params = {'symbol': ticker, 'apikey': API_KEY}
    
    try:
        time.sleep(API_CALL_DELAY)  # Rate limiting
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        api_calls_made += 1
        
        if data and len(data) > 0:
            profile = data[0]
            return {
                'market_cap': profile.get('mktCap', 'N/A'),
                'beta': profile.get('beta', 'N/A'),
                'sector': profile.get('sector', 'N/A'),
            }, api_calls_made
        return None, api_calls_made
        
    except Exception as e:
        print(f"  Error fetching profile for {ticker}: {str(e)[:80]}")
        return None, api_calls_made


def enrich_with_financial_data(insider_data):
    """
    Enrich insider trading data with financial health metrics
    """
    print("\n" + "=" * 50)
    print("Fetching Company Profile Data (Free Tier)...")
    print("=" * 50)
    
    api_calls_made = 0
    enriched_data = []
    
    for idx, record in enumerate(insider_data, 1):
        ticker = record.get('Ticker', '').strip()
        
        if not ticker:
            enriched_data.append(record)
            continue
        
        print(f"\n[{idx}/{len(insider_data)}] Analyzing {ticker}...")
        
        # Only use profile endpoint (free tier - 1 API call per ticker)
        profile, api_calls_made = get_financial_scores(ticker, api_calls_made)
        
        # Merge all data
        enriched_record = record.copy()
        
        if profile:
            enriched_record.update({
                'Market_Cap': profile['market_cap'],
                'Beta': profile['beta'],
                'Sector': profile['sector'],
            })
        
        # Health assessment
        health_flags = []
        if profile:
            beta = profile['beta']
            if beta != 'N/A':
                if beta < 1.0:
                    health_flags.append('✓ Lower Volatility')
                elif beta > 1.5:
                    health_flags.append('⚠ High Volatility')
        
        enriched_record['Health_Flags'] = ' | '.join(health_flags) if health_flags else 'N/A'
        
        print(f"  API Calls Used: {api_calls_made}/{MAX_API_CALLS}")
        if health_flags:
            print(f"  Health: {' | '.join(health_flags)}")
        
        enriched_data.append(enriched_record)
        
        # Safety check
        if api_calls_made >= MAX_API_CALLS:
            print(f"\n⚠️  Reached API call limit ({MAX_API_CALLS}). Stopping enrichment.")
            # Add remaining records without enrichment
            enriched_data.extend(insider_data[idx:])
            break
    
    print(f"\n✓ Total API calls made: {api_calls_made}/{MAX_API_CALLS}")
    return enriched_data


def main():
    """Main function to scrape and save OpenInsider data"""
    
    print("OpenInsider Screener + Financial Health Analyzer")
    print("=" * 50)
    print("\nFilters applied:")
    print("- Minimum price: $5")
    print("- Filing date: Last 30 days")
    print("- Insiders: CEO, COO, CFO, Director")
    print("- Minimum insiders: 3")
    print("- Minimum value: $150k+")
    print("\nFinancial Metrics (Free Tier):") 
    print("- Market Cap, Beta, Sector")
    print("- Volatility Assessment")
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
    
    # Enrich with financial data
    if all_data:
        enriched_data = enrich_with_financial_data(all_data)
        save_to_csv(enriched_data)
    else:
        print("No data was scraped. Please check the filters or website availability.")


if __name__ == "__main__":
    main()
