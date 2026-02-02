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
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# FMP API Configuration (DISABLED - too limited in free tier)
# API_KEY = "EypEpLbJcxfRpdMBFcJppxD2YIEnGD0T"
# FMP_BASE_URL = "https://financialmodelingprep.com/stable"

API_CALL_DELAY = 0.5  # Delay between yfinance calls (reduced for parallel processing)
MAX_WORKERS = 8  # Number of parallel threads for API calls
progress_lock = Lock()  # Thread-safe progress printing


def scrape_ticker_details(ticker, filing_days=30, trade_type='purchase'):
    """
    Fetch individual trades for a specific ticker to get role breakdown
    
    Parameters:
    - ticker: Stock ticker symbol
    - filing_days: Only count trades within this many days
    - trade_type: 'purchase' or 'sale'
    
    Returns:
    - Dictionary with role counts and trade details
    """
    from datetime import datetime, timedelta
    
    url = f"http://openinsider.com/search?q={ticker}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        time.sleep(0.3)  # Rate limiting
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'class': 'tinytable'})
        
        if not table:
            return None
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=filing_days)
        
        role_counts = {
            'COB': 0, 'CEO': 0, 'Pres': 0, 'COO': 0, 'CFO': 0,
            'GC': 0, 'VP': 0, 'Director': 0, 'Owner': 0, 'Other': 0
        }
        
        purchase_trades = []
        rows = table.find_all('tr')[1:]  # Skip header
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 8:
                continue
            
            # Column structure: X | Filing Date | Trade Date | Ticker | Insider Name | Title | Trade Type | Price | ...
            # Parse trade info
            trade_date_str = cols[2].text.strip()
            insider_name = cols[4].text.strip()
            title = cols[5].text.strip()
            trade_type_col = cols[6].text.strip()
            
            # Filter by trade type
            if trade_type == 'purchase':
                if 'P - Purchase' not in trade_type_col:
                    continue
            else:  # sale
                if 'S - Sale' not in trade_type_col:
                    continue
            
            try:
                trade_date = datetime.strptime(trade_date_str, '%Y-%m-%d')
                if trade_date < cutoff_date:
                    continue
            except:
                continue
            
            # Count roles based on title
            title_lower = title.lower()
            
            # Track which role to assign (highest priority)
            assigned_role = None
            
            if 'cob' in title_lower or 'chairman' in title_lower:
                assigned_role = 'COB'
            elif 'ceo' in title_lower or 'chief executive' in title_lower:
                assigned_role = 'CEO'
            elif 'pres' in title_lower or 'president' in title_lower:
                assigned_role = 'Pres'
            elif 'cfo' in title_lower or 'chief financial' in title_lower:
                assigned_role = 'CFO'
            elif 'coo' in title_lower or 'chief operating' in title_lower:
                assigned_role = 'COO'
            elif 'gc' in title_lower or 'general counsel' in title_lower:
                assigned_role = 'GC'
            elif 'vp' in title_lower or 'vice pres' in title_lower:
                assigned_role = 'VP'
            elif 'dir' in title_lower or 'director' in title_lower:
                assigned_role = 'Director'
            elif '10%' in title or 'beneficial' in title_lower:
                assigned_role = 'Owner'
            else:
                assigned_role = 'Other'
            
            purchase_trades.append({
                'date': trade_date_str,
                'title': title,
                'role': assigned_role,
                'insider': insider_name
            })
        
        # Count unique insiders per role (not trades)
        insider_roles = {}
        for trade in purchase_trades:
            insider_name = trade['insider']
            role = trade['role']
            
            # Assign each insider to their highest priority role
            if insider_name not in insider_roles:
                insider_roles[insider_name] = role
            else:
                # Role priority
                priority = {'COB': 10, 'CEO': 9, 'Pres': 8, 'CFO': 7, 'COO': 6,
                           'GC': 5, 'VP': 4, 'Director': 3, 'Owner': 2, 'Other': 1}
                if priority.get(role, 0) > priority.get(insider_roles[insider_name], 0):
                    insider_roles[insider_name] = role
        
        # Count by role
        for insider, role in insider_roles.items():
            role_counts[role] += 1
        
        return {
            'role_counts': role_counts,
            'total_insiders': len(insider_roles),
            'purchase_trades': purchase_trades
        }
        
    except Exception as e:
        print(f"Error fetching details for {ticker}: {e}")
        return None


def scrape_openinsider_simple(page=1, min_price=5, filing_days=30, min_insiders=3, 
                               min_value=150, min_own_change=0, trade_type='purchase'):
    """
    Simplified scraper: Get companies with cluster buying/selling using grouped view
    
    Returns companies that meet the basic criteria. Role breakdown will be
    fetched separately per ticker.
    """
    base_url = "http://openinsider.com/screener"
    
    # Trade type: For sales, use td=0 with xs=1 (xs=1 overrides td)
    # For purchases, use td=0 with no xs parameter
    td_value = '0'  # Always 0
    xs_value = '1' if trade_type == 'sale' else ''
    
    # For sales, ownership change should be positive in API (OpenInsider stores absolute values)
    # But we'll display them as negative in the UI
    own_change_param = str(min_own_change) if min_own_change > 0 else ''
    
    params = {
        's': '', 'o': '', 'pl': str(min_price), 'ph': '',
        'll': '', 'lh': '', 'fd': str(filing_days), 'fdr': '',
        'td': td_value, 'tdr': '', 'fdlyl': '', 'fdlyh': '',
        'daysago': '', 'xp': '1', 'xs': xs_value, 'vl': '', 'vh': '',
        'ocl': '', 'och': '', 'sic1': '-1', 'sicl': '100', 'sich': '9999',  # Exclude funds (SIC < 100)
        'isofficer': '1', 'iscob': '1', 'isceo': '1', 'ispres': '1', 'iscoo': '1', 'iscfo': '1',
        'isgc': '1', 'isvp': '1', 'isdirector': '1', 'istenpercent': '1', 'isother': '1',
        'grp': '2',  # Group by company (works for both purchases and sales)
        'nfl': '', 'nfh': '', 'nil': str(min_insiders), 'nih': '',
        'nol': '', 'noh': '',
        'v2l': str(min_value), 'v2h': '',
        'oc2l': own_change_param, 'oc2h': '',
        'sortcol': '0', 'cnt': '100', 'page': str(page)
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'class': 'tinytable'})
        
        if not table:
            return []
        
        data = []
        rows = table.find_all('tr')[1:]  # Skip header
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 13:
                continue
            
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
            
            data.append(record)
        
        return data
        
    except Exception as e:
        print(f"Error fetching page {page}: {e}")
        return []


def scrape_openinsider_by_role(page=1, min_price=5, filing_days=30, min_value=150,
                                min_own_change=0, role='CEO'):
    """
    Scrape OpenInsider for a specific insider role (ungrouped data)
    
    Parameters:
    - page: Page number to fetch
    - min_price: Minimum stock price
    - filing_days: Filing date within X days
    - min_value: Minimum transaction value in thousands
    - min_own_change: Minimum ownership change percentage
    - role: One of 'COB', 'CEO', 'Pres', 'COO', 'CFO', 'GC', 'VP', 'Director', '10Owner', 'Other'
    
    Returns:
    - List of individual trades with role information
    """
    base_url = "http://openinsider.com/screener"
    
    # Set role-specific filters - OpenInsider uses these parameter names
    role_filters = {
        'COB': {'iscob': '1', 'isceo': '', 'ispres': '', 'iscoo': '', 'iscfo': '', 'isgc': '', 'isvp': '', 'isdirector': '', 'is10be': '', 'isother': ''},
        'CEO': {'iscob': '', 'isceo': '1', 'ispres': '', 'iscoo': '', 'iscfo': '', 'isgc': '', 'isvp': '', 'isdirector': '', 'is10be': '', 'isother': ''},
        'Pres': {'iscob': '', 'isceo': '', 'ispres': '1', 'iscoo': '', 'iscfo': '', 'isgc': '', 'isvp': '', 'isdirector': '', 'is10be': '', 'isother': ''},
        'COO': {'iscob': '', 'isceo': '', 'ispres': '', 'iscoo': '1', 'iscfo': '', 'isgc': '', 'isvp': '', 'isdirector': '', 'is10be': '', 'isother': ''},
        'CFO': {'iscob': '', 'isceo': '', 'ispres': '', 'iscoo': '', 'iscfo': '1', 'isgc': '', 'isvp': '', 'isdirector': '', 'is10be': '', 'isother': ''},
        'GC': {'iscob': '', 'isceo': '', 'ispres': '', 'iscoo': '', 'iscfo': '', 'isgc': '1', 'isvp': '', 'isdirector': '', 'is10be': '', 'isother': ''},
        'VP': {'iscob': '', 'isceo': '', 'ispres': '', 'iscoo': '', 'iscfo': '', 'isgc': '', 'isvp': '1', 'isdirector': '', 'is10be': '', 'isother': ''},
        'Director': {'iscob': '', 'isceo': '', 'ispres': '', 'iscoo': '', 'iscfo': '', 'isgc': '', 'isvp': '', 'isdirector': '1', 'is10be': '', 'isother': ''},
        '10Owner': {'iscob': '', 'isceo': '', 'ispres': '', 'iscoo': '', 'iscfo': '', 'isgc': '', 'isvp': '', 'isdirector': '', 'is10be': '1', 'isother': ''},
        'Other': {'iscob': '', 'isceo': '', 'ispres': '', 'iscoo': '', 'iscfo': '', 'isgc': '', 'isvp': '', 'isdirector': '', 'is10be': '', 'isother': '1'}
    }
    
    role_params = role_filters.get(role, role_filters['CEO'])
    
    params = {
        's': '',
        'o': '',
        'pl': str(min_price),
        'ph': '',
        'll': '',
        'lh': '',
        'fd': str(filing_days),
        'fdr': '',
        'td': '0',
        'tdr': '',
        'fdlyl': '',
        'fdlyh': '',
        'daysago': '',
        'xp': '1',
        'vl': '',
        'vh': '',
        'ocl': '',
        'och': '',
        'sic1': '-1',
        'sicl': '',
        'sich': '',
        **role_params,  # Apply role-specific filters
        'grp': '0',     # NO grouping - get individual trades
        'nfl': '',
        'nfh': '',
        'nil': '',      # Don't filter by number of insiders here
        'nih': '',
        'nol': '',
        'noh': '',
        'v2l': str(min_value),
        'v2h': '',
        'oc2l': str(min_own_change) if min_own_change > 0 else '',
        'oc2h': '',
        'sortcol': '0',
        'cnt': '100',
        'page': str(page)
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'class': 'tinytable'})
        
        if not table:
            return []
        
        data = []
        rows = table.find_all('tr')[1:]  # Skip header
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 11:
                continue
            
            # Ungrouped format (grp=0) has different column order than grouped
            # Columns: X | Filing Date | Trade Date | Ticker | Company | Insider Name | Title | Trade Type | Price | Qty | Owned | ΔOwn | Value
            record = {
                'X': cols[0].text.strip(),
                'Filing_Date': cols[1].text.strip(),
                'Trade_Date': cols[2].text.strip(),
                'Ticker': cols[3].text.strip(),
                'Company_Name': cols[4].text.strip(),
                'Insider_Name': cols[5].text.strip() if len(cols) > 5 else '',  # Individual insider name
                'Role': role,  # Add role tag
                'Trade_Type': cols[7].text.strip() if len(cols) > 7 else '',
                'Price': cols[8].text.strip() if len(cols) > 8 else '',
                'Qty': cols[9].text.strip() if len(cols) > 9 else '',
                'Owned': cols[10].text.strip() if len(cols) > 10 else '',
                'Delta_Own': cols[11].text.strip() if len(cols) > 11 else '',
                'Value': cols[12].text.strip() if len(cols) > 12 else ''
            }
            
            data.append(record)
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {role} data: {e}")
        return []


def aggregate_insider_trades(all_trades, min_insiders=3):
    """
    Aggregate individual insider trades by company with role breakdown
    
    Parameters:
    - all_trades: List of individual trades from multiple role queries
    - min_insiders: Minimum total number of insiders required
    
    Returns:
    - List of aggregated company records with role breakdowns
    """
    from collections import defaultdict
    
    # Group by ticker
    ticker_groups = defaultdict(lambda: {
        'trades': [],
        'unique_trades': {},  # Key: (insider_name, trade_date, value) to dedupe
        'insider_roles': {},  # Track primary role for each insider
        'COB_count': 0,
        'CEO_count': 0,
        'Pres_count': 0,
        'COO_count': 0,
        'CFO_count': 0,
        'GC_count': 0,
        'VP_count': 0,
        'Director_count': 0,
        'Owner_count': 0,
        'Other_count': 0,
        'insider_names': set()
    })
    
    # Role priority for classification (higher = more important)
    role_priority = {
        'COB': 10, 'CEO': 9, 'Pres': 8, 'CFO': 7, 'COO': 6, 
        'GC': 5, 'VP': 4, 'Director': 3, '10Owner': 2, 'Other': 1
    }
    
    for trade in all_trades:
        ticker = trade['Ticker']
        role = trade['Role']
        insider_name = trade['Insider_Name']
        trade_date = trade['Trade_Date']
        value = trade.get('Value', '')
        
        # Create unique key to avoid double-counting same trade
        trade_key = (insider_name, trade_date, value)
        
        # Only add if this exact trade hasn't been seen before
        if trade_key not in ticker_groups[ticker]['unique_trades']:
            ticker_groups[ticker]['unique_trades'][trade_key] = trade
            ticker_groups[ticker]['trades'].append(trade)
        
        # Track insider names
        ticker_groups[ticker]['insider_names'].add(insider_name)
        
        # Assign insider to their highest priority role
        current_role = ticker_groups[ticker]['insider_roles'].get(insider_name)
        if current_role is None or role_priority.get(role, 0) > role_priority.get(current_role, 0):
            ticker_groups[ticker]['insider_roles'][insider_name] = role
    
    # Now count roles based on primary assignments
    for ticker, group in ticker_groups.items():
        for insider_name, role in group['insider_roles'].items():
            if role == 'COB':
                group['COB_count'] += 1
            elif role == 'CEO':
                group['CEO_count'] += 1
            elif role == 'Pres':
                group['Pres_count'] += 1
            elif role == 'CFO':
                group['CFO_count'] += 1
            elif role == 'COO':
                group['COO_count'] += 1
            elif role == 'GC':
                group['GC_count'] += 1
            elif role == 'VP':
                group['VP_count'] += 1
            elif role == 'Director':
                group['Director_count'] += 1
            elif role == '10Owner':
                group['Owner_count'] += 1
            elif role == 'Other':
                group['Other_count'] += 1
    
    # Aggregate and filter
    aggregated = []
    
    for ticker, group in ticker_groups.items():
        total_insiders = len(group['insider_names'])
        
        # Filter by minimum insiders
        if total_insiders < min_insiders:
            continue
        
        # Get the most recent trade for basic info
        trades = sorted(group['trades'], key=lambda x: x['Trade_Date'], reverse=True)
        latest = trades[0]
        
        # Calculate total value and quantities
        total_value = 0
        total_qty = 0
        delta_own_sum = 0
        delta_own_count = 0
        
        for trade in trades:
            try:
                # Parse value - format is like "+$150,000" or "$150000"
                value_str = trade['Value'].replace('+$', '').replace('$', '').replace(',', '').replace('k', '000').strip()
                if value_str:
                    total_value += float(value_str)
            except Exception as e:
                pass
            
            try:
                qty_str = trade['Qty'].replace('+', '').replace(',', '').strip()
                if qty_str:
                    total_qty += int(qty_str)
            except:
                pass
            
            try:
                # Parse Delta_Own percentage - format is like "+5%" or "5%"
                delta_str = trade['Delta_Own'].replace('+', '').replace('%', '').strip()
                if delta_str:
                    delta_own_sum += float(delta_str)
                    delta_own_count += 1
            except:
                pass
        
        # Calculate average Delta_Own
        avg_delta_own = (delta_own_sum / delta_own_count) if delta_own_count > 0 else 0
        
        # Create aggregated record
        aggregated_record = {
            'Ticker': ticker,
            'Company_Name': latest['Company_Name'],
            'Trade_Date': latest['Trade_Date'],
            'Filing_Date': latest['Filing_Date'],
            'Total_Insiders': total_insiders,
            'COB_Count': group['COB_count'],
            'CEO_Count': group['CEO_count'],
            'Pres_Count': group['Pres_count'],
            'CFO_Count': group['CFO_count'],
            'COO_Count': group['COO_count'],
            'GC_Count': group['GC_count'],
            'VP_Count': group['VP_count'],
            'Director_Count': group['Director_count'],
            'Owner_Count': group['Owner_count'],
            'Other_Count': group['Other_count'],
            'Total_Value': f"+${int(total_value):,}",
            'Total_Qty': f"+{total_qty:,}",
            'Price': latest['Price'],
            'Owned': latest['Owned'],
            'Delta_Own': f"+{avg_delta_own:.1f}%" if avg_delta_own > 0 else f"{avg_delta_own:.1f}%",
            'Trade_Type': 'P - Purchase'
        }
        
        aggregated.append(aggregated_record)
    
    return aggregated


def scrape_openinsider(page=1, min_price=5, filing_days=30, min_insiders=3, min_value=150,
                       min_own_change=0, include_cob=True, include_ceo=True, include_pres=True, 
                       include_coo=True, include_cfo=True, include_gc=True, include_vp=True,
                       include_director=True, include_10owner=True, include_other=True):
    """
    Scrape OpenInsider with role breakdown by fetching each role separately
    
    Parameters:
    - page: Page number to fetch (default: 1)
    - min_price: Minimum stock price (default: 5)
    - filing_days: Filing date within X days (default: 30)
    - min_insiders: Minimum number of insiders (default: 3)
    - min_value: Minimum transaction value in thousands (default: 150)
    - min_own_change: Minimum ownership change percentage (default: 0)
    - include_cob: Include COB trades (default: True)
    - include_ceo: Include CEO trades (default: True)
    - include_pres: Include President trades (default: True)
    - include_coo: Include COO trades (default: True)
    - include_cfo: Include CFO trades (default: True)
    - include_gc: Include GC trades (default: True)
    - include_vp: Include VP trades (default: True)
    - include_director: Include Director trades (default: True)
    - include_10owner: Include 10% Owner trades (default: True)
    - include_other: Include Other trades (default: True)
    
    Returns:
    - List of dictionaries containing aggregated insider trading data with role breakdowns
    """
    
    print(f"\n🔍 Fetching page {page} with role breakdown...")
    
    all_trades = []
    roles_to_fetch = []
    
    if include_cob: roles_to_fetch.append('COB')
    if include_ceo: roles_to_fetch.append('CEO')
    if include_pres: roles_to_fetch.append('Pres')
    if include_coo: roles_to_fetch.append('COO')
    if include_cfo: roles_to_fetch.append('CFO')
    if include_gc: roles_to_fetch.append('GC')
    if include_vp: roles_to_fetch.append('VP')
    if include_director: roles_to_fetch.append('Director')
    if include_10owner: roles_to_fetch.append('10Owner')
    if include_other: roles_to_fetch.append('Other')
    
    # Fetch trades for each role
    for role in roles_to_fetch:
        print(f"  Fetching {role} trades...")
        role_trades = scrape_openinsider_by_role(
            page=page,
            min_price=min_price,
            filing_days=filing_days,
            min_value=min_value,
            min_own_change=min_own_change,
            role=role
        )
        all_trades.extend(role_trades)
        print(f"    Found {len(role_trades)} {role} trades")
        time.sleep(0.5)  # Rate limiting
    
    # Aggregate by company with role breakdown
    print(f"  Aggregating {len(all_trades)} total trades by company...")
    aggregated = aggregate_insider_trades(all_trades, min_insiders=min_insiders)
    
    # Filter by minimum total value (convert from $k to dollars)
    min_value_dollars = min_value * 1000
    filtered = []
    for company in aggregated:
        try:
            # Parse the total value
            value_str = company['Total_Value'].replace('+$', '').replace('$', '').replace(',', '').strip()
            if value_str and float(value_str) >= min_value_dollars:
                filtered.append(company)
            else:
                print(f"    Filtered out {company['Ticker']} (${float(value_str):,.0f} < ${min_value_dollars:,.0f})")
        except:
            filtered.append(company)  # Keep if can't parse
    
    aggregated = filtered
    print(f"  ✅ Found {len(aggregated)} companies meeting criteria")
    
    # Convert to format compatible with existing enrichment code
    data = []
    for record in aggregated:
        formatted_record = {
            'X': '',
            'Filing_Date': record['Filing_Date'],
            'Trade_Date': record['Trade_Date'],
            'Ticker': record['Ticker'],
            'Company_Name': record['Company_Name'],
            'Industry': '',
            'Insiders': str(record['Total_Insiders']),
            'COB_Count': record['COB_Count'],
            'CEO_Count': record['CEO_Count'],
            'Pres_Count': record['Pres_Count'],
            'CFO_Count': record['CFO_Count'],
            'COO_Count': record['COO_Count'],
            'GC_Count': record['GC_Count'],
            'VP_Count': record['VP_Count'],
            'Director_Count': record['Director_Count'],
            'Owner_Count': record['Owner_Count'],
            'Other_Count': record['Other_Count'],
            'Trade_Type': record['Trade_Type'],
            'Price': record['Price'],
            'Qty': record['Total_Qty'],
            'Owned': record['Owned'],
            'Delta_Own': record['Delta_Own'],
            'Value': record['Total_Value']
        }
        data.append(formatted_record)
    
    return data


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
        filename = "openinsider_data_latest.csv"
    
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
    Returns: Ratios, Metrics, Profile data, Institutional Holdings
    """
    try:
        time.sleep(API_CALL_DELAY)  # Be respectful to Yahoo
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get institutional holders
        institutional_holders = None
        institutional_ownership_pct = 'N/A'
        try:
            inst_holders = stock.institutional_holders
            if inst_holders is not None and not inst_holders.empty:
                institutional_holders = inst_holders
                # Calculate total institutional ownership
                institutional_ownership_pct = info.get('heldPercentInstitutions', 'N/A')
        except:
            pass
        
        # Get current price
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
        
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
            
            # Institutional Data (NEW)
            'institutional_ownership_pct': institutional_ownership_pct,
            'institutional_holders': institutional_holders,
            
            # Price Data (NEW)
            'current_price': current_price,
        }
        
    except Exception as e:
        print(f"  Error fetching yfinance data for {ticker}: {str(e)[:80]}")
        return None


def calculate_rainy_day_score(record, yf_data):
    """
    Calculate the Rainy Day Score (1-10) for bubble burst strategy
    
    Scoring:
    +3 points for 3+ Insiders
    +3 points if Debt/Equity < 100
    +2 points if Sector is "Defensive" (Financials, Healthcare, Consumer Staples, Utilities)
    +2 points if Price is > 20% below Analyst Targets
    """
    score = 0
    reasons = []
    
    # +3 for 3+ insiders
    try:
        insiders_count = int(record.get('Insiders', 0))
        if insiders_count >= 3:
            score += 3
            reasons.append(f"{insiders_count} Insiders")
    except:
        pass
    
    # +3 for low debt (< 100)
    if yf_data:
        debt_eq = yf_data['debt_to_equity']
        if debt_eq != 'N/A' and debt_eq < 100:
            score += 3
            reasons.append("Low Debt")
        
        # +2 for defensive sector
        sector = yf_data['sector']
        defensive_sectors = ['Financial Services', 'Healthcare', 'Consumer Defensive', 
                           'Utilities', 'Consumer Staples']
        if sector in defensive_sectors:
            score += 2
            reasons.append("Defensive Sector")
        
        # +2 if price is > 20% below analyst target
        current_price = yf_data['current_price']
        target_mean = yf_data['target_mean_price']
        if current_price != 'N/A' and target_mean != 'N/A' and target_mean > 0:
            discount = ((target_mean - current_price) / target_mean) * 100
            if discount >= 20:
                score += 2
                reasons.append(f"{discount:.1f}% Below Target")
    
    return score, reasons


def parse_delta_own(delta_own_str):
    """Parse Delta_Own percentage string to float"""
    try:
        # Remove '+' and '%' characters
        clean_str = delta_own_str.replace('+', '').replace('%', '').strip()
        return float(clean_str)
    except:
        return 0.0


def enrich_single_record(record, idx, total):
    """
    Enrich a single record with financial data (for parallel processing)
    """
    ticker = record.get('Ticker', '').strip()
    
    if not ticker:
        return record
    
    with progress_lock:
        print(f"\n[{idx}/{total}] Analyzing {ticker}...")
    
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
            
            # NEW: Institutional Data
            'Institutional_Ownership_Pct': yf_data['institutional_ownership_pct'],
            'Current_Price': yf_data['current_price'],
        })
        
        # NEW: Skin in the Game Filter - Check Delta_Own
        delta_own = parse_delta_own(record.get('Delta_Own', '0'))
        skin_in_game = "YES" if delta_own >= 5 else "NO"
        enriched_record['Skin_in_Game'] = skin_in_game
        
        # NEW: Beta Classification (Macro Hedge)
        beta = yf_data['beta']
        if beta != 'N/A':
            if beta < 1.0:
                beta_class = "Safe (Low Volatility)"
            elif beta > 1.5:
                beta_class = "Risky (High Volatility)"
            else:
                beta_class = "Market Aligned"
        else:
            beta_class = "N/A"
        enriched_record['Beta_Classification'] = beta_class
        
        # NEW: Whale Check (Institutional Stability)
        inst_own = yf_data['institutional_ownership_pct']
        if inst_own != 'N/A':
            if inst_own > 0.5:  # > 50%
                whale_status = "Stabilized (Institutions > 50%)"
            elif inst_own > 0.3:
                whale_status = "Moderate Institutional Support"
            else:
                whale_status = "Low Institutional Interest"
        else:
            whale_status = "N/A"
        enriched_record['Whale_Status'] = whale_status
        
        # NEW: Sector Classification (Defensive vs Aggressive)
        sector = yf_data['sector']
        defensive_sectors = ['Financial Services', 'Healthcare', 'Consumer Defensive', 
                           'Utilities', 'Consumer Staples']
        aggressive_sectors = ['Technology', 'Communication Services']
        
        if sector in defensive_sectors:
            sector_type = "DEFENSIVE (Safe Haven)"
        elif sector in aggressive_sectors:
            sector_type = "AGGRESSIVE (AI Bubble Risk)"
        else:
            sector_type = "NEUTRAL"
        enriched_record['Sector_Type'] = sector_type
        
        # NEW: Calculate Rainy Day Score
        rainy_day_score, score_reasons = calculate_rainy_day_score(record, yf_data)
        enriched_record['Rainy_Day_Score'] = rainy_day_score
        enriched_record['Score_Reasons'] = ' | '.join(score_reasons) if score_reasons else 'N/A'
        
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
        
        # Add Skin in the Game badge
        if skin_in_game == "YES":
            health_flags.append('💎 HIGH CONVICTION (Skin in Game)')
        
        enriched_record['Health_Flags'] = ' | '.join(health_flags) if health_flags else 'N/A'
    else:
        # Failed to fetch data
        enriched_record.update({
            'Health_Flags': 'N/A',
            'Skin_in_Game': 'N/A',
            'Beta_Classification': 'N/A',
            'Whale_Status': 'N/A',
            'Sector_Type': 'N/A',
            'Rainy_Day_Score': 0,
            'Score_Reasons': 'N/A'
        })
    
    return enriched_record


def enrich_with_financial_data(insider_data):
    """
    Enrich insider trading data with financial health metrics using yfinance
    Uses parallel processing for speed
    """
    print("\n" + "=" * 50)
    print(f"Fetching Financial Data (yfinance - FREE)")
    print(f"Using {MAX_WORKERS} parallel threads for speed...")
    print("=" * 50)
    
    enriched_data = []
    total = len(insider_data)
    
    # Use ThreadPoolExecutor for parallel API calls
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_record = {
            executor.submit(enrich_single_record, record, idx, total): record
            for idx, record in enumerate(insider_data, 1)
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_record):
            try:
                enriched_record = future.result()
                enriched_data.append(enriched_record)
            except Exception as e:
                record = future_to_record[future]
                ticker = record.get('Ticker', 'Unknown')
                print(f"\n❌ Error processing {ticker}: {str(e)}")
                enriched_data.append(record)
    
    # Sort by Rainy Day Score (highest first)
    enriched_data.sort(key=lambda x: x.get('Rainy_Day_Score', 0), reverse=True)
    
    print("\n" + "=" * 50)
    print("✅ All stocks analyzed!")
    print("=" * 50)
    
    return enriched_data


def main():
    """Main function to scrape and save OpenInsider data"""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Scrape OpenInsider with custom filters')
    parser.add_argument('--min-price', type=float, default=5, help='Minimum stock price (default: 5)')
    parser.add_argument('--filing-days', type=int, default=30, help='Filing date within X days (default: 30)')
    parser.add_argument('--min-insiders', type=int, default=3, help='Minimum number of insiders (default: 3)')
    parser.add_argument('--min-value', type=int, default=150, help='Minimum transaction value in thousands (default: 150)')
    parser.add_argument('--min-own-change', type=int, default=0, help='Minimum ownership change percentage (default: 0)')
    parser.add_argument('--trade-type', type=str, default='purchase', choices=['purchase', 'sale'], help='Trade type to search for (default: purchase)')
    parser.add_argument('--include-cob', type=int, default=1, help='Include COB trades (1=yes, 0=no, default: 1)')
    parser.add_argument('--include-ceo', type=int, default=1, help='Include CEO trades (1=yes, 0=no, default: 1)')
    parser.add_argument('--include-pres', type=int, default=1, help='Include President trades (1=yes, 0=no, default: 1)')
    parser.add_argument('--include-coo', type=int, default=1, help='Include COO trades (1=yes, 0=no, default: 1)')
    parser.add_argument('--include-cfo', type=int, default=1, help='Include CFO trades (1=yes, 0=no, default: 1)')
    parser.add_argument('--include-gc', type=int, default=1, help='Include GC trades (1=yes, 0=no, default: 1)')
    parser.add_argument('--include-vp', type=int, default=1, help='Include VP trades (1=yes, 0=no, default: 1)')
    parser.add_argument('--include-director', type=int, default=1, help='Include Director trades (1=yes, 0=no, default: 1)')
    parser.add_argument('--include-10owner', type=int, default=1, help='Include 10% Owner trades (1=yes, 0=no, default: 1)')
    parser.add_argument('--include-other', type=int, default=1, help='Include Other trades (1=yes, 0=no, default: 1)')
    
    args = parser.parse_args()
    
    enabled_roles = []
    if args.include_cob: enabled_roles.append('COB')
    if args.include_ceo: enabled_roles.append('CEO')
    if args.include_pres: enabled_roles.append('Pres')
    if args.include_coo: enabled_roles.append('COO')
    if args.include_cfo: enabled_roles.append('CFO')
    if args.include_gc: enabled_roles.append('GC')
    if args.include_vp: enabled_roles.append('VP')
    if args.include_director: enabled_roles.append('Director')
    if args.include_10owner: enabled_roles.append('10% Owner')
    if args.include_other: enabled_roles.append('Other')
    
    print("OpenInsider Screener + Financial Health Analyzer")
    print("=" * 50)
    print("\nFilters applied:")
    print(f"- Trade Type: {args.trade_type.capitalize()}")
    print(f"- Minimum price: ${args.min_price}")
    print(f"- Filing date: Last {args.filing_days} days")
    print(f"- Insiders: {', '.join(enabled_roles)}")
    print(f"- Minimum insiders: {args.min_insiders}")
    print(f"- Minimum value: ${args.min_value}k+")
    if args.min_own_change > 0:
        if args.trade_type == 'purchase':
            print(f"- Minimum ownership change: +{args.min_own_change}%+")
        else:
            print(f"- Minimum ownership change: -{args.min_own_change}% or more (sold at least {args.min_own_change}%)")
    print("\nFinancial Metrics (yfinance - FREE):") 
    print("- Debt-to-Equity, Current Ratio, Quick Ratio, ROE")
    print("- Profit & Operating Margins")
    print("- PE, PEG, Price-to-Book Ratios")
    print("- Analyst Price Targets & Recommendations")
    print("- Market Cap, Beta, Sector, Industry")
    print("=" * 50)
    print()
    
    # Step 1: Get companies with cluster buying using simple grouped view
    all_companies = []
    page = 1
    max_pages = 10
    
    while page <= max_pages:
        print(f"\n📊 Fetching companies page {page} (grouped view)...")
        companies = scrape_openinsider_simple(
            page=page,
            min_price=args.min_price,
            filing_days=args.filing_days,
            min_insiders=args.min_insiders,
            min_value=args.min_value,
            min_own_change=args.min_own_change,
            trade_type=args.trade_type
        )
        
        if not companies:
            print(f"No more companies found. Stopping at page {page - 1}.")
            break
        
        print(f"  Found {len(companies)} companies on this page")
        all_companies.extend(companies)
        page += 1
        
        if page <= max_pages:
            time.sleep(2)
    
    # Deduplicate by ticker
    unique_companies = {}
    for company in all_companies:
        ticker = company['Ticker']
        if ticker not in unique_companies:
            unique_companies[ticker] = company
        else:
            # Keep more recent trade
            existing_date = unique_companies[ticker].get('Trade_Date', '')
            new_date = company.get('Trade_Date', '')
            if new_date > existing_date:
                unique_companies[ticker] = company
    
    all_companies = list(unique_companies.values())
    trade_action = "buying" if args.trade_type == 'purchase' else "selling"
    print(f"\n✅ Found {len(all_companies)} unique companies with cluster {trade_action}")
    
    # Step 2: For each company, fetch individual trades to get role breakdown
    print(f"\n🔍 Fetching role breakdown for each company...")
    enriched_companies = []
    
    for idx, company in enumerate(all_companies, 1):
        ticker = company['Ticker']
        print(f"\n  [{idx}/{len(all_companies)}] {ticker}: {company['Company_Name']}")
        
        # Get individual trades and role breakdown
        details = scrape_ticker_details(ticker, filing_days=args.filing_days, trade_type=args.trade_type)
        
        if details:
            # Filter by enabled roles
            role_counts = details['role_counts']
            
            # Apply role filters
            if not args.include_cob:
                role_counts['COB'] = 0
            if not args.include_ceo:
                role_counts['CEO'] = 0
            if not args.include_pres:
                role_counts['Pres'] = 0
            if not args.include_coo:
                role_counts['COO'] = 0
            if not args.include_cfo:
                role_counts['CFO'] = 0
            if not args.include_gc:
                role_counts['GC'] = 0
            if not args.include_vp:
                role_counts['VP'] = 0
            if not args.include_director:
                role_counts['Director'] = 0
            if not args.include_10owner:
                role_counts['Owner'] = 0
            if not args.include_other:
                role_counts['Other'] = 0
            
            # Count remaining insiders after filtering
            remaining_insiders = sum(role_counts.values())
            
            # Check if still meets minimum insiders requirement
            if remaining_insiders < args.min_insiders:
                print(f"    ⏭️  Skipped (only {remaining_insiders} insiders after role filtering)")
                continue
            
            # Add role breakdown to company record
            company['COB_Count'] = role_counts['COB']
            company['CEO_Count'] = role_counts['CEO']
            company['Pres_Count'] = role_counts['Pres']
            company['CFO_Count'] = role_counts['CFO']
            company['COO_Count'] = role_counts['COO']
            company['GC_Count'] = role_counts['GC']
            company['VP_Count'] = role_counts['VP']
            company['Director_Count'] = role_counts['Director']
            company['Owner_Count'] = role_counts['Owner']
            company['Other_Count'] = role_counts['Other']
            company['Insiders'] = str(remaining_insiders)
            
            print(f"    ✅ {remaining_insiders} insiders: ", end='')
            breakdown = []
            if role_counts['COB'] > 0:
                breakdown.append(f"COB({role_counts['COB']})")
            if role_counts['CEO'] > 0:
                breakdown.append(f"CEO({role_counts['CEO']})")
            if role_counts['Pres'] > 0:
                breakdown.append(f"Pres({role_counts['Pres']})")
            if role_counts['CFO'] > 0:
                breakdown.append(f"CFO({role_counts['CFO']})")
            if role_counts['COO'] > 0:
                breakdown.append(f"COO({role_counts['COO']})")
            if role_counts['GC'] > 0:
                breakdown.append(f"GC({role_counts['GC']})")
            if role_counts['VP'] > 0:
                breakdown.append(f"VP({role_counts['VP']})")
            if role_counts['Director'] > 0:
                breakdown.append(f"Dir({role_counts['Director']})")
            if role_counts['Owner'] > 0:
                breakdown.append(f"10Own({role_counts['Owner']})")
            if role_counts['Other'] > 0:
                breakdown.append(f"Other({role_counts['Other']})")
            print(', '.join(breakdown))
            
            enriched_companies.append(company)
        else:
            print(f"    ❌ Could not fetch details")
            # Add empty role counts
            company['COB_Count'] = 0
            company['CEO_Count'] = 0
            company['Pres_Count'] = 0
            company['CFO_Count'] = 0
            company['COO_Count'] = 0
            company['GC_Count'] = 0
            company['VP_Count'] = 0
            company['Director_Count'] = 0
            company['Owner_Count'] = 0
            company['Other_Count'] = 0
            enriched_companies.append(company)
    
    all_data = enriched_companies
    print(f"\n✅ {len(all_data)} companies meet all criteria with role breakdown")
    
    # Enrich with financial data
    if all_data:
        enriched_data = enrich_with_financial_data(all_data)
        save_to_csv(enriched_data)
    else:
        print("No data was scraped. Please check the filters or website availability.")


if __name__ == "__main__":
    main()
