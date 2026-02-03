#!/usr/bin/env python3
"""
House Stock Watcher - Stealth Scraper
Uses Playwright with stealth mode to bypass S3 restrictions
Intercepts network requests to capture JSON data
"""

import asyncio
import json
import os
import re
from playwright.async_api import async_playwright

class HouseStealth:
    def __init__(self):
        self.output_path = os.path.join(os.path.dirname(__file__), '..', 'output CSVs', 'house_trades_raw.json')
        self.house_data = []
        
    async def scrape_house_data_stealth(self):
        """Main stealth scraping function"""
        async with async_playwright() as p:
            # 1. Launch real Chromium browser
            print("🚀 Launching stealth browser (Chromium)...")
            browser = await p.chromium.launch(
                headless=True,  # Set to False to watch it work
                args=['--disable-blink-features=AutomationControlled']
            )
            
            # 2. Create realistic human context with stealth features built-in
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
                timezone_id='America/New_York',
                # Additional stealth settings
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                }
            )
            
            page = await context.new_page()
            
            # 3. Hide automation indicators
            print("🕵️  Applying stealth patches...")
            await page.add_init_script("""
                // Hide webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)
            
            print("🔍 Navigating to House Stock Watcher in stealth mode...")
            
            # 4. Intercept API responses
            async def handle_response(response):
                """Intercept JSON responses that look like trade data"""
                url = response.url.lower()
                
                # Look for API endpoints or JSON files
                if any(keyword in url for keyword in ['api', 'trades', 'transactions', '.json']):
                    try:
                        # Check if it's JSON
                        if 'json' in response.headers.get('content-type', ''):
                            data = await response.json()
                            
                            # Validate it looks like trade data
                            if isinstance(data, list) and len(data) > 0:
                                # Check if first item has trade-like fields
                                first_item = data[0]
                                if any(field in str(first_item).lower() for field in ['ticker', 'representative', 'trade', 'transaction']):
                                    self.house_data = data
                                    print(f"✅ Intercepted {len(self.house_data)} House records from: {response.url}")
                            elif isinstance(data, dict) and ('trades' in data or 'transactions' in data):
                                # Handle wrapped responses
                                self.house_data = data.get('trades', data.get('transactions', []))
                                print(f"✅ Intercepted {len(self.house_data)} House records (unwrapped)")
                    except Exception as e:
                        # Silently ignore non-JSON or malformed responses
                        pass
            
            page.on("response", handle_response)
            
            # 5. Visit the main site (triggers internal API calls)
            try:
                await page.goto("https://housestockwatcher.com/", wait_until="networkidle", timeout=30000)
                
                # Wait a bit for lazy-loaded content
                await page.wait_for_timeout(3000)
                
                # Try clicking "All Trades" if it exists (loads more data)
                try:
                    await page.click('text="All"', timeout=5000)
                    await page.wait_for_timeout(2000)
                except:
                    pass
                    
            except Exception as e:
                print(f"⚠️ Navigation warning: {e}")
            
            # 6. Fallback: Try direct data extraction from page
            if not self.house_data:
                print("⚠️ API interception failed, attempting DOM extraction...")
                try:
                    # Look for embedded JSON in script tags
                    scripts = await page.query_selector_all('script')
                    for script in scripts:
                        content = await script.inner_text()
                        if 'transaction' in content.lower() or 'trade' in content.lower():
                            # Try to parse JSON from script
                            try:
                                # Look for JSON array patterns
                                import re
                                json_match = re.search(r'\[{.*}\]', content, re.DOTALL)
                                if json_match:
                                    potential_data = json.loads(json_match.group())
                                    if len(potential_data) > 10:  # Reasonable amount
                                        self.house_data = potential_data
                                        print(f"✅ Extracted {len(self.house_data)} records from embedded JSON")
                                        break
                            except:
                                continue
                except Exception as e:
                    print(f"⚠️ DOM extraction failed: {e}")
            
            await browser.close()
            
            return self.house_data
    
    def save_data(self):
        """Save intercepted data to JSON file"""
        if self.house_data:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(self.house_data, f, indent=2)
            print(f"💾 House data saved: {self.output_path}")
            print(f"   Records: {len(self.house_data)}")
            return True
        else:
            print("❌ No House data intercepted")
            return False
    
    async def run(self):
        """Main execution flow"""
        data = await self.scrape_house_data_stealth()
        return self.save_data()

async def main():
    print("=" * 70)
    print("🏛️  House Stock Watcher - Stealth Mode")
    print("=" * 70)
    
    scraper = HouseStealth()
    success = await scraper.run()
    
    if success:
        print("\n✅ SUCCESS! House data intercepted and saved")
        print("   This data can now be processed by your enrichment pipeline")
    else:
        print("\n⚠️ No House data available")
        print("   Possible reasons:")
        print("   - Website structure changed")
        print("   - Network timeout")
        print("   - Need to install: pip install playwright playwright-stealth")
        print("   - Run: playwright install chromium")
    
    print("=" * 70)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have installed:")
        print("   pip install playwright playwright-stealth")
        print("   playwright install chromium")
