#!/usr/bin/env python3
"""
Scraper for quiverquant.com politician trading data
Extracts data from HTML tables (cleaner than Plotly JavaScript parsing)
Handles both stock-specific pages and main congresstrading page
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
import os


def scrape_stock_trades(ticker):
    """
    Scrape politician trading data for a specific stock ticker
    from https://www.quiverquant.com/congresstrading/stock/{TICKER}
    
    Args:
        ticker: Stock symbol (e.g., 'NVDA', 'TSLA')
        
    Returns:
        List of dictionaries with trade data
    """
    url = f"https://www.quiverquant.com/congresstrading/stock/{ticker}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    print(f"Fetching trades for {ticker} from: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the table-congress table
    table = soup.find('table', class_='table-congress')
    
    if not table:
        print("Error: Could not find table-congress table")
        return []
    
    trades = []
    tbody = table.find('tbody')
    
    if not tbody:
        print("Error: No tbody in table")
        return []
    
    rows = tbody.find_all('tr')
    print(f"Found {len(rows)} rows in table")
    
    for row in rows:
        try:
            cells = row.find_all('td')
            
            if len(cells) < 6:
                continue
            
            # Extract data from table cells
            # Columns: Stock | Transaction | Politician | Filed | Traded | Description
            
            # Stock (should be the ticker we're looking for)
            stock_cell = cells[0]
            stock = stock_cell.get_text(strip=True)
            
            # Transaction type (Sale/Purchase)
            transaction_cell = cells[1]
            transaction_type = transaction_cell.get_text(strip=True)
            
            # Politician name
            politician_cell = cells[2]
            politician = politician_cell.get_text(strip=True)
            # Clean up politician name - remove extra spaces and party info
            politician = re.sub(r'\s+', ' ', politician).strip()
            # Remove party affiliation like "House / D" or "Senate / R"
            politician = re.sub(r'\s+(?:House|Senate)\s*/\s*[DR]', '', politician)
            
            # Filed date
            filed_cell = cells[3]
            filed_date = filed_cell.get_text(strip=True)
            
            # Traded date
            traded_cell = cells[4]
            traded_date = traded_cell.get_text(strip=True)
            
            # Description (transaction size)
            description_cell = cells[5]
            transaction_size = description_cell.get_text(strip=True)
            
            trade = {
                'ticker': stock,
                'transaction_type': transaction_type,
                'politician': politician,
                'filed_date': filed_date,
                'traded_date': traded_date,
                'transaction_size': transaction_size
            }
            
            trades.append(trade)
            
        except Exception as e:
            print(f"Error parsing row: {e}")
            continue
    
    print(f"Successfully extracted {len(trades)} trades")
    return trades


def scrape_main_page():
    """
    Scrape recent politician trades from main congresstrading page
    https://www.quiverquant.com/congresstrading/
    
    Returns:
        List of dictionaries with trade data
    """
    url = "https://www.quiverquant.com/congresstrading/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    print(f"Fetching recent trades from: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the table-congress table
    table = soup.find('table', class_='table-congress')
    
    if not table:
        print("Error: Could not find table-congress table")
        return []
    
    trades = []
    tbody = table.find('tbody')
    
    if not tbody:
        print("Error: No tbody in table")
        return []
    
    rows = tbody.find_all('tr')
    print(f"Found {len(rows)} rows in table")
    
    for row in rows:
        try:
            cells = row.find_all('td')
            
            if len(cells) < 6:
                continue
            
            # Extract data - same structure as stock-specific page
            stock = cells[0].get_text(strip=True)
            transaction_type = cells[1].get_text(strip=True)
            politician = cells[2].get_text(strip=True)
            politician = re.sub(r'\s+', ' ', politician).strip()
            politician = re.sub(r'\s+(?:House|Senate)\s*/\s*[DR]', '', politician)
            filed_date = cells[3].get_text(strip=True)
            traded_date = cells[4].get_text(strip=True)
            transaction_size = cells[5].get_text(strip=True)
            
            trade = {
                'ticker': stock,
                'transaction_type': transaction_type,
                'politician': politician,
                'filed_date': filed_date,
                'traded_date': traded_date,
                'transaction_size': transaction_size
            }
            
            trades.append(trade)
            
        except Exception as e:
            print(f"Error parsing row: {e}")
            continue
    
    print(f"Successfully extracted {len(trades)} trades")
    return trades


def save_to_csv(trades, filepath):
    """Save trades to CSV file"""
    if not trades:
        print("No trades to save")
        return
    
    df = pd.DataFrame(trades)
    df.to_csv(filepath, index=False)
    print(f"Saved {len(trades)} trades to: {filepath}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python fetch_quiver_stock_trades.py TICKER     # Scrape specific stock")
        print("  python fetch_quiver_stock_trades.py main       # Scrape main page")
        sys.exit(1)
    
    arg = sys.argv[1].upper()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output CSVs')
    os.makedirs(output_dir, exist_ok=True)
    
    if arg == 'MAIN':
        # Scrape main congresstrading page
        trades = scrape_main_page()
        if trades:
            filepath = os.path.join(output_dir, 'quiver_recent_trades.csv')
            save_to_csv(trades, filepath)
    else:
        # Scrape specific stock
        ticker = arg
        trades = scrape_stock_trades(ticker)
        if trades:
            filepath = os.path.join(output_dir, f'quiver_{ticker}_trades.csv')
            save_to_csv(trades, filepath)
