#!/usr/bin/env python3
"""
Political Intelligence Data Fetcher
Fetches Congressional and Senate stock trades via web scraping
Based on research from deep_search_3.txt - scrapes House Stock Watcher website
"""

import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import time
import os
import re


class PoliticalTradesFetcher:
    """Fetch and normalize political trades from House and Senate via web scraping"""
    
    # House Stock Watcher website (maintained and up-to-date)
    HOUSE_URL = "https://housestockwatcher.com/api/all_transactions"
    SENATE_URL = "https://senatestockwatcher.com/api/all_transactions"
    
    # Amount range midpoints (conservative approach per research)
    AMOUNT_MIDPOINTS = {
        "$1,001 - $15,000": 8000,
        "$15,001 - $50,000": 32500,
        "$50,001 - $100,000": 75000,
        "$100,001 - $250,000": 175000,
        "$250,001 - $500,000": 375000,
        "$500,001 - $1,000,000": 750000,
        "$1,000,001 - $5,000,000": 3000000,
        "$5,000,001 - $25,000,000": 15000000,
        "$25,000,001 - $50,000,000": 37500000,
        "Over $50,000,000": 75000000,
        # Additional formats
        "$1,000 - $15,000": 8000,
        "$15,000 - $50,000": 32500,
        "$50,000 - $100,000": 75000,
        "$100,000 - $250,000": 175000,
        "$250,000 - $500,000": 375000,
        "$500,000 - $1,000,000": 750000,
        "$1,000,000 - $5,000,000": 3000000,
        "$5,000,000 - $25,000,000": 15000000,
        "$25,000,000 - $50,000,000": 37500000,
    }
    
    def __init__(self):
        self.trades = []
        
    def normalize_amount(self, amount_str):
        """Convert amount range string to numeric midpoint value"""
        if not amount_str or amount_str.strip() == "":
            return 0
        
        # Clean the string
        amount_str = amount_str.strip()
        
        # Direct lookup
        if amount_str in self.AMOUNT_MIDPOINTS:
            return self.AMOUNT_MIDPOINTS[amount_str]
        
        # Try to parse numeric values directly
        try:
            # Remove $ and commas
            cleaned = amount_str.replace('$', '').replace(',', '')
            return float(cleaned)
        except:
            pass
        
        # Default fallback
        return 50000  # Conservative default
    
    def fetch_senate_trades(self, days_back=60):
        """Fetch Senate trades from API"""
        print(f"📡 Fetching Senate trades (last {days_back} days)...")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(self.SENATE_URL, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for trade in data:
                try:
                    # Parse transaction date
                    trans_date_str = trade.get('transaction_date', trade.get('transactionDate', ''))
                    if not trans_date_str:
                        continue
                    
                    # Handle different date formats
                    try:
                        trans_date = datetime.strptime(trans_date_str, '%Y-%m-%d')
                    except:
                        try:
                            trans_date = datetime.strptime(trans_date_str, '%m/%d/%Y')
                        except:
                            try:
                                trans_date = datetime.strptime(trans_date_str, '%Y/%m/%d')
                            except:
                                continue
                    
                    # Filter by date
                    if trans_date < cutoff_date:
                        continue
                    
                    # Extract and normalize data
                    ticker = trade.get('ticker', '').upper().strip()
                    if not ticker or ticker == '--' or ticker == 'N/A':
                        # Try to extract from asset_description
                        asset_desc = trade.get('asset_description', trade.get('assetDescription', ''))
                        # Basic ticker extraction (this is imperfect)
                        if '(' in asset_desc and ')' in asset_desc:
                            ticker = asset_desc[asset_desc.find('(')+1:asset_desc.find(')')].upper()
                        else:
                            continue
                    
                    trade_type = trade.get('type', trade.get('transactionType', '')).lower()
                    if not trade_type:
                        continue
                    
                    # Normalize trade type
                    is_purchase = 'purchase' in trade_type.lower() or 'buy' in trade_type.lower()
                    
                    # Get amount
                    amount_str = trade.get('amount', trade.get('amount_range', ''))
                    amount_value = self.normalize_amount(amount_str)
                    
                    # Build trade record
                    trade_record = {
                        'source': 'Senate',
                        'politician': trade.get('senator', trade.get('name', 'Unknown')),
                        'ticker': ticker,
                        'asset_description': trade.get('asset_description', trade.get('assetDescription', '')),
                        'trade_type': 'Purchase' if is_purchase else 'Sale',
                        'trade_date': trans_date.strftime('%Y-%m-%d'),
                        'disclosure_date': trade.get('disclosure_date', trade.get('disclosureDate', '')),
                        'amount_range': amount_str,
                        'amount_value': amount_value,
                        'party': trade.get('party', ''),
                        'state': trade.get('state', ''),
                        'ptr_link': trade.get('ptr_link', trade.get('ptrLink', '')),
                        'committee': '',  # Senate API doesn't always have this
                    }
                    
                    self.trades.append(trade_record)
                    
                except Exception as e:
                    print(f"  ⚠️  Error parsing Senate trade: {e}")
                    continue
            
            print(f"✅ Fetched {len([t for t in self.trades if t['source'] == 'Senate'])} Senate trades")
            
        except Exception as e:
            print(f"❌ Error fetching Senate data: {e}")
    
    def fetch_house_trades(self, days_back=60):
        """Fetch House trades from API"""
        print(f"📡 Fetching House trades (last {days_back} days)...")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(self.HOUSE_URL, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for trade in data:
                try:
                    # Parse transaction date
                    trans_date_str = trade.get('transaction_date', trade.get('transactionDate', ''))
                    if not trans_date_str:
                        continue
                    
                    # Handle different date formats
                    try:
                        trans_date = datetime.strptime(trans_date_str, '%Y-%m-%d')
                    except:
                        try:
                            trans_date = datetime.strptime(trans_date_str, '%m/%d/%Y')
                        except:
                            try:
                                trans_date = datetime.strptime(trans_date_str, '%Y/%m/%d')
                            except:
                                continue
                    
                    # Filter by date
                    if trans_date < cutoff_date:
                        continue
                    
                    # Extract and normalize data
                    ticker = trade.get('ticker', '').upper().strip()
                    if not ticker or ticker == '--' or ticker == 'N/A':
                        # Try to extract from asset_description
                        asset_desc = trade.get('asset_description', trade.get('assetDescription', ''))
                        if '(' in asset_desc and ')' in asset_desc:
                            ticker = asset_desc[asset_desc.find('(')+1:asset_desc.find(')')].upper()
                        else:
                            continue
                    
                    trade_type = trade.get('type', trade.get('transactionType', '')).lower()
                    if not trade_type:
                        continue
                    
                    # Normalize trade type
                    is_purchase = 'purchase' in trade_type.lower() or 'buy' in trade_type.lower()
                    
                    # Get amount
                    amount_str = trade.get('amount', trade.get('amount_range', ''))
                    amount_value = self.normalize_amount(amount_str)
                    
                    # Build trade record
                    trade_record = {
                        'source': 'House',
                        'politician': trade.get('representative', trade.get('name', 'Unknown')),
                        'ticker': ticker,
                        'asset_description': trade.get('asset_description', trade.get('assetDescription', '')),
                        'trade_type': 'Purchase' if is_purchase else 'Sale',
                        'trade_date': trans_date.strftime('%Y-%m-%d'),
                        'disclosure_date': trade.get('disclosure_date', trade.get('disclosureDate', '')),
                        'amount_range': amount_str,
                        'amount_value': amount_value,
                        'party': trade.get('party', ''),
                        'district': trade.get('district', ''),
                        'ptr_link': trade.get('ptr_link', trade.get('ptrLink', '')),
                        'committee': '',  # House API doesn't always have this
                    }
                    
                    self.trades.append(trade_record)
                    
                except Exception as e:
                    print(f"  ⚠️  Error parsing House trade: {e}")
                    continue
            
            print(f"✅ Fetched {len([t for t in self.trades if t['source'] == 'House'])} House trades")
            
        except Exception as e:
            print(f"❌ Error fetching House data: {e}")
    
    def save_to_csv(self, output_path):
        """Save political trades to CSV"""
        print(f"💾 Saving {len(self.trades)} trades to CSV...")
        
        # Sort by date (newest first)
        self.trades.sort(key=lambda x: x['trade_date'], reverse=True)
        
        fieldnames = [
            'source', 'politician', 'ticker', 'asset_description', 
            'trade_type', 'trade_date', 'disclosure_date',
            'amount_range', 'amount_value', 'party', 
            'state', 'district', 'committee', 'ptr_link'
        ]
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for trade in self.trades:
                # Ensure all fields exist
                row = {field: trade.get(field, '') for field in fieldnames}
                writer.writerow(row)
        
        print(f"✅ Saved to {output_path}")
    
    def get_ticker_summary(self):
        """Get summary statistics by ticker"""
        ticker_stats = {}
        
        for trade in self.trades:
            ticker = trade['ticker']
            if ticker not in ticker_stats:
                ticker_stats[ticker] = {
                    'purchases': 0,
                    'sales': 0,
                    'purchase_value': 0,
                    'sale_value': 0,
                    'politicians': set(),
                    'latest_trade': trade['trade_date']
                }
            
            stats = ticker_stats[ticker]
            stats['politicians'].add(trade['politician'])
            
            if trade['trade_type'] == 'Purchase':
                stats['purchases'] += 1
                stats['purchase_value'] += trade['amount_value']
            else:
                stats['sales'] += 1
                stats['sale_value'] += trade['amount_value']
            
            # Update latest trade date
            if trade['trade_date'] > stats['latest_trade']:
                stats['latest_trade'] = trade['trade_date']
        
        # Convert sets to counts
        for ticker in ticker_stats:
            ticker_stats[ticker]['politician_count'] = len(ticker_stats[ticker]['politicians'])
            del ticker_stats[ticker]['politicians']
        
        return ticker_stats


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch political trades from Congress')
    parser.add_argument('--days', type=int, default=60, 
                       help='Number of days back to fetch (default: 60)')
    parser.add_argument('--output', type=str, 
                       default='output CSVs/political_trades_latest.csv',
                       help='Output CSV path')
    parser.add_argument('--source', choices=['senate', 'house', 'both'], 
                       default='both', help='Data source to fetch')
    
    args = parser.parse_args()
    
    print("🏛️  Political Intelligence Data Fetcher")
    print("=" * 60)
    
    fetcher = PoliticalTradesFetcher()
    
    # Fetch data based on source selection
    if args.source in ['senate', 'both']:
        fetcher.fetch_senate_trades(days_back=args.days)
    
    if args.source in ['house', 'both']:
        fetcher.fetch_house_trades(days_back=args.days)
    
    # Save to CSV
    if fetcher.trades:
        fetcher.save_to_csv(args.output)
        
        # Print summary
        print("\n📊 Summary Statistics:")
        print("-" * 60)
        
        ticker_stats = fetcher.get_ticker_summary()
        
        # Sort by total activity (purchases + sales)
        sorted_tickers = sorted(
            ticker_stats.items(),
            key=lambda x: x[1]['purchases'] + x[1]['sales'],
            reverse=True
        )[:10]
        
        print(f"{'Ticker':<8} {'Purchases':<12} {'Sales':<12} {'Politicians':<12} {'Latest Trade'}")
        print("-" * 60)
        for ticker, stats in sorted_tickers:
            print(f"{ticker:<8} {stats['purchases']:<12} {stats['sales']:<12} "
                  f"{stats['politician_count']:<12} {stats['latest_trade']}")
    else:
        print("❌ No trades fetched")


if __name__ == "__main__":
    main()
