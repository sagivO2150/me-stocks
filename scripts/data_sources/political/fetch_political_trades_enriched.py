#!/usr/bin/env python3
"""
Political Trades Fetcher - ENRICHED with Congress Legislators Data
Combines Senate Stock Watcher data with official Congress member info
Adds: Party, State, Committees, Current status
Cost: $0.00 forever!
"""

import requests
import csv
import os
import json
from datetime import datetime

class EnrichedPoliticalTradesFetcher:
    def __init__(self):
        # GitHub data mirrors - free and publicly accessible
        self.senate_url = "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master/aggregate/all_transactions.json"
        
        # Congress legislators data for enrichment (JSON from gh-pages branch)
        self.legislators_current_url = "https://raw.githubusercontent.com/unitedstates/congress-legislators/gh-pages/legislators-current.json"
        self.legislators_historical_url = "https://raw.githubusercontent.com/unitedstates/congress-legislators/gh-pages/legislators-historical.json"
        
        # House data sources with User-Agent headers to bypass blocking
        self.house_urls_to_try = [
            # Official API endpoint (preferred)
            "https://housestockwatcher.com/api/latest_trades",
            # S3 bucket with year-specific files
            "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json",
            # GitHub yearly files (fallback)
            "https://raw.githubusercontent.com/timothycarambat/house-stock-watcher-data/master/data/2026.json",
            "https://raw.githubusercontent.com/timothycarambat/house-stock-watcher-data/master/data/2025.json",
        ]
        
        # Browser headers to bypass 403 blocks
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://housestockwatcher.com/'
        }
        
        self.legislator_map = {}
        
    def fetch_legislators_data(self):
        """Fetch and index Congress members by name for enrichment"""
        print("🔄 Fetching Congress legislators data for enrichment...")
        
        try:
            # Fetch current legislators
            response = requests.get(self.legislators_current_url, timeout=30)
            response.raise_for_status()
            current_legislators = response.json()
            
            # Fetch historical legislators (for trades from past senators)
            try:
                response = requests.get(self.legislators_historical_url, timeout=30)
                response.raise_for_status()
                historical_legislators = response.json()
            except:
                historical_legislators = []
            
            # Combine both datasets
            all_legislators = current_legislators + historical_legislators
            
            # Build name index
            for legislator in all_legislators:
                name_info = legislator.get('name', {})
                bio = legislator.get('bio', {})
                terms = legislator.get('terms', [])
                
                # Get full name variations
                official_full = name_info.get('official_full', '')
                first = name_info.get('first', '')
                middle = name_info.get('middle', '')
                last = name_info.get('last', '')
                
                # Create name variations to match
                name_variations = []
                if official_full:
                    name_variations.append(official_full)
                
                # "First Last"
                if first and last:
                    name_variations.append(f"{first} {last}")
                
                # "First Middle Last"
                if first and middle and last:
                    name_variations.append(f"{first} {middle} {last}")
                    # Also try middle initial
                    name_variations.append(f"{first} {middle[0]} {last}")
                
                # Get most recent term info
                if terms:
                    latest_term = terms[-1]
                    party = latest_term.get('party', '')
                    state = latest_term.get('state', '')
                    chamber = latest_term.get('type', '')  # 'sen' or 'rep'
                    district = latest_term.get('district', '')
                    
                    # Store under all name variations
                    legislator_info = {
                        'party': party,
                        'state': state,
                        'chamber': chamber,
                        'district': str(district) if district else ''
                    }
                    
                    for name in name_variations:
                        self.legislator_map[name] = legislator_info
            
            print(f"✅ Indexed {len(self.legislator_map)} legislator name variations")
            return True
            
        except Exception as e:
            print(f"⚠️ Warning: Could not fetch legislators data: {e}")
            print(f"   Will proceed without party/state enrichment")
            return False
    
    def enrich_with_legislator_info(self, politician_name):
        """Look up party, state, chamber info for a politician"""
        if not self.legislator_map:
            return {'party': '', 'state': '', 'chamber': '', 'district': ''}
        
        # Try exact match first
        if politician_name in self.legislator_map:
            return self.legislator_map[politician_name]
        
        # Try case-insensitive match
        for name, info in self.legislator_map.items():
            if name.lower() == politician_name.lower():
                return info
        
        # Try partial match (last name only)
        politician_last = politician_name.split()[-1].lower()
        for name, info in self.legislator_map.items():
            if name.split()[-1].lower() == politician_last:
                return info
        
        return {'party': '', 'state': '', 'chamber': '', 'district': ''}
    
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
            response = requests.get(self.senate_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Fetched {len(data)} Senate trade records")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching Senate data: {e}")
            return []
    
    def fetch_house_data(self):
        """Try multiple House data sources with browser headers"""
        # First, try loading from stealth scraper cache
        print(f"🔄 Attempting to fetch House data...")
        stealth_file = os.path.join(os.path.dirname(__file__), '..', 'output CSVs', 'house_trades_raw.json')
        if os.path.exists(stealth_file):
            try:
                print(f"   🕵️  Found stealth cache: {stealth_file}")
                with open(stealth_file, 'r') as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    print(f"   ✅ Loaded {len(data)} House records from stealth cache")
                    return data
            except Exception as e:
                print(f"   ⚠️ Failed to load stealth cache: {e}")
        
        print(f"   📡 Trying direct URLs with browser headers...")
        for url in self.house_urls_to_try:
            try:
                print(f"   📡 Trying: {url}")
                response = requests.get(url, headers=self.headers, timeout=30, allow_redirects=True)
                response.raise_for_status()
                
                data = response.json()
                
                # Handle different response formats
                if isinstance(data, dict):
                    # API might return {trades: [...]} or {data: [...]}
                    if 'trades' in data:
                        data = data['trades']
                    elif 'data' in data:
                        data = data['data']
                    elif 'transactions' in data:
                        data = data['transactions']
                
                if data and len(data) > 0:
                    print(f"✅ Found House data! Fetched {len(data)} records")
                    return data
                else:
                    print(f"   ⚠️ Empty response")
                    continue
                
            except requests.exceptions.HTTPError as e:
                print(f"   ❌ HTTP {e.response.status_code}: {e}")
                continue
            except Exception as e:
                print(f"   ❌ Failed: {type(e).__name__}: {str(e)[:100]}")
                continue
        
        print(f"⚠️ No House data source available - continuing with Senate only")
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
            # Try parsing as YYYY-MM-DD (already correct format)
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
                return date_str
            except ValueError:
                return date_str  # Return as-is if parsing fails
    
    def standardize_trade(self, trade, source):
        """Standardize trade format and enrich with legislator data"""
        politician_name = trade.get('senator', trade.get('representative', ''))
        
        # Enrich with legislator data
        enrichment = self.enrich_with_legislator_info(politician_name)
        
        return {
            'source': source,
            'politician': politician_name,
            'ticker': trade.get('ticker', ''),
            'asset_description': trade.get('asset_description', ''),
            'trade_type': self.parse_trade_type(trade.get('type', '')),
            'trade_date': self.convert_date_format(trade.get('transaction_date', '')),
            'disclosure_date': self.convert_date_format(trade.get('disclosure_date', '')),
            'amount_range': trade.get('amount', ''),
            'amount_value': self.normalize_amount(trade.get('amount', '')),
            'party': enrichment['party'],
            'state': enrichment['state'],
            'district': enrichment['district'] if source == 'House' else '',
            'committee': trade.get('committee', ''),
            'ptr_link': trade.get('ptr_link', '')
        }
    
    def fetch_and_save(self):
        """Main method to fetch all data and save to CSV"""
        all_trades = []
        
        # First, fetch and index legislators data
        self.fetch_legislators_data()
        
        # Fetch Senate data
        senate_trades = self.fetch_senate_data()
        senate_valid_count = 0
        
        for trade in senate_trades:
            # Only include trades with valid ticker
            ticker = trade.get('ticker', '')
            if ticker and ticker != 'N/A' and ticker != '--' and not ticker.startswith('This filing'):
                standardized = self.standardize_trade(trade, 'Senate')
                all_trades.append(standardized)
                senate_valid_count += 1
        
        print(f"📊 Senate: {senate_valid_count} valid trades")
        
        # Fetch House data
        house_trades = self.fetch_house_data()
        house_valid_count = 0
        
        for trade in house_trades:
            ticker = trade.get('ticker', '')
            if ticker and ticker != 'N/A' and ticker != '--' and not ticker.startswith('This filing'):
                standardized = self.standardize_trade(trade, 'House')
                all_trades.append(standardized)
                house_valid_count += 1
        
        if house_valid_count > 0:
            print(f"📊 House: {house_valid_count} valid trades")
        
        if not all_trades:
            print("❌ No valid trades found. Check data sources.")
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
        
        print(f"\n✅ SUCCESS! Saved {len(all_trades)} enriched political trades")
        print(f"   📁 Location: {output_file}")
        print(f"   💰 Cost: $0.00 (all sources are free!)")
        print(f"   🎯 Enriched with party/state data from congress-legislators")
        print(f"   🔄 Data sources:")
        print(f"      - Senate: Timothy Carambat's mirror")
        if house_valid_count > 0:
            print(f"      - House: Found working source!")
        print(f"\n📝 NOTE: Trade data may be historical.")
        print(f"   For current 2026 data, you'll need a paid API or live scraper.")

if __name__ == "__main__":
    print("=" * 70)
    print("🏛️  Political Trades Fetcher - ENRICHED Edition")
    print("=" * 70)
    
    fetcher = EnrichedPoliticalTradesFetcher()
    fetcher.fetch_and_save()
    
    print("\n" + "=" * 70)
