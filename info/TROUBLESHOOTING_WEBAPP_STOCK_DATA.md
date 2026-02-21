# Troubleshooting: Stock Data Not Appearing in Web UI

## Problem Description

When switching between different trading strategies (ATR, Insider Conviction, etc.), the webapp shows:
- ✅ Strategy results loaded (e.g., "1 best performers, 3 trades")
- ✅ Trade markers data is present in console
- ❌ **Stock price chart fails to load with 404 or 500 error**
- ❌ UI shows "No backtest data available"

## Root Causes & Solutions

### Issue 1: Node.js String Length Limit (ERR_STRING_TOO_LONG)

**Symptom:**
```
Error: Cannot create a string longer than 0x1fffffe8 characters
```

**Cause:**
The full yfinance cache (`yfinance_cache_full.json`) is ~1GB with 3,171 stocks. Node.js V8 engine has a maximum string length of ~512MB, so `fs.readFileSync()` fails when loading the entire file.

**Solution:**
Use Python to extract just the needed ticker instead of loading the entire cache:

```javascript
// webapp-stocks/server.js - Stock history endpoint

// Try top performers cache first (small file, 12MB - safe to load)
if (fs.existsSync(topPerformersCachePath)) {
  const topCache = JSON.parse(fs.readFileSync(topPerformersCachePath, 'utf-8'));
  if (topCache.data && topCache.data[ticker]) {
    stockData = topCache.data[ticker];
  }
}

// Fall back to full cache using Python extraction
if (!stockData && fs.existsSync(fullCachePath)) {
  console.log(`🔍 [STOCK] ${ticker} not in top performers cache, extracting from full cache...`);
  
  try {
    const pythonCmd = `.venv/bin/python -c "import json; f=open('output CSVs/yfinance_cache_full.json'); data=json.load(f); print(json.dumps(data['data'].get('${ticker}', None)))"`;
    const result = execSync(pythonCmd, { 
      cwd: path.join(__dirname, '..'),
      encoding: 'utf-8',
      maxBuffer: 50 * 1024 * 1024 // 50MB buffer for single ticker
    });
    
    const tickerData = JSON.parse(result);
    if (tickerData && tickerData !== null) {
      stockData = tickerData;
    }
  } catch (pythonError) {
    console.error(`❌ [STOCK] Failed to extract ${ticker}:`, pythonError.message);
  }
}
```

### Issue 2: ES Module `require` Not Defined

**Symptom:**
```
require is not defined
```

**Cause:**
Server.js uses ES modules (`import`/`export`), not CommonJS (`require`). The code attempted to use `require('child_process')` inside a function, which doesn't exist in ES module scope.

**Solution:**
Import `execSync` at the top of the file with the other imports:

```javascript
// WRONG - CommonJS in ES module
const { execSync } = require('child_process');  // ❌ Error: require is not defined

// CORRECT - ES module import
import { spawn, execSync } from 'child_process';  // ✅ At top of file
```

## Quick Diagnostic Checklist

When stock data isn't loading in the webapp:

### 1. Check Server Logs
```bash
tail -50 logs/node-server.log | grep -E "STOCK|ERROR"
```

Look for:
- `❌ [STOCK] <TICKER> not found in any cache`
- `Error: Cannot create a string longer than...`
- `require is not defined`
- `Failed to extract <TICKER> from full cache`

### 2. Test API Endpoint Directly
```bash
curl "http://localhost:3001/api/stock-history/BLNE?period=1y" | head -50
```

Should return JSON with `{"success":true,"ticker":"BLNE","history":[...]}`. If it returns error, check logs immediately.

### 3. Verify Ticker in Cache
```bash
.venv/bin/python -c "import json; f=open('output CSVs/yfinance_cache_full.json'); data=json.load(f); ticker='BLNE'; print(f'Found: {ticker in data[\"data\"]}')"
```

### 4. Check Browser Cache
Hard refresh the browser:
- **Mac:** Cmd+Shift+R
- **Windows:** Ctrl+Shift+R
- Or open in incognito/private window

The browser may cache 404 responses even after the backend is fixed.

## Step-by-Step Fix Procedure

### When Adding New Strategy Results:

1. **Create results JSON file** (e.g., `atr_strategy_results.json`)
   - Ensure `top_25_best` array is populated
   - Include individual `trades` array for each stock

2. **Update server.js strategy parameter handling**
   ```javascript
   const strategy = req.query.strategy || 'atr';
   const resultsFile = strategy === 'atr' 
     ? 'atr_strategy_results.json'
     : 'insider_conviction_all_stocks_results.json';
   ```

3. **Verify stock-history endpoint works**
   - Check imports: `import { spawn, execSync } from 'child_process';`
   - Check Python extraction code is present
   - Test with curl command above

4. **Restart webapp**
   ```bash
   ./restart_webapp_stocks.sh
   ```

5. **Monitor logs for errors**
   ```bash
   tail -f logs/node-server.log
   ```
   Then refresh browser and watch for stock-history requests

6. **Hard refresh browser** to clear cache

## Prevention Tips

- **Always test API endpoint** with curl before blaming frontend
- **Check logs immediately** when stock data fails to load
- **Use Python extraction** for large cache files (>500MB)
- **ES modules only** - never use `require()` in server.js
- **Hard refresh browser** after backend changes

## Related Files

- `webapp-stocks/server.js` - Backend API (stock-history endpoint around line 319)
- `output CSVs/yfinance_cache_full.json` - Full price cache (~1GB, 3,171 stocks)
- `output CSVs/yfinance_cache_top_performers.json` - Small cache (~12MB, 28 stocks)
- `output CSVs/atr_strategy_results.json` - ATR strategy results
- `output CSVs/insider_conviction_all_stocks_results.json` - Original strategy results

## Common Mistakes

1. ❌ Using `fs.readFileSync()` on full cache without size check
2. ❌ Using `require()` in ES module context
3. ❌ Forgetting to restart webapp after server.js changes
4. ❌ Not hard-refreshing browser after fixing backend
5. ❌ Assuming frontend is broken when backend has errors

## Success Indicators

- ✅ Curl returns JSON with price history
- ✅ Server logs show `✅ [STOCK] Extracted BLNE from full cache`
- ✅ Browser network tab shows 200 response for `/api/stock-history/BLNE`
- ✅ Chart renders with trade markers visible
- ✅ No console errors in browser
