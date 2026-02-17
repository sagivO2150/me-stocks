# Pyramid Strategy Implementation Summary

## What Was Implemented

Added a "pyramid on insider confirmation" feature to the backtest strategy. When we already hold a profitable position and insiders buy again with significant amounts, the strategy now adds to the position.

## Pyramid Entry Conditions

The strategy will add to an existing position when ALL of the following are met:

1. **Already holding a position** in that stock
2. **Position is profitable** (>50% gain from entry)
3. **C-suite insider** (CEO, CFO, COO, President, Chief)
4. **Large transaction** ($500K+ purchase)
5. **Good reputation** stock (position_multiplier > 0)

## Position Sizing

- **New positions**: Full size based on reputation ($1000 base × reputation multiplier)
- **Pyramid additions**: 50% of base ($500) to preserve capital

## FTAI Example - Before vs After

### BEFORE (Single Position Only)
```
Entry: 2023-03-15 at $22.31
Exit:  2026-02-13 at $279.85
Invested: $1,000
Profit: $11,546 (+1154.6%)
```

### AFTER (Pyramid Strategy)
```
Position 1: 2023-03-15 at $22.31 → $279.85 = +$11,546 (Original)
Position 2: 2024-05-30 at $80.11 → $279.85 = +$1,247 (Pyramid on CEO $4.8M buy)
Position 3: 2025-05-02 at $89.33 → $153.57 = +$360 (Pyramid on COO $624K buy)
Position 4: 2025-11-13 at $153.00 → $279.85 = +$415 (Pyramid on COO $1M buy)

Total Invested: $3,500
Total Profit: $13,514 (+386.1% ROI)

IMPROVEMENT: $1,968 additional profit!
```

## Key Insights

### Why Some Trades Were Still Skipped

1. **2022-11-09 trade**: Stopped out at -5.3% (entered before explosive catalyst)
2. **2025-02-28 trade (Dir $283K)**: Not C-suite + too small (<$500K)
3. **2025-05-02 trade (Adams $284K)**: Too small (<$500K)
4. **2025-05-05 trade (Dir $99K)**: Not C-suite + too small
5. **2025-11-14 trade (CFO $100K)**: Too small

The strategy is still selective - it only pyramids on MAJOR insider purchases (C-suite, $500K+).

## Overall Backtest Performance

- **Total Trades**: 6,157
- **Win Rate**: 26.0%
- **Average Return**: +6.70%
- **Portfolio ROI**: +6.57%

The pyramid feature helps capture MORE of explosive moves when insiders continue buying into strength.

## Implementation Location

Modified: `scripts/backtests/backtest_batch_1_data.py`
- Lines 648-700: Added pyramid logic before position creation
- Checks if ticker already has open position
- Evaluates profitability and insider/transaction quality
- Creates smaller position (50% size) for pyramids

## Technical Notes

- Does NOT require explosive catalyst for pyramid entries (only for new positions)
- Allows multiple positions per ticker (up to 4+ if conditions keep being met)
- Each position is tracked independently with its own entry price and exit criteria
- Exit strategy (stop loss, trend reversal) applies to each position separately
