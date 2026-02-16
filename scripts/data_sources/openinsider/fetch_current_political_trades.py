#!/usr/bin/env python3
"""
Fetch CURRENT Political Trades (2025-2026)
Uses official government sources for Senate and House
NO STALE DATA - Only fresh trades from last 365 days
"""

import requests
import json
import csv
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import time

class CurrentPoliticalTradesFetcher:
    def __init__(self):
        self.output_dir = os.path.join(os.path.dirname(__file__), '..', 'output CSVs')
        self.output_file = os.path.join(self.output_dir, 'political_trades_enriched.csv')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.legislators = {}
        self.senate_trades = []
        self.house_trades = []
        
    def load_legislators(self):
        """Load congress members data for enrichment"""
        print("📥 Loading current legislators database...")
        url = "https://raw.githubusercontent.com/unitedstates/congress-legislators/gh-pages/legislators-current.json"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            legislators_data = response.json()
            
            for leg in legislators_data:
                name = leg.get('name', {})
                bio = leg.get('bio', {})
                terms = leg.get('terms', [])
                
                if not terms:
                    continue
                    
                last_term = terms[-1]
                
                # Build name variations
                full_name = f"{name.get('first', '')} {name.get('last', '')}".strip()
                official_full = name.get('official_full', '')
                
                legislator_info = {
                    'party': bio.get('gender'),  # We'll fix party below
                    'state': last_term.get('state', ''),
                    'chamber': last_term.get('type', ''),  # 'sen' or 'rep'
                    'district': last_term.get('district', ''),
                }
                
                # Determine party from last term
                party_code = last_term.get('party', '')
                if party_code == 'Democrat':
                    legislator_info['party'] = 'Democrat'
                elif party_code == 'Republican':
                    legislator_info['party'] = 'Republican'
                elif party_code == 'Independent':
                    legislator_info['party'] = 'Independent'
                else:
                    legislator_info['party'] = party_code
                
                # Store under multiple name formats
                self.legislators[full_name.lower()] = legislator_info
                if official_full:
                    self.legislators[official_full.lower()] = legislator_info
                
            print(f"   ✅ Loaded {len(legislators_data)} current legislators")
            return True
            
        except Exception as e:
            print(f"   ⚠️ Failed to load legislators: {e}")
            return False
    
    def fetch_senate_trades_api(self):
        """
        Fetch current Senate trades from official eFiling API
        This is the REAL source - updated in real-time
        """
        print("\n🏛️ Fetching CURRENT Senate trades from official eFiling system...")
        
        # The Senate has a search API endpoint
        # We'll search for PTR (Periodic Transaction Reports) from last year
        api_url = "https://efdsearch.senate.gov/search/report/data/"
        
        params = {
            'report_types': '[11]',  # PTR = 11
            'filed_after': (datetime.now() - timedelta(days=365)).strftime('%m/%d/%Y'),
            'submitted_start_date': (datetime.now() - timedelta(days=365)).strftime('%m/%d/%Y'),
            'submitted_end_date': datetime.now().strftime('%m/%d/%Y'),
        }
        
        try:
            print(f"   📡 Searching filings from {params['filed_after']} to today...")
            response = requests.post(api_url, headers=self.headers, json=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Found {len(data)} Senate filings to parse")
                # Now we need to parse each filing to extract trades
                # This will require additional requests to get transaction details
                return self.parse_senate_filings(data)
            else:
                print(f"   ❌ API returned status {response.status_code}")
                return []
                
        except Exception as e:
            print(f"   ❌ Error fetching Senate trades: {e}")
            return []
    
    def parse_senate_filings(self, filings):
        """Parse Senate PTR filings to extract individual trades"""
        trades = []
        print(f"   🔍 Parsing {len(filings)} Senate filings...")
        
        for i, filing in enumerate(filings[:50]):  # Limit to 50 filings for now
            try:
                # Each filing has a URL to the actual report
                filing_id = filing.get('filing_uuid', '')
                senator = filing.get('filer', '')
                
                if not filing_id:
                    continue
                
                # Fetch the actual filing details
                detail_url = f"https://efdsearch.senate.gov/search/view/ptr/{filing_id}/"
                
                print(f"   📄 [{i+1}/{min(50, len(filings))}] Parsing {senator}...")
                
                time.sleep(0.5)  # Be respectful
                
                # This would require scraping the HTML page
                # For now, return empty - we'll build this incrementally
                
            except Exception as e:
                print(f"   ⚠️ Error parsing filing: {e}")
                continue
        
        return trades
    
    def fetch_house_trades_clerk(self):
        """
        Fetch current House trades from official Clerk XML
        Download 2025 and 2026 PTR filings
        """
        print("\n🏛️ Fetching CURRENT House trades from Clerk's office...")
        
        years = [2025, 2026]
        all_trades = []
        
        for year in years:
            try:
                print(f"   📡 Downloading {year} PTR filings...")
                url = f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/"
                
                response = requests.get(url, headers=self.headers, timeout=30)
                
                if response.status_code == 200:
                    # Parse the directory listing
                    soup = BeautifulSoup(response.text, 'html.parser')
                    pdf_links = soup.find_all('a', href=True)
                    
                    print(f"   ✅ Found {len(pdf_links)} filings for {year}")
                    # Would need to download and parse PDFs - complex
                    
                else:
                    print(f"   ⚠️ No data for {year}")
                    
            except Exception as e:
                print(f"   ❌ Error fetching {year} House data: {e}")
        
        return all_trades
    
    def try_quiver_alternative(self):
        """
        Alternative: Check if there's a current mirror similar to Quiver
        """
        print("\n🔍 Checking for current data mirrors...")
        
        # Capitol Trades style endpoints
        endpoints = [
            "https://api.capitoltrades.com/trades",  # Might need auth
            "https://www.quiverquant.com/congresstrading/",  # Website
        ]
        
        for endpoint in endpoints:
            try:
                print(f"   📡 Trying: {endpoint}")
                response = requests.get(endpoint, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    print(f"   ✅ Found potential data source!")
                    print(f"   Response length: {len(response.text)} chars")
                    return response.text[:500]  # Preview
                    
            except Exception as e:
                print(f"   ❌ {e}")
        
        return None
    
    def run(self):
        """Main execution"""
        print("=" * 70)
        print("🚀 CURRENT Political Trades Fetcher")
        print("=" * 70)
        print(f"Target: Trades from {(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')} to today")
        print("")
        
        # Load enrichment data
        self.load_legislators()
        
        # Try Senate official API
        self.senate_trades = self.fetch_senate_trades_api()
        
        # Try House official Clerk
        self.house_trades = self.fetch_house_trades_clerk()
        
        # Try alternative sources
        alternative = self.try_quiver_alternative()
        
        print("\n" + "=" * 70)
        print(f"📊 Results:")
        print(f"   Senate trades: {len(self.senate_trades)}")
        print(f"   House trades: {len(self.house_trades)}")
        print(f"   Alternative preview: {'Yes' if alternative else 'No'}")
        print("=" * 70)

if __name__ == "__main__":
    fetcher = CurrentPoliticalTradesFetcher()
    fetcher.run()
