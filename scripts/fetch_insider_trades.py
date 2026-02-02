#!/usr/bin/env python3
"""
Fetch Insider Trades from OpenInsider
======================================
This script fetches all insider trading activity for a specific ticker from OpenInsider.
It returns purchases (P) and sales (S) with dates and amounts to overlay on stock charts.
"""

import requests
from bs4 import BeautifulSoup
import sys
import json
from datetime import datetime, timedelta
import time


def fetch_insider_trades(ticker_symbol, days_back=1461):
    """
    Fetch insider trading data for a specific ticker from OpenInsider.
    
    Args:
        ticker_symbol: Stock ticker (e.g., 'AAPL', 'GME')
        days_back: How many days back to look (default: 1461 = ~4 years)
    
    Returns:
        JSON object with:
        - ticker: Symbol
        - purchases: Array of {date, shares, value, insider_name, title}
        - sales: Array of {date, shares, value, insider_name, title}
        - success: Boolean
        - error: Error message if failed
    """
    try:
        # Build OpenInsider URL for specific ticker
        # To get BOTH purchases and sales: use td=0 with NO xs parameter
        # Removed xp=1 to include all transaction types (it was too restrictive)
        url = (
            f"http://openinsider.com/screener"
            f"?s={ticker_symbol.upper()}"
            f"&o=&pl=&ph=&ll=&lh=&fd={days_back}&fdr=&td=0&tdr="
            f"&fdlyl=&fdlyh=&daysago="  # NO xp to get all transactions
            f"&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999"
            f"&isofficer=1&iscob=1&isceo=1&ispres=1&iscoo=1&iscfo=1"
            f"&isgc=1&isvp=1&isdirector=1&istenpercent=1&isother=1"
            f"&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h="
            f"&sortcol=0&cnt=1000&page=1"  # Get up to 1000 transactions
        )
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the main data table
        table = soup.find('table', {'class': 'tinytable'})
        
        if not table:
            return {
                "success": False,
                "error": f"No insider trading data found for {ticker_symbol}",
                "ticker": ticker_symbol
            }
        
        purchases = []
        sales = []
        
        rows = table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 10:
                continue
            
            try:
                # Extract data from columns
                # Column layout: X | Filing Date | Trade Date | Ticker | Insider | Title | Type | Price | Shares | Owned | ΔOwn% | Value | ...
                # cols[0]=X, cols[1]=Filing, cols[2]=Trade Date, cols[3]=Ticker, cols[4]=Insider, cols[5]=Title,
                # cols[6]=Type, cols[7]=Price, cols[8]=Shares, cols[9]=Owned, cols[10]=ΔOwn%, cols[11]=Value
                trade_type_col = cols[6]  # Transaction type
                trade_date_col = cols[2]  # Trade date
                insider_name_col = cols[4]  # Insider name
                title_col = cols[5]  # Title
                shares_col = cols[8]  # Shares traded
                value_col = cols[11]  # Value (dollar amount of change)
                
                trade_type = trade_type_col.text.strip()
                
                # Only process P (Purchase) and S (Sale)
                # Skip S - Sale+OE and F - Tax
                if trade_type not in ['P - Purchase', 'S - Sale']:
                    continue
                
                trade_date_str = trade_date_col.text.strip()
                insider_name = insider_name_col.text.strip()
                title = title_col.text.strip()
                shares_text = shares_col.text.strip().replace(',', '')
                value_text = value_col.text.strip()
                
                # Parse date
                try:
                    trade_date = datetime.strptime(trade_date_str, '%Y-%m-%d')
                    trade_date_formatted = trade_date.strftime('%Y-%m-%d')
                except:
                    continue
                
                # Parse shares (remove + signs and convert to int)
                try:
                    shares = int(shares_text.replace('+', '').replace('-', ''))
                except:
                    shares = 0
                
                # Parse value (handle $, commas, etc.)
                try:
                    value = float(value_text.replace('$', '').replace(',', '').replace('+', '').replace('-', ''))
                except:
                    value = 0
                
                trade_data = {
                    "date": trade_date_formatted,
                    "shares": shares,
                    "value": value,
                    "insider_name": insider_name,
                    "title": title
                }
                
                if trade_type == 'P - Purchase':
                    purchases.append(trade_data)
                elif trade_type == 'S - Sale':
                    sales.append(trade_data)
                    
            except Exception as e:
                # Skip rows that can't be parsed
                continue
        
        # Sort by date (oldest first for chart overlay)
        purchases.sort(key=lambda x: x['date'])
        sales.sort(key=lambda x: x['date'])
        
        return {
            "success": True,
            "ticker": ticker_symbol,
            "purchases": purchases,
            "sales": sales,
            "total_purchases": len(purchases),
            "total_sales": len(sales),
            "purchase_volume": sum(p['shares'] for p in purchases),
            "sale_volume": sum(s['shares'] for s in sales),
            "purchase_value": sum(p['value'] for p in purchases),
            "sale_value": sum(s['value'] for s in sales)
        }
        
    except requests.Timeout:
        return {
            "success": False,
            "error": "Request timed out while fetching insider data",
            "ticker": ticker_symbol
        }
    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"Failed to fetch insider data: {str(e)}",
            "ticker": ticker_symbol
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "ticker": ticker_symbol
        }


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python fetch_insider_trades.py <TICKER> [DAYS_BACK]"
        }))
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    days_back = int(sys.argv[2]) if len(sys.argv) > 2 else 1461
    
    result = fetch_insider_trades(ticker, days_back)
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
