#!/usr/bin/env python3
"""
Political Trades Fetcher - GitHub Mirror Edition
Free data from Timothy Carambat's Senate Stock Watcher mirror
Cost: $0.00 forever!
"""

import requests
import csv
import os
from datetime import datetime

class PoliticalTradesFetcher:
    def __init__(self):
        # GitHub data mirror - free and publicly accessible
        self.senate_url = "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master/aggregate/all_transactions.json"
        
    def normalize_amount(self, amount_range):
        """Convert amount range string to midpoint value"""
        if not amount_range or amount_range == "Unknown":
            return 0
            
        # Remove $ and commas
        clean_range = amount_range.replace('$', '').replace(',', '')
        
        # Parse range like "1001 - 15000" or "1,001 - 15,000"
        if ' - ' in clean_range:
            parts = clean_range.split(' - ')
            try:
                low = float(parts[0].strip())
                high = float(parts[1].strip())
                return (low + high) / 2
            except ValueError:
                return 0
        
        # Try to parse as single number
        try:
            return float(clean_range)
        except ValueError:
            return 0
    
    def fetch_senate_data(self):
        """Fetch Senate trades from GitHub mirror"""
        print(f"🔄 Fetching Senate data from GitHub mirror...")
        
        try:
            response = requests.get(self.senate_url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Fetched {len(data)} Senate trade records")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching Senate data: {e}")
            return []
    
    def parse_trade_type(self, type_str):
        """Parse trade type from various formats"""
        if not type_str:
            return 'Unknown'
        
        type_str = type_str.lower()
        if 'purchase' in type_str or 'buy' in type_str:
            return 'Purchase'
        elif 'sale' in type_str or 'sell' in type_str:
            return 'Sale'
        else:
            return 'Other'
    
    def convert_date_format(self, date_str):
        """Convert MM/DD/YYYY to YYYY-MM-DD"""
        if not date_str:
            return ''
        
        try:
            # Parse MM/DD/YYYY
            dt = datetime.strptime(date_str, '%m/%d/%Y')
            # Return YYYY-MM-DD
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            return date_str  # Return as-is if parsing fails
    
    def standardize_trade(self, trade, source):
        """Standardize trade format to match our CSV structure"""
        return {
            'source': source,
            'politician': trade.get('senator', trade.get('representative', '')),
            'ticker': trade.get('ticker', ''),
            'asset_description': trade.get('asset_description', ''),
            'trade_type': self.parse_trade_type(trade.get('type', '')),
            'trade_date': self.convert_date_format(trade.get('transaction_date', '')),
            'disclosure_date': self.convert_date_format(trade.get('disclosure_date', '')),
            'amount_range': trade.get('amount', ''),
            'amount_value': self.normalize_amount(trade.get('amount', '')),
            'party': trade.get('party', ''),
            'state': trade.get('state', ''),
            'district': '',  # Senate doesn't have districts
            'committee': trade.get('committee', ''),
            'ptr_link': trade.get('ptr_link', '')
        }
    
    def fetch_and_save(self):
        """Main method to fetch all data and save to CSV"""
        all_trades = []
        
        # Fetch Senate data
        senate_trades = self.fetch_senate_data()
        valid_count = 0
        
        for trade in senate_trades:
            # Only include trades with valid ticker (not N/A, PDF disclosures, etc.)
            ticker = trade.get('ticker', '')
            if ticker and ticker != 'N/A' and ticker != '--' and not ticker.startswith('This filing'):
                standardized = self.standardize_trade(trade, 'Senate')
                all_trades.append(standardized)
                valid_count += 1
        
        print(f"📊 Filtered to {valid_count} valid trades (removed PDF disclosures and N/A tickers)")
        
        if not all_trades:
            print("❌ No valid trades found. Check data source.")
            return
        
        # Save to CSV
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output CSVs')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'political_trades_latest.csv')
        
        fieldnames = ['source', 'politician', 'ticker', 'asset_description', 'trade_type', 
                     'trade_date', 'disclosure_date', 'amount_range', 'amount_value',
                     'party', 'state', 'district', 'committee', 'ptr_link']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_trades)
        
        print(f"\n✅ SUCCESS! Saved {len(all_trades)} political trades")
        print(f"   📁 Location: {output_file}")
        print(f"   💰 Cost: $0.00 (GitHub mirrors are free!)")
        print(f"   🔄 Data source: Timothy Carambat's Senate Stock Watcher")
        print(f"\n📝 NOTE: This data is historical (2012-2014).")
        print(f"   For current 2026 data, you'll need to use a paid API or build a live scraper.")

if __name__ == "__main__":
    print("=" * 70)
    print("🏛️  Political Trades Fetcher - FREE GitHub Mirror Edition")
    print("=" * 70)
    
    fetcher = PoliticalTradesFetcher()
    fetcher.fetch_and_save()
    
    print("\n" + "=" * 70)
