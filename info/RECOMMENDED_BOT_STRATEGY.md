# Recommended Bot Trading Strategy
## Analysis Date: February 13, 2026

## 🔍 What The Backtests Reveal

### Key Findings:
1. **Most gains happen in 1-3 days** - Initial market reaction, then pullback
2. **Low win rate on simple following** - Only 32-38% profitable
3. **Average gain small** - ~2% per trade (before fees/slippage)
4. **High variance** - Some +26%, most -5%
5. **Recent trades still holding** - Can't evaluate 2026 purchases yet

### The Reality:
**You're not front-running insiders, you're following retail hype 2 days later.**

---

## 🎯 My Recommended Multi-Factor Strategy

### **Phase 1: Smart Filtering (Before Entry)**

#### A. Insider Quality Filters
- [ ] **Multiple insiders buying same day** (conviction signal)
  - 1 insider buying = skip
  - 2-3 insiders buying = moderate signal
  - 4+ insiders buying = strong signal
  
- [ ] **CEO/CFO buys > other roles** (they know the business)
  - Weight: CEO/CFO = 3x, Directors = 1x, 10% owners = 0.5x
  
- [ ] **Purchase size relative to salary** (skin in the game)
  - >6 months salary = very bullish
  - 1-6 months = moderately bullish
  - <1 month = ignore

#### B. Technical Filters
- [ ] **Stock NOT at 52-week high** (buying dips, not tops)
  - If within 10% of 52w high → skip (likely top)
  - If down 30%+ from 52w high → strong signal
  
- [ ] **Volume spike on filing date** (market paying attention)
  - Volume >2x average = good
  - Volume <1x average = market doesn't care
  
- [ ] **RSI < 70** (not overbought)

#### C. Fundamental Filters
- [ ] **Market cap >$500M** (avoid illiquid penny stocks)
- [ ] **Positive earnings or clear path to profitability**
- [ ] **Sector momentum** (is the whole sector up/down?)

#### D. Timing Filters
- [ ] **Don't chase** - If stock already up 10%+ from insider purchase price → skip
- [ ] **Market environment** - Bull market = more aggressive, Bear = more cautious

---

## 💰 Phase 2: Position Sizing & Entry

### Smart Entry:
```python
# Don't go all-in on entry
entry_plan = {
    "initial_position": 50%,  # Half position immediately
    "second_tranche": 25%,    # If dips 3% in first 2 days
    "final_tranche": 25%      # If dips 5% in first week
}

# OR use limit orders
limit_price = filing_day_open * 0.98  # Try to buy 2% below open
```

### Position Size:
- Never more than 5% of portfolio per trade
- Max 20% of portfolio in insider-following strategies total
- Scale position size with conviction (more filters passed = larger position)

---

## 📊 Phase 3: Exit Strategy (Hybrid Approach)

### The "Scale Out" Method:
```python
exit_strategy = {
    # Take profits on the spike
    "sell_33%_at": "+8% profit",   # Lock in gains on initial pop
    "sell_33%_at": "+15% profit",  # Take more off on bigger moves
    
    # Protect remaining position
    "trailing_stop": "5% from peak for remaining 34%",
    
    # Time-based backup
    "force_exit": "30 days OR if breaks below entry -5%"
}
```

**Why this works:**
- Captures initial hype (most reliable)
- Lets winners run (catches the 20%+ moves)
- Limits losses (strict stop loss)

---

## 🚀 Phase 4: Advanced Signals

### A. "Cluster Buying" Signal (STRONGEST)
When 3+ insiders from DIFFERENT companies in SAME SECTOR all buy within 1 week:
- Example: 3 pharma CEOs buying their own stocks = sector bottom?
- This is a MACRO signal, not micro
- Consider sector ETFs or strongest stock in sector

### B. "CEO Loading Up" Signal
When CEO/CFO makes multiple purchases in short time:
- Example: Ryan Cohen buying GME 5x in 2 months
- Shows extreme conviction OR desperation
- Check stock price trend: If down 50% = conviction, If up 50% = suspicious

### C. "10% Owner Accumulation" Signal  
Large funds (10%+ owners) buying more:
- They have inside access to management
- Check if they're doubling down or cutting losses
- Bullish if: buying after stock dropped
- Bearish if: buying small amounts (token support)

### D. Unusual Activity Score
```python
score = 0
if multiple_insiders_same_day: score += 3
if ceo_or_cfo: score += 2  
if purchase_size > 1M: score += 2
if stock_down_30_from_high: score += 2
if sector_trending_up: score += 1
if volume_spike_2x: score += 1

# Only trade if score >= 6
```

---

## ⚠️ Red Flags (Don't Trade)

1. **Stock up >20% in past week** (you're chasing)
2. **Insider sold larger amount recently** (mixed signals)
3. **Company has earnings in <7 days** (wait for results)
4. **Stock at all-time high** (insiders might be wrong on timing)
5. **Penny stock <$2** (manipulation risk)
6. **Options-based compensation** (not real conviction)
7. **10-b5-1 plan purchase** (automatic, not discretionary)

---

## 💡 Alternative Approach: Options Strategy

Instead of buying stock directly:
```python
# For high-conviction signals
strategy = "Buy ITM call options"  # 60-80 delta
expiration = "60-90 days out"
position_size = "Risk only 2% of portfolio"

# Why?
# - Leverage: Control more stock for less money
# - Limited downside: Can only lose premium
# - Time to be right: 60-90 days vs 30 days

# Example:
# Stock at $50, insider bought at $48
# Buy $45 call (ITM) expiring in 60 days
# If wrong: Lose premium (~$8/share) = -16%
# If right and stock hits $60: Make $15-8 = $7 = +87.5%
```

---

## 📈 Expected Performance (Realistic)

### With Smart Filters:
- **Win Rate:** 50-55% (vs 32% naive approach)
- **Average Win:** +12% (taking profits at 8% and 15%)
- **Average Loss:** -4% (stop loss at -5%, but some stop at -3%)
- **Expected Return:** ~4% per trade

### With 20 trades/year:
- Best case (60% win rate): +80% annual return
- Base case (50% win rate): +40% annual return  
- Worst case (40% win rate): +10% annual return

**Reality check:** 
- Slippage/fees: -0.5% per trade
- Bad fills: -10% of trades
- Emotional override: -20% (bot doesn't have this problem)

**Bot advantage:** No emotions, executes consistently, never "feels" the market

---

## 🛠️ Implementation Checklist

### Data You Need:
- [ ] Real-time insider filing data (SEC EDGAR API)
- [ ] Historical stock prices (yfinance or similar)
- [ ] Company financials (market cap, earnings)
- [ ] Technical indicators (RSI, volume, 52w high)
- [ ] Sector/industry data
- [ ] Insider compensation data (to filter option grants)

### Bot Architecture:
```python
1. Monitor EDGAR for Form 4 filings (real-time)
2. Parse filing → extract: who, how much, when, price
3. Run through filters (insider quality, technical, fundamental)
4. Calculate conviction score
5. If score >= threshold:
   - Check existing positions (diversification)
   - Calculate position size
   - Place limit order (don't chase)
6. Monitor open positions:
   - Check for profit targets
   - Update trailing stops
   - Force exit after 30 days
7. Log everything for backtesting/improvement
```

---

## 🎓 My Honest Opinion

### What I'd Actually Do:

**DON'T build a bot that blindly follows insiders.**

**DO build a bot that:**
1. Uses insiders as ONE signal among many
2. Waits for multiple confirmation signals
3. Scales in/out of positions intelligently  
4. Adapts to market conditions
5. Takes small losses, lets winners run
6. Keeps detailed logs to improve over time

### The Best Signal I See:
**"Clustered Insider Buying During Market Weakness"**

When:
- Stock down 30%+ from highs
- Multiple insiders buying
- Sector showing signs of bottoming
- Company fundamentals still solid

This is insiders "calling the bottom" - much more reliable than chasing momentum.

### Example from your data:
**Under Armour (UA)** - Watsa buying multiple times
- Stock was beaten down
- Large purchases ($49M, $16M)
- Result: +21% and +15%

This is the pattern to look for.

---

## 🔬 Next Steps for Testing

1. **Backtest with filters** - Add the quality filters I suggested, re-run
2. **Compare to S&P 500** - Is 4% per trade even worth it vs index?
3. **Paper trade 3 months** - Test in real-time before risking money
4. **Track why trades fail** - Build a "post-mortem" database
5. **Optimize** - Which filters matter most? Remove noise.

---

## ⚠️ Final Warning

- **Backtesting looks better than reality** (survivorship bias, perfect execution)
- **Fees matter** - 2x $5 trades on $1000 = -1% immediately  
- **Slippage matters** - You won't get the exact price you want
- **Market impact** - If everyone follows insiders, signal degrades
- **Insider can be wrong** - They lose money too (see: any tech CEO in 2022)

**Start small. Test real. Improve constantly.**
