# OpenInsider URL Analysis Report
**Date:** February 13, 2026
**Objective:** Determine whether extended screener URL provides more insider trading data than simple search URL

## Summary

### RECOMMENDATION: ✅ SWITCH TO EXTENDED URL

The extended screener URL provides **+233 trades (+59.9% more data)** with **ZERO data loss** across all tested stocks.

---

## Test Methodology

### Baseline Approach (Current)
```
http://openinsider.com/search?q={TICKER}
```
- **Limitation:** Only shows ~2 years of data
- **Data returned:** 389 trades across 50 stocks
- **Success rate:** 100% (50/50 stocks)
- **Avg trades per stock:** 7.8

### Extended Approach (Proposed)
```
http://openinsider.com/screener?s={TICKER}&fd=1461&xp=1&cnt=1000&page=1
```
- **Advantage:** Shows ~4 years of data (1461 days)
- **Data returned:** 622 trades across 50 stocks
- **Success rate:** 100% (50/50 stocks)
- **Avg trades per stock:** 12.4

---

## Test Results

### Dataset
- **Source:** Top Monthly Insider Trades
- **Total tickers tested:** 50 stocks
- **Test date:** 2026-02-13

### Comparison Breakdown
| Metric | Simple URL | Extended URL | Difference |
|--------|------------|--------------|------------|
| Success rate | 100.0% | 100.0% | 0% |
| Total trades | 389 | 622 | **+233 (+59.9%)** |
| Avg per stock | 7.8 | 12.4 | **+4.6 (+59.0%)** |
| Stocks w/ MORE data | - | 26 (52.0%) | - |
| Stocks w/ SAME data | - | 24 (48.0%) | - |
| Stocks w/ LESS data | - | **0 (0.0%)** | - |

---

## Top 10 Biggest Gainers

| Ticker | Simple | Extended | Gain | Simple Date Range | Extended Date Range |
|--------|--------|----------|------|-------------------|---------------------|
| **VANI** | 21 | 74 | **+53** | 2023-11-22 to 2026-01-27 | **2022-05-18** to 2026-01-27 |
| **ASA** | 77 | 113 | **+36** | 2024-11-14 to 2026-02-11 | **2022-07-05** to 2026-02-11 |
| **STEX** | 10 | 34 | **+24** | 2025-07-25 to 2026-02-04 | **2022-05-20** to 2026-02-04 |
| **IMDX** | 15 | 38 | **+23** | 2024-04-11 to 2026-02-10 | **2022-03-15** to 2026-02-10 |
| **GEF** | 29 | 44 | **+15** | 2024-03-05 to 2026-02-09 | **2022-04-07** to 2026-02-09 |
| **LXRX** | 1 | 15 | **+14** | 2026-02-02 only | **2022-08-01** to 2026-02-02 |
| **SHCO** | 2 | 13 | **+11** | 2024-06-20 to 2026-01-29 | **2022-06-16** to 2026-01-29 |
| **PMN** | 9 | 19 | **+10** | 2024-07-31 to 2026-02-03 | **2022-07-11** to 2026-02-03 |
| **GME** | 10 | 19 | **+9** | 2024-04-08 to 2026-01-23 | **2022-03-21** to 2026-01-23 |
| **YYAI** | 6 | 12 | **+6** | 2025-10-08 to 2026-01-21 | **2022-07-15** to 2026-01-21 |

---

## Technical Discoveries

### Issue #1: xs Parameter
**Problem:** The user's example URL included `xs=1` which filters for **SALES** not **PURCHASES**
**Solution:** Remove `xs=1` parameter for purchase data

### Issue #2: SIC Filters
**Problem:** Parameters `sicl=100&sich=9999` excluded funds/investment companies (SIC < 100)
- ASA Gold was filtered out (77 → 2 trades)
- NFRX showed 0 trades when it should show 5

**Solution:** Remove SIC filters to include all company types

### Final URL Parameters
```python
params = {
    's': ticker,           # Stock symbol
    'fd': '1461',         # Filing days back (~4 years)
    'xp': '1',            # Exclude certain transaction types
    'cnt': '1000',        # Max results per page
    'page': '1'           # Page number
}
```

---

## Implementation Notes

### Current Script to Update
- **File:** `scripts/openinsider_scraper.py`
- **Function:** `scrape_ticker_details()` (line ~24)

### Current Implementation
```python
url = f"http://openinsider.com/search?q={ticker}"
```

### Proposed Implementation
```python
url = "http://openinsider.com/screener"
params = {
    's': ticker,
    'fd': '1461',  # ~4 years of data
    'xp': '1',
    'cnt': '1000',
    'page': '1'
}
response = requests.get(url, params=params, headers=headers, timeout=30)
```

---

## Benefits

### Quantitative
- **59.9% more trades** discovered
- **NO data loss** for any stock
- **100% success rate** maintained
- **4-year historical data** vs 2-year

### Qualitative
- Better trend analysis with longer history
- More insider trades per stock discovered
- Includes all company types (funds, etc.)
- Same parsing logic - no code changes needed

---

## Conclusion

The extended URL approach is a clear winner:
- ✅ Significantly more data (+59.9%)
- ✅ Zero data loss
- ✅ Longer historical period
- ✅ Same success rate
- ✅ Minimal code changes required

**Recommendation:** Proceed with migration to extended URL format immediately.

---

## Test Artifacts

### Scripts
- `scripts/test_openinsider_url_comparison.py` - Main comparison test
- `scripts/investigate_problematic_tickers.py` - Investigation script
- `scripts/test_asa_filters.py` - Parameter testing

### Logs
- `logs/url_comparison_20260213_155319.json` - Detailed results with all ticker comparisons
