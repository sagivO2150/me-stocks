#!/usr/bin/env python3
"""
OpenInsider Screener Data Scraper with Financial Health Check
Fetches insider trading data and validates company financial health using yfinance (FREE)
"""

import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import time
import yfinance as yf

# FMP API Configuration (DISABLED - too limited in free tier)
# API_KEY = "EypEpLbJcxfRpdMBFcJppxD2YIEnGD0T"
# FMP_BASE_URL = "https://financialmodelingprep.com/stable"

API_CALL_DELAY = 1.0  # Delay between yfinance calls (be respectful)


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
    
    # Output directory
    output_dir = "/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs"
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"openinsider_data_{timestamp}.csv"
    
    # Full path to output file
    filepath = f"{output_dir}/{filename}"
    
    # Get all possible field names
    fieldnames = list(data[0].keys())
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"\nData saved to: {filepath}")
    print(f"Total records: {len(data)}")


def get_yfinance_data(ticker):
    """
    Fetch comprehensive financial data using yfinance (FREE)
    Returns: Ratios, Metrics, Profile data
    """
    try:
        time.sleep(API_CALL_DELAY)  # Be respectful to Yahoo
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Extract all the metrics that FMP wanted money for
        return {
            # Financial Ratios
            'debt_to_equity': info.get('debtToEquity', 'N/A'),
            'current_ratio': info.get('currentRatio', 'N/A'),
            'quick_ratio': info.get('quickRatio', 'N/A'),
            'roe': info.get('returnOnEquity', 'N/A'),
            
            # Key Metrics
            'profit_margins': info.get('profitMargins', 'N/A'),
            'operating_margins': info.get('operatingMargins', 'N/A'),
            'revenue_per_share': info.get('revenuePerShare', 'N/A'),
            'free_cash_flow': info.get('freeCashflow', 'N/A'),
            
            # Valuation Metrics
            'pe_ratio': info.get('trailingPE', 'N/A'),
            'forward_pe': info.get('forwardPE', 'N/A'),
            'peg_ratio': info.get('pegRatio', 'N/A'),
            'price_to_book': info.get('priceToBook', 'N/A'),
            
            # Profile
            'market_cap': info.get('marketCap', 'N/A'),
            'beta': info.get('beta', 'N/A'),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            
            # Analyst Data
            'target_mean_price': info.get('targetMeanPrice', 'N/A'),
            'target_high_price': info.get('targetHighPrice', 'N/A'),
            'target_low_price': info.get('targetLowPrice', 'N/A'),
            'recommendation': info.get('recommendationKey', 'N/A'),
        }
        
    except Exception as e:
        print(f"  Error fetching yfinance data for {ticker}: {str(e)[:80]}")
        return None


def enrich_with_financial_data(insider_data):
    """
    Enrich insider trading data with financial health metrics using yfinance
    """
    print("\n" + "=" * 50)
    print("Fetching Financial Data (yfinance - FREE)...")
    print("=" * 50)
    
    enriched_data = []
    
    for idx, record in enumerate(insider_data, 1):
        ticker = record.get('Ticker', '').strip()
        
        if not ticker:
            enriched_data.append(record)
            continue
        
        print(f"\n[{idx}/{len(insider_data)}] Analyzing {ticker}...")
        
        # Fetch comprehensive data from yfinance
        yf_data = get_yfinance_data(ticker)
        
        # Merge all data
        enriched_record = record.copy()
        
        if yf_data:
            enriched_record.update({
                # Financial Ratios
                'Debt_to_Equity': yf_data['debt_to_equity'],
                'Current_Ratio': yf_data['current_ratio'],
                'Quick_Ratio': yf_data['quick_ratio'],
                'ROE': yf_data['roe'],
                
                # Profitability
                'Profit_Margins': yf_data['profit_margins'],
                'Operating_Margins': yf_data['operating_margins'],
                
                # Valuation
                'PE_Ratio': yf_data['pe_ratio'],
                'Forward_PE': yf_data['forward_pe'],
                'PEG_Ratio': yf_data['peg_ratio'],
                'Price_to_Book': yf_data['price_to_book'],
                
                # Company Info
                'Market_Cap': yf_data['market_cap'],
                'Beta': yf_data['beta'],
                'Sector': yf_data['sector'],
                'Industry': yf_data['industry'],
                
                # Analyst Targets
                'Target_Mean_Price': yf_data['target_mean_price'],
                'Target_High_Price': yf_data['target_high_price'],
                'Target_Low_Price': yf_data['target_low_price'],
                'Recommendation': yf_data['recommendation'],
            })
            
            # Health assessment using the "2026 Strategy"
            health_flags = []
            
            # Debt Check
            debt_eq = yf_data['debt_to_equity']
            if debt_eq != 'N/A' and debt_eq < 150:
                health_flags.append('✓ Low Debt')
            elif debt_eq != 'N/A' and debt_eq > 300:
                health_flags.append('⚠ High Debt')
            
            # Liquidity Check
            curr_ratio = yf_data['current_ratio']
            if curr_ratio != 'N/A' and curr_ratio > 1.0:
                health_flags.append('✓ Good Liquidity')
            elif curr_ratio != 'N/A' and curr_ratio < 1.0:
                health_flags.append('⚠ Low Liquidity')
            
            # Profitability Check
            profit_margin = yf_data['profit_margins']
            if profit_margin != 'N/A' and profit_margin > 0:
                health_flags.append('✓ Profitable')
            elif profit_margin != 'N/A' and profit_margin < 0:
                health_flags.append('⚠ Unprofitable')
            
            # Overall Quality Score
            if debt_eq != 'N/A' and curr_ratio != 'N/A' and profit_margin != 'N/A':
                if debt_eq < 150 and curr_ratio > 1.0 and profit_margin > 0:
                    health_flags.append('🔥 HIGH QUALITY')
            
            enriched_record['Health_Flags'] = ' | '.join(health_flags) if health_flags else 'N/A'
            
            if health_flags:
                print(f"  Health: {' | '.join(health_flags)}")
        else:
            enriched_record['Health_Flags'] = 'N/A'
        
        enriched_data.append(enriched_record)
    
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
    print("\nFinancial Metrics (yfinance - FREE):") 
    print("- Debt-to-Equity, Current Ratio, Quick Ratio, ROE")
    print("- Profit & Operating Margins")
    print("- PE, PEG, Price-to-Book Ratios")
    print("- Analyst Price Targets & Recommendations")
    print("- Market Cap, Beta, Sector, Industry")
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
