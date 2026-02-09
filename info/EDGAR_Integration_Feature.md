# Extended Historical Insider Trading Data (EDGAR Integration)

## What's New

You can now extend insider trading data beyond OpenInsider's ~2 year limit by loading historical data directly from SEC EDGAR!

## How It Works

### Main View (OpenInsider - Fast)
- Shows ~2 years of insider trading data
- Fast loading for screening stocks
- Perfect for identifying recent insider activity during downturns

### Extended View (EDGAR - Deep History)
- Click the **"📈 Load Extended History (EDGAR)"** button on any stock detail page
- Fetches 5-10 years of historical insider trading data
- Shows only **real purchases (P) and sales (S)** - no gifts, awards, or tax transactions
- Same data format as OpenInsider for seamless chart integration

## Usage

1. **Screen stocks** using the main dashboard (OpenInsider data)
2. **Click a stock card** to view details
3. **Click "Load Extended History"** to see 10+ years of insider trades
4. **Switch back** to OpenInsider data anytime with the "Use OpenInsider Only" button

## Data Sources

| Feature | OpenInsider | EDGAR |
|---------|-------------|-------|
| Historical Range | ~2 years | 10+ years |
| Load Speed | Fast | Slower (20-30 sec) |
| Transaction Types | P (Purchase), S (Sale) | P (Purchase), S (Sale) |
| Data Quality | Pre-aggregated | Raw from SEC |
| Best For | Screening | Deep analysis before buying |

## Visual Indicators

- **Green badge** shows when EDGAR data is loaded
- **Trade counts** update to reflect EDGAR totals
- **(EDGAR)** label appears next to insider trade counts in the legend

## Technical Details

### Files Modified
- `webapp-stocks/server.js` - Added `/api/edgar-trades/:ticker` endpoint
- `webapp-stocks/src/components/StockDetail.jsx` - Added EDGAR toggle and data handling
- `scripts/fetch_edgar_trades.py` - EDGAR scraper (already created)

### API Endpoints
```javascript
// OpenInsider data (default)
GET /api/insider-trades/:ticker

// EDGAR historical data
GET /api/edgar-trades/:ticker?years=10
```

### Response Format (Identical)
```json
{
  "success": true,
  "ticker": "AAPL",
  "purchases": [...],
  "sales": [...],
  "total_purchases": 156,
  "total_sales": 45,
  "source": "EDGAR" // or "OpenInsider"
}
```

## Benefits

1. **Better Due Diligence**: See long-term insider behavior patterns
2. **Historical Context**: Understand how insiders have traded during past downturns
3. **More Data Points**: 5-10x more trades for trend analysis
4. **Same Interface**: Seamless integration with existing chart overlay

## Limitations

- **SEC Rate Limits**: 10 requests/second max
- **Load Time**: 20-30 seconds for 10 years of data
- **No Caching Yet**: Each load fetches fresh data (caching planned)

## Example Workflow

```
1. Screen dashboard → Find "ADC" with insider buying during downturn
2. Click card → See 2 years of trades (OpenInsider)
3. Click "Load Extended History" → See 10 years of trades (EDGAR)
4. Analyze long-term pattern → Make informed decision
```

## Next Steps (Optional Enhancements)

- [ ] Add caching to avoid repeated EDGAR requests
- [ ] Show date range indicator (e.g., "Showing: Jan 2015 - Feb 2026")
- [ ] Add loading progress indicator
- [ ] Allow custom year range (5yr, 10yr, max)
- [ ] Export EDGAR data to CSV
