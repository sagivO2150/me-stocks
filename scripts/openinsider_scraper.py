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

# FMP API Configuration (DISABLED - too limited in free tier)
# API_KEY = "EypEpLbJcxfRpdMBFcJppxD2YIEnGD0T"
# FMP_BASE_URL = "https://financialmodelingprep.com/stable"

API_CALL_DELAY = 1.0  # Delay between yfinance calls (be respectful)


def scrape_openinsider(page=1, min_price=5, filing_days=30, min_insiders=3, min_value=150,
                       include_ceo=True, include_coo=True, include_cfo=True, include_director=True):
    """
    Scrape OpenInsider with the specified filters
    
    Parameters:
    - page: Page number to fetch (default: 1)
    - min_price: Minimum stock price (default: 5)
    - filing_days: Filing date within X days (default: 30)
    - min_insiders: Minimum number of insiders (default: 3)
    - min_value: Minimum transaction value in thousands (default: 150)
    - include_ceo: Include CEO trades (default: True)
    - include_coo: Include COO trades (default: True)
    - include_cfo: Include CFO trades (default: True)
    - include_director: Include Director trades (default: True)
    
    Returns:
    - List of dictionaries containing insider trading data
    """
    
    # Base URL and parameters from your request
    base_url = "http://openinsider.com/screener"
    
    params = {
        's': '',
        'o': '',
        'pl': str(min_price),          # Minimum price
        'ph': '',
        'll': '',
        'lh': '',
        'fd': str(filing_days),         # Filing date within X days
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
        'isceo': '1' if include_ceo else '',       # Include CEO
        'iscoo': '1' if include_coo else '',       # Include COO
        'iscfo': '1' if include_cfo else '',       # Include CFO
        'isdirector': '1' if include_director else '',  # Include Director
        'grp': '2',
        'nfl': '',
        'nfh': '',
        'nil': str(min_insiders),         # Number of insiders
        'nih': '',
        'nol': '1',
        'noh': '',
        'v2l': str(min_value),       # Volume filter
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
            
            # High Conviction Flag (NEW)
            if skin_in_game == "YES":
                health_flags.append('💎 HIGH CONVICTION (Skin in Game)')
            
            enriched_record['Health_Flags'] = ' | '.join(health_flags) if health_flags else 'N/A'
            
            # Print summary
            print(f"  Rainy Day Score: {rainy_day_score}/10 - {', '.join(score_reasons) if score_reasons else 'No bonus points'}")
            print(f"  Sector: {sector_type}")
            print(f"  Skin in Game: {skin_in_game} (Δ Own: {delta_own}%)")
            print(f"  Beta: {beta_class}")
            print(f"  Institutions: {whale_status}")
            if health_flags:
                print(f"  Health: {' | '.join(health_flags)}")
        else:
            enriched_record['Health_Flags'] = 'N/A'
            enriched_record['Rainy_Day_Score'] = 0
            enriched_record['Skin_in_Game'] = 'N/A'
            enriched_record['Beta_Classification'] = 'N/A'
            enriched_record['Whale_Status'] = 'N/A'
            enriched_record['Sector_Type'] = 'N/A'
            enriched_record['Score_Reasons'] = 'N/A'
        
        enriched_data.append(enriched_record)
    
    # Sort by Rainy Day Score (highest first)
    enriched_data.sort(key=lambda x: x.get('Rainy_Day_Score', 0), reverse=True)
    
    return enriched_data


def main():
    """Main function to scrape and save OpenInsider data"""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Scrape OpenInsider with custom filters')
    parser.add_argument('--min-price', type=float, default=5, help='Minimum stock price (default: 5)')
    parser.add_argument('--filing-days', type=int, default=30, help='Filing date within X days (default: 30)')
    parser.add_argument('--min-insiders', type=int, default=3, help='Minimum number of insiders (default: 3)')
    parser.add_argument('--min-value', type=int, default=150, help='Minimum transaction value in thousands (default: 150)')
    parser.add_argument('--include-ceo', type=int, default=1, help='Include CEO trades (1=yes, 0=no, default: 1)')
    parser.add_argument('--include-coo', type=int, default=1, help='Include COO trades (1=yes, 0=no, default: 1)')
    parser.add_argument('--include-cfo', type=int, default=1, help='Include CFO trades (1=yes, 0=no, default: 1)')
    parser.add_argument('--include-director', type=int, default=1, help='Include Director trades (1=yes, 0=no, default: 1)')
    parser.add_argument('--num-pages', type=int, default=1, help='Number of pages to scrape (default: 1)')
    
    args = parser.parse_args()
    
    print("OpenInsider Screener + Financial Health Analyzer")
    print("=" * 50)
    print("\nFilters applied:")
    print(f"- Minimum price: ${args.min_price}")
    print(f"- Filing date: Last {args.filing_days} days")
    print(f"- Insiders: {', '.join([r for r, inc in [('CEO', args.include_ceo), ('COO', args.include_coo), ('CFO', args.include_cfo), ('Director', args.include_director)] if inc])}")
    print(f"- Minimum insiders: {args.min_insiders}")
    print(f"- Minimum value: ${args.min_value}k+")
    print("\nFinancial Metrics (yfinance - FREE):") 
    print("- Debt-to-Equity, Current Ratio, Quick Ratio, ROE")
    print("- Profit & Operating Margins")
    print("- PE, PEG, Price-to-Book Ratios")
    print("- Analyst Price Targets & Recommendations")
    print("- Market Cap, Beta, Sector, Industry")
    print("=" * 50)
    print()
    
    # Scrape pages
    all_data = []
    
    for page in range(1, args.num_pages + 1):
        data = scrape_openinsider(
            page=page,
            min_price=args.min_price,
            filing_days=args.filing_days,
            min_insiders=args.min_insiders,
            min_value=args.min_value,
            include_ceo=bool(args.include_ceo),
            include_coo=bool(args.include_coo),
            include_cfo=bool(args.include_cfo),
            include_director=bool(args.include_director)
        )
        all_data.extend(data)
        
        # Be respectful to the server
        if page < args.num_pages:
            time.sleep(2)
    
    # Enrich with financial data
    if all_data:
        enriched_data = enrich_with_financial_data(all_data)
        save_to_csv(enriched_data)
    else:
        print("No data was scraped. Please check the filters or website availability.")


if __name__ == "__main__":
    main()
