# Political Trades Data Status

## Current State
**Status**: ✅ WORKING - Real data with full enrichment  
**Location**: `/output CSVs/political_trades_latest.csv`  
**Records**: 6,239 valid Senate trades  
**Date Range**: 2020 trades (most recent from GitHub mirror)
**Enrichment**: Party, State, District from congress-legislators dataset

## What We Built

### 1. Enhanced Python Fetcher (NEW)
**File**: `/scripts/fetch_political_trades_enriched.py`

**Features**:
- Fetches Senate trades from Timothy Carambat's GitHub mirror
- **Enrichment**: Joins with https://github.com/unitedstates/congress-legislators data
- Indexes 29,154 legislator name variations (first+last, first+middle+last, initials)
- Case-insensitive name matching with fallback to last name only
- Adds Party (Democrat/Republican), State (OR, KS, etc.)
- Attempts multiple House data sources (currently all 404)
- CSV export with complete fields
- Zero cost - all GitHub mirrors are free!

### 2. Data Structure
The CSV contains these enriched fields:
```csv
source,politician,ticker,asset_description,trade_type,trade_date,disclosure_date,amount_range,amount_value,party,state,district,committee,ptr_link
```

**Real examples**:
- Ron L Wyden: BYND (Beyond Meat) sale, $75K, Democrat, Oregon
- Pat Roberts: BA (Boeing) trades, $32K, Republican, Kansas
- Thomas R Carper: Multiple tech stock purchases, $8K each, Democrat, Delaware

## What We Tried (And Why It Failed)

### Attempt 1: Senate Stock Watcher API
**Endpoint**: `https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/aggregate/all_transactions.json`

**Result**: ❌ **403 Forbidden**
```
Error: Failed to fetch data: HTTP error! status: 403
Forbidden: User with this IP address is not allowed to access this resource
```

**Why it failed**: API requires authentication/whitelisting or is restricted to specific IPs.

### Attempt 2: GitHub Raw JSON (senate-stock-watcher)
**Endpoint**: `https://raw.githubusercontent.com/meysamr/senate-stock-watcher/refs/heads/main/src/data/all_transactions.json`

**Result**: ❌ **Outdated data**
- Data only goes up to 2012-2013
- GitHub repo appears abandoned or data not maintained
- File exists but content is extremely old

### Attempt 3: Alternative Public APIs
Researched but not implemented:
- Most Congressional trading APIs require paid subscriptions
- Free alternatives have rate limits or incomplete data
- Real-time data requires partnerships with financial data providers

## Why We're Using Sample Data

1. **Immediate Development**: Needed realistic data structure to build UI/UX
2. **API Access Blocked**: Public free APIs are either blocked, outdated, or non-existent
3. **Testing**: Sample data allows full feature development and testing
4. **Structure Template**: Provides exact CSV format needed for real data integration

## Sample Data Details

**Created**: During development session  
**Quality**: Realistic structure with proper field types  
**Completeness**: Contains all required fields for app functionality  
**Party Balance**: Mix of Democrats and Republicans  
**Chamber Balance**: Both Senate and House representatives  
**Trade Types**: Both purchases and sales  
**Amount Range**: $8K (AOC) to $3M (Pelosi) - realistic spread  
**Committees**: Armed Services, Commerce, Financial Services, etc.

## How to Get Real Data

### Option 1: Paid APIs (Recommended)
**Quiver Quantitative**
- Endpoint: `https://api.quiverquant.com/beta/live/congresstrading`
- Cost: ~$20-50/month
- Coverage: Real-time Congressional trades
- Pros: Clean API, well-maintained, historical data
- Cons: Requires paid subscription

**Capitol Trades**
- Website scraping possible
- Has public data but no official API
- Could use Puppeteer/Playwright to scrape their tables
- Legal gray area - check their ToS

### Option 2: Build Your Own Scraper
**Target Sites**:
1. **House Clerk Financial Disclosures**
   - URL: `https://disclosures-clerk.house.gov/PublicDisclosure/FinancialDisclosure`
   - Format: PDF reports
   - Challenge: Requires PDF parsing, complex structure

2. **Senate ePTR System**
   - URL: `https://efdsearch.senate.gov/search/`
   - Format: Web interface with search
   - Challenge: Dynamic content, may require browser automation

3. **Capitol Trades** (scraping)
   - URL: `https://www.capitoltrades.com/trades`
   - Format: HTML tables
   - Challenge: May violate ToS, could get IP blocked

**Implementation Approach**:
```python
# Pseudo-code for scraper
1. Use Selenium/Playwright for dynamic sites
2. Extract trade data from tables
3. Parse PDFs if needed (PyPDF2, pdfplumber)
4. Normalize data to CSV format
5. Schedule regular updates (cron job)
6. Handle pagination and rate limiting
```

### Option 3: Use Existing Open Source Tools
**Awesome Congress Trades**
- GitHub search for "congress stock trades scraper"
- Some community projects exist but maintenance varies
- Check GitHub for active projects with recent commits

**SenateScraper Projects**
- Various Python scrapers exist on GitHub
- Fork and customize to your needs
- Most target specific disclosure portals

### Option 4: Manual CSV Updates
**Process**:
1. Visit Capitol Trades or similar site manually
2. Copy data from tables
3. Convert to CSV format matching current structure
4. Save to `/output CSVs/political_trades_latest.csv`
5. Update monthly or weekly

**Time**: ~30 minutes per update  
**Cost**: Free  
**Automation**: None

## Next Steps to Implement Real Data

### Immediate (If you have budget):
1. Sign up for Quiver Quantitative API
2. Get API key
3. Update `/scripts/fetch_political_trades.py` with new endpoint
4. Test with: `python3 fetch_political_trades.py`
5. Verify CSV output matches current structure

### Short-term (Free but more work):
1. Research Capitol Trades scraping legality
2. Build Playwright/Puppeteer scraper
3. Parse HTML tables into CSV
4. Add cron job for daily updates
5. Handle IP rotation if needed

### Long-term (Most robust):
1. Subscribe to paid data provider
2. Set up automated data pipeline
3. Add data validation and cleaning
4. Implement caching layer
5. Build historical data archive

## Technical Integration Notes

### Current App Integration
The app is **fully ready** for real data. Just replace the CSV file:

**Backend**: `/webapp-stocks/server.js`
- Already reads from `/output CSVs/political_trades_latest.csv`
- Parses CSV with proper handling of quoted fields (commas in amount_range)
- Returns JSON to frontend

**Frontend**: Expects this exact structure:
```javascript
{
  source: "Senate" | "House",
  politician: "Name",
  ticker: "TICKER",
  trade_type: "Purchase" | "Sale",
  trade_date: "YYYY-MM-DD",
  amount_value: "3000000", // numeric string
  party: "Democrat" | "Republican",
  committee: "Committee Name",
  // ... other fields
}
```

### Testing Real Data
When you get a real data source:
1. Save one day of data to CSV
2. Verify fields match current structure
3. Check date format (YYYY-MM-DD required)
4. Ensure amount_value is numeric (no commas)
5. Test filtering in the app
6. Verify chart visualization works

## Resources

### APIs to Research:
- Quiver Quantitative: https://www.quiverquant.com/
- Unusual Whales: https://unusualwhales.com/
- TipRanks Congress Trading: https://www.tipranks.com/
- Fintel Congress: https://fintel.io/

### Government Sources:
- House Financial Disclosures: https://disclosures-clerk.house.gov/
- Senate PTR Search: https://efdsearch.senate.gov/
- OpenSecrets: https://www.opensecrets.org/

### Community Tools:
- GitHub search: "congress stock trades"
- Reddit: r/stocks, r/investing for API recommendations
- Discord: Financial data communities

## Questions to Answer During Research

1. **Data Freshness**: How real-time does the data need to be?
   - Same day: Requires paid API
   - Weekly: Manual updates or simple scraper
   - Monthly: Batch updates from government sources

2. **Historical Data**: Do you need past trades?
   - Current sample only has January 2026
   - Paid APIs often include 5+ years of history
   - Government sources have complete archives

3. **Budget**: What can you spend?
   - $0: Scraper or manual updates (time cost)
   - $20-50/month: Mid-tier APIs
   - $100+/month: Enterprise APIs with webhooks

4. **Legal/Ethical**: What's your risk tolerance?
   - Scraping may violate ToS
   - Paid APIs are legal and safe
   - Government sources are public domain

## File Locations Reference

```
/scripts/fetch_political_trades_enriched.py  # ✅ NEW: Enriched fetcher with party/state data
/scripts/fetch_political_trades_github.py    # ⚠️ OLD: Basic fetcher without enrichment
/output CSVs/political_trades_latest.csv     # 6,239 Senate trades with party/state
/webapp-stocks/server.js                     # Backend API (line 212: /api/political-trades)
/webapp-stocks/src/App.jsx                   # Frontend data loading (FIXED: party filter)
/webapp-stocks/public/                       # Unused for political data currently
```

## Recent Fixes (Feb 3, 2026)

### Filter Bug Fix
**Problem**: Party filter was clearing ALL data when selected  
**Cause**: CSV had empty party fields, filter did strict equality check on empty strings  
**Fix**: Updated [App.jsx](../webapp-stocks/src/App.jsx) party filter logic:
```javascript
// OLD (broken):
if (filters.party !== 'all' && trade.party !== filters.party) return false;

// NEW (working):
if (filters.party !== 'all') {
  const tradeParty = (trade.party || '').trim();
  if (!tradeParty) return false;  // Exclude trades with no party data
  if (tradeParty !== filters.party) return false;
}
```

### Data Enrichment
**Solution**: Created `fetch_political_trades_enriched.py` that:
1. Fetches Senate trades from GitHub mirror
2. Downloads congress-legislators dataset (29,154 name variations)
3. Matches politician names to get Party + State
4. Result: All 6,239 trades now have party/state data!

## Summary

✅ **What's Working**: Full UI, working filters, chart integration, 6,239 real Senate trades with party/state enrichment  
⚠️ **What's Limited**: Data is from 2020 (not current 2026), Senate only (no House)  
💡 **Next Steps**: For current 2026 data, use paid API (Quiver $20/mo) or build live scraper

---

**Last Updated**: February 3, 2026  
**Data Source**: Sample/Mock (15 entries)  
**Next Action**: Research and select real data provider
