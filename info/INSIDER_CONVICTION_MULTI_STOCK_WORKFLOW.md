# Insider Conviction Strategy - Multi-Stock Workflow

## Overview
This workflow allows you to run the Insider Conviction Strategy on all stocks in the database and then drill down into specific stocks for detailed analysis.

## Two-Script Workflow

### 1. Main Analysis Script (Run on All Stocks)
**Script:** `scripts/backtests/backtest_all_stocks_insider_conviction.py`

**Purpose:** Analyze all stocks and generate summary results with top 25 best/worst performers

**How to run:**
```bash
.venv/bin/python /Users/sagiv.oron/Documents/scripts_playground/stocks/scripts/backtests/backtest_all_stocks_insider_conviction.py
```

**Output:**
- `output CSVs/insider_conviction_all_stocks_results.json` - Contains:
  - Overall ROI across all stocks
  - Overall statistics (win rate, total profit, etc.)
  - Top 25 best performers (sorted by ROI)
  - Top 25 worst performers (sorted by ROI)
  - Full results for all stocks analyzed

**What it does:**
- Loads all stocks from `merged_insider_trades.json`
- Runs the insider conviction strategy on each stock
- Tracks buy/sell signals using the same logic as the GROV POC
- Calculates ROI, win rate, average returns for each stock
- Displays top 25 best and worst performers
- Saves comprehensive results to JSON for webapp integration

---

### 2. Detailed Analysis Script (Run on Demand)
**Script:** `scripts/analysis/generate_stock_detailed_analysis.py`

**Purpose:** Generate detailed drill-down files (CSV/XLSX/JSON) for a specific stock

**How to run:**
```bash
.venv/bin/python /Users/sagiv.oron/Documents/scripts_playground/stocks/scripts/analysis/generate_stock_detailed_analysis.py TICKER
```

**Example:**
```bash
.venv/bin/python /Users/sagiv.oron/Documents/scripts_playground/stocks/scripts/analysis/generate_stock_detailed_analysis.py GME
```

**Output:** (using GME as example)
- `output CSVs/gme_rise_events.csv` - Rise/fall events with dates, percentages, ranks
- `output CSVs/gme_rise_events.xlsx` - Color-coded Excel (green=rise, pink=fall)
- `output CSVs/gme_rise_volatility_analysis.json` - Detailed volatility analysis:
  - Mid-rises and mid-falls during each rise event
  - First dip, recovery, and second dip after each rise
  - Insider purchase dates
  - Days held and percentages

**What it does:**
- Loads insider trades for the specific ticker
- Fetches price data from yfinance
- Tracks all rise/fall events throughout stock history
- Analyzes volatility patterns (mid-rises, mid-falls)
- Generates formatted CSV, Excel, and JSON files for detailed analysis

---

## Workflow Example

### Step 1: Run Main Analysis
```bash
.venv/bin/python scripts/backtests/backtest_all_stocks_insider_conviction.py
```

**Output:**
```
================================================================================
OVERALL STATISTICS
--------------------------------------------------------------------------------
Stocks Analyzed:           29
Total Trades:              51
Winning Trades:            36 (70.6%)
Total Profit:              $-360.59
Total Invested:            $102,000.00
Overall ROI:               -0.35%

TOP 25 BEST PERFORMERS:
--------------------------------------------------------------------------------
Rank  Ticker   Trades  ROI %      Win Rate   Avg Return  
--------------------------------------------------------------------------------
1     GME      2          +63.27%    100.0%      +63.27%
2     HYMC     1          +42.19%    100.0%      +42.19%
3     UAA      1          +40.12%    100.0%      +40.12%
...
```

### Step 2: Identify Interesting Stocks
Look at the top/worst performers and choose stocks to analyze further.

### Step 3: Generate Detailed Analysis
```bash
# For GME (best performer)
.venv/bin/python scripts/analysis/generate_stock_detailed_analysis.py GME

# For YYAI (worst performer)
.venv/bin/python scripts/analysis/generate_stock_detailed_analysis.py YYAI
```

**Output:**
```
================================================================================
GENERATING DETAILED ANALYSIS FOR GME
================================================================================
✓ CSV saved to: output CSVs/gme_rise_events.csv
✓ Excel saved to: output CSVs/gme_rise_events.xlsx
✓ Volatility JSON saved to: output CSVs/gme_rise_volatility_analysis.json
```

### Step 4: Analyze the Detailed Files
- Open `gme_rise_events.xlsx` in Excel to see color-coded rise/fall events
- Review `gme_rise_volatility_analysis.json` to understand:
  - Which rises had the most mid-volatility
  - Post-rise behavior (dip-recovery-dip patterns)
  - Insider purchase timing relative to rises/falls

---

## Strategy Details

### Buy Signals

1. **Shopping Spree** (Hot Stocks)
   - Insiders buy during rise AND continue during fall
   - Target = Peak stock price during shopping spree period
   - Requires 3 consecutive up days for entry (conservative)

2. **Absorption Buy** (Fall-Only)
   - Insiders buy ONLY during fall (minimum $5K invested)
   - Target = Recover what was lost (fall percentage)
   - Requires 2 consecutive up days for entry

### Sell Signals

1. **For Shopping Spree:**
   - Stop loss: -15% from entry
   - After target reached: Sell on first dip >1%

2. **For Absorption Buy:**
   - No stop loss
   - Sell when cumulative rise from entry ≥ fall percentage
   - BUT only if not currently in a mid-rise (wait for dip)

3. **Stagnation:**
   - Exit after 60 days if target not reached and gain <5%

---

## Files Generated

### Main Analysis Output
```
output CSVs/
├── insider_conviction_all_stocks_results.json    # Main results file for webapp
```

### Detailed Analysis Outputs (per stock)
```
output CSVs/
├── {ticker}_rise_events.csv                      # CSV with rise/fall events
├── {ticker}_rise_events.xlsx                     # Color-coded Excel
└── {ticker}_rise_volatility_analysis.json        # Detailed volatility JSON
```

---

## Webapp Integration

The main results file (`insider_conviction_all_stocks_results.json`) contains:

```json
{
  "analysis_date": "2026-02-19 17:25:58",
  "strategy": "Insider Conviction (No Hindsight)",
  "overall_stats": {
    "stocks_analyzed": 29,
    "total_trades": 51,
    "winning_trades": 36,
    "overall_win_rate": 70.6,
    "total_profit": -360.59,
    "total_invested": 102000,
    "overall_roi": -0.35
  },
  "top_25_best": [
    {
      "ticker": "GME",
      "company_name": "GME",
      "total_trades": 2,
      "winning_trades": 2,
      "losing_trades": 0,
      "win_rate": 100.0,
      "target_rate": 100.0,
      "total_profit": 2530.82,
      "total_invested": 4000,
      "roi": 63.27,
      "avg_return": 63.27,
      "median_return": 122.07,
      "max_return": 122.07,
      "min_return": 42.19,
      "avg_days_held": 153.0
    },
    ...
  ],
  "top_25_worst": [...],
  "all_results": [...]
}
```

This can be displayed in the "Best/Worst" section of the webapp.

---

## Key Differences from GROV POC

1. **Main script** runs on ALL stocks but does NOT generate CSV/XLSX/JSON files
2. **On-demand script** generates detailed files only for requested stocks
3. **Separation of concerns:**
   - Main = broad analysis, identify opportunities
   - Detailed = deep dive, understand specific stock behavior
4. **Performance:** Running detailed analysis on all stocks would take hours and generate hundreds of files
5. **Workflow:** Analyze all → identify interesting → drill down on specific stocks

---

## Next Steps

1. ✅ Main analysis script created and tested
2. ✅ On-demand detailed analysis script created and tested
3. ✅ Both scripts working correctly
4. ⏳ Integrate JSON results into webapp "Best/Worst" section
5. ⏳ Add UI button to generate detailed analysis for specific stocks

---

## Notes

- The main script processes ~50 stocks in about 2-3 minutes
- Detailed analysis for one stock takes ~5-10 seconds
- All output files are saved to `output CSVs/` directory
- The strategy uses NO HINDSIGHT - simulates live trading day-by-day
- Position size is fixed at $2,000 per trade
