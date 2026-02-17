#!/usr/bin/env python3
"""
REPUTATION-BASED TREND FOLLOWING STRATEGY
==========================================
Builds on the 19% explosive catalyst strategy by adding insider/stock reputation tracking.

REPUTATION SYSTEM:
- Tracks performance for each ticker after insider purchases
- Rewards stocks that spike after insider buys (regardless of our P/L)
- Punishes stocks where insiders buy but stock doesn't perform
- Adjusts stop-loss and position sizing based on reputation

SCORING:
- Good: Stock gains 20%+ within 30 days after insider purchase → Relax stop loss, increase position
- Bad: Stock fails to gain or loses after insider purchases → Tighter stop loss, decrease position
- Neutral: First time seeing insider/stock combo → Use baseline strategy

Based on commit: e0d99c6498bfec77c26751fe73fcc6e997f66c60 (19% explosive catalyst test)
"""

import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from multiprocessing import Pool, cpu_count
import threading

# Global progress counter with lock
progress_counter = 0
progress_lock = threading.Lock()

# ===== REPUTATION SYSTEM =====

class ReputationTracker:
    """
    Track and score insider/ticker combinations based on historical post-purchase performance.
    
    Scoring Criteria:
    - Positive points: Stock gained 20%+ within 30 days after purchase
    - Negative points: Stock failed to gain 10%+ or dropped within 30 days
    - Neutral: Not enough data yet
    """
    
    def __init__(self):
        self.ticker_scores = defaultdict(lambda: {'events': [], 'score': 0, 'total_purchases': 0})
        
    def record_purchase_outcome(self, ticker, insider, purchase_date, entry_price, peak_price_30d, days_to_peak):
        """
        Record outcome of an insider purchase for reputation tracking.
        
        Args:
            ticker: Stock ticker
            insider: Insider name
            purchase_date: Date of purchase
            entry_price: Price at entry
            peak_price_30d: Highest price reached within 30 days
            days_to_peak: Days to reach peak
        """
        if peak_price_30d is None or entry_price is None or entry_price == 0:
            return
        
        gain_pct = ((peak_price_30d - entry_price) / entry_price) * 100
        
        event = {
            'insider': insider,
            'date': purchase_date,
            'entry_price': entry_price,
            'peak_price': peak_price_30d,
            'gain_pct': gain_pct,
            'days_to_peak': days_to_peak
        }
        
        self.ticker_scores[ticker]['events'].append(event)
        self.ticker_scores[ticker]['total_purchases'] += 1
        
        # Score the outcome
        if gain_pct >= 20.0:
            # Excellent - stock spiked after insider purchase
            points = 2
        elif gain_pct >= 10.0:
            # Good - decent gain
            points = 1
        elif gain_pct >= 0:
            # Neutral/slight gain
            points = 0
        else:
            # Bad - lost money
            points = -1
            
        self.ticker_scores[ticker]['score'] += points
        
    def get_reputation(self, ticker):
        """
        Get reputation score and category for a ticker.
        
        Returns:
            dict: {
                'score': raw score,
                'category': 'excellent'/'good'/'neutral'/'poor'/'unknown',
                'total_purchases': count,
                'avg_gain': average gain percentage,
                'stop_loss_multiplier': adjustment to stop loss (1.0 = baseline),
                'position_multiplier': adjustment to position size (1.0 = baseline)
            }
        """
        if ticker not in self.ticker_scores or self.ticker_scores[ticker]['total_purchases'] == 0:
            return {
                'score': 0,
                'category': 'unknown',
                'total_purchases': 0,
                'avg_gain': 0,
                'stop_loss_multiplier': 1.0,  # Baseline
                'position_multiplier': 1.0     # Baseline
            }
        
        data = self.ticker_scores[ticker]
        score = data['score']
        total = data['total_purchases']
        avg_score_per_purchase = score / total if total > 0 else 0
        
        # Calculate average gain
        gains = [e['gain_pct'] for e in data['events']]
        avg_gain = sum(gains) / len(gains) if gains else 0
        
        # Categorize and set multipliers
        if avg_score_per_purchase >= 1.5:
            # Excellent track record
            category = 'excellent'
            stop_loss_multiplier = 1.0   # Keep standard stop loss
            position_multiplier = 1.0    # Standard position (trust the track record)
        elif avg_score_per_purchase >= 0.8:
            # Good track record
            category = 'good'
            stop_loss_multiplier = 1.0   # Keep standard stop loss
            position_multiplier = 1.0    # Standard position
        elif avg_score_per_purchase >= -0.5:
            # Neutral - DON'T TRADE
            category = 'neutral'
            stop_loss_multiplier = 1.0
            position_multiplier = 0.0    # SKIP THIS STOCK
        else:
            # Poor track record - DON'T TRADE
            category = 'poor'
            stop_loss_multiplier = 1.0
            position_multiplier = 0.0    # SKIP THIS STOCK
        
        return {
            'score': score,
            'avg_score': avg_score_per_purchase,
            'category': category,
            'total_purchases': total,
            'avg_gain': avg_gain,
            'stop_loss_multiplier': stop_loss_multiplier,
            'position_multiplier': position_multiplier
        }
    
    def print_reputation_report(self):
        """Print summary of all ticker reputations"""
        print(f"\n{'='*120}")
        print("TICKER REPUTATION REPORT")
        print(f"{'='*120}")
        print(f"{'Ticker':<8} {'Category':<12} {'Score':<8} {'Purchases':<12} {'Avg Gain':<12} {'SL Mult':<10} {'Pos Mult':<10}")
        print(f"{'-'*120}")
        
        # Sort by score descending
        sorted_tickers = sorted(self.ticker_scores.items(), 
                              key=lambda x: x[1]['score'], 
                              reverse=True)
        
        for ticker, data in sorted_tickers:
            rep = self.get_reputation(ticker)
            print(f"{ticker:<8} {rep['category']:<12} {rep['score']:<8} {rep['total_purchases']:<12} "
                  f"{rep['avg_gain']:>10.1f}% {rep['stop_loss_multiplier']:<10.2f} {rep['position_multiplier']:<10.2f}")
        
        print(f"{'='*120}\n")

# ===== HELPER FUNCTIONS (from original backtest) =====

def fetch_ticker_data(args):
    """Fetch historical data for a ticker with progress tracking"""
    ticker, total = args
    global progress_counter
    
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(start='2022-03-16', end='2026-02-14')
        
        # Update progress counter
        with progress_lock:
            progress_counter += 1
            if progress_counter % 10 == 0 or progress_counter == total:
                print(f"\rProgress: {progress_counter}/{total}", end='', flush=True)
        
        if not history.empty:
            history.index = history.index.tz_localize(None)
            return (ticker, history)
    except:
        pass
    
    # Still update progress even on failure
    with progress_lock:
        progress_counter += 1
        if progress_counter % 10 == 0 or progress_counter == total:
            print(f"\rProgress: {progress_counter}/{total}", end='', flush=True)
    
    return (ticker, None)

def parse_value(value_str):
    """Parse value string like '+$8,783,283' to float"""
    if not value_str:
        return 0
    cleaned = value_str.replace('+', '').replace('$', '').replace(',', '')
    try:
        return float(cleaned)
    except:
        return 0

def generate_business_days(start_date, end_date):
    """Generate list of business days between two dates"""
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    business_days = pd.bdate_range(start=start, end=end)
    return [d.strftime('%Y-%m-%d') for d in business_days]

def get_peak_price_in_window(history, start_date, days=30):
    """
    Get the peak price within X days after start_date.
    Returns (peak_price, days_to_peak)
    """
    start_ts = pd.Timestamp(start_date)
    end_ts = start_ts + pd.Timedelta(days=days)
    
    # Get prices in window
    mask = (history.index >= start_ts) & (history.index <= end_ts)
    window_data = history[mask]
    
    if window_data.empty:
        return None, 0
    
    peak_price = window_data['High'].max()
    peak_idx = window_data['High'].idxmax()
    days_to_peak = (peak_idx - start_ts).days
    
    return peak_price, days_to_peak

def detect_trend_reversal(position, current_date, history, reputation):
    """
    Detect trend reversal using SLOPE-BASED dip detection.
    Now uses reputation-adjusted stop loss.
    
    Args:
        position: Position dict
        current_date: Current date string
        history: Price history DataFrame
        reputation: Reputation dict with multipliers
    
    Returns: (should_exit, reason, exit_price)
    """
    current_date_ts = pd.Timestamp(current_date)
    
    if current_date_ts not in history.index:
        return (False, None, None)
    
    close_price = history.loc[current_date_ts, 'Close']
    high_price = history.loc[current_date_ts, 'High']
    
    # Add current price to history
    position['price_history'].append((current_date_ts, close_price))
    
    # Calculate current profit from entry
    current_profit_pct = ((close_price - position['entry_price']) / position['entry_price']) * 100
    
    # GRACE PERIOD: Don't exit in first 2 business days
    if position['days_held'] <= 2:
        return (False, None, None)
    
    # Update highest price and track peak
    if high_price > position['highest_price']:
        old_peak = position['highest_price']
        position['highest_price'] = high_price
        position['peak_date'] = current_date_ts
        position['peak_idx'] = len(position['price_history']) - 1
        
        # Track consecutive up days for sustained uptrend detection
        if close_price > position.get('last_close', position['entry_price']):
            position['consecutive_up_days'] = position.get('consecutive_up_days', 0) + 1
        else:
            position['consecutive_up_days'] = 1
        
        # Reset decline tracking on new high
        position['consecutive_decline_days'] = 0
        
        # EXPLOSIVE CATALYST DETECTION: Look for sharp announcement spike
        if not position.get('catalyst_detected', False):
            # Look back 3-5 days to detect explosive rise
            lookback_window = min(5, len(position['price_history']))
            if lookback_window >= 3:
                lookback_idx = len(position['price_history']) - lookback_window
                lookback_price = position['price_history'][lookback_idx][1]
                gain_pct = ((high_price - lookback_price) / lookback_price) * 100
                
                # Explosive: >20% gain in 3-5 days
                if gain_pct > 20.0:
                    position['catalyst_detected'] = True
                    position['catalyst_price'] = high_price
                    position['days_since_peak'] = 0
                    rep_category = reputation['category']
                    print(f"      🚀 EXPLOSIVE CATALYST for {position['ticker']} [{rep_category}]: +{gain_pct:.1f}% in {lookback_window} days!")
        
        # New high reached - reset dip tracking
        if high_price > old_peak * 1.02:  # At least 2% higher
            position['violent_dip_count'] = 0
            position['in_violent_dip'] = False
            position['failed_recovery'] = False
            position['days_since_peak'] = 0
    else:
        # Not a new high - increment days since peak
        position['days_since_peak'] = position.get('days_since_peak', 0) + 1
        
        # Track if we're going up or down
        if close_price < position.get('last_close', position['entry_price']):
            position['consecutive_up_days'] = 0
        else:
            position['consecutive_up_days'] = position.get('consecutive_up_days', 0) + 1
    
    position['last_close'] = close_price
    
    # REPUTATION-ADJUSTED STOP LOSS
    catalyst_detected = position.get('catalyst_detected', False)
    days_since_peak = position.get('days_since_peak', 0)
    
    # Calculate drawdown from peak
    peak = position['highest_price']
    drawdown_from_peak_pct = ((close_price - peak) / peak) * 100
    
    # Expire catalyst tracking if:
    # 1. No new high in 15+ days OR
    # 2. Dropped 15%+ from peak
    catalyst_expired = False
    if catalyst_detected and (days_since_peak >= 15 or drawdown_from_peak_pct <= -15.0):
        catalyst_expired = True
    
    # Apply REPUTATION-ADJUSTED stop loss
    base_stop_loss = -5.0
    adjusted_stop_loss = base_stop_loss * reputation['stop_loss_multiplier']
    
    # Apply stop loss if:
    # 1. No catalyst yet (waiting phase) OR
    # 2. Catalyst expired (trend over)
    if (not catalyst_detected or catalyst_expired) and current_profit_pct < adjusted_stop_loss:
        rep_info = f"{reputation['category']} (SL: {adjusted_stop_loss:.1f}%)"
        print(f"      🛑 STOP LOSS hit for {position['ticker']} [{rep_info}]: {current_profit_pct:.1f}%")
        return (True, 'stop_loss', close_price)
    
    # SLOPE-BASED DIP DETECTION: Only after catalyst detected
    if not catalyst_detected:
        return (False, None, None)
    
    # Calculate drawdown from peak
    drawdown_pct = ((close_price - peak) / peak) * 100
    
    # Detect violent dips
    if drawdown_pct < -3.0 and not position['in_violent_dip']:
        is_violent = False
        reason = ""
        
        current_idx = len(position['price_history']) - 1
        lookback = min(2, current_idx)
        if lookback > 0:
            lookback_idx = current_idx - lookback
            recent_prices = position['price_history'][lookback_idx:current_idx + 1]
            
            # Calculate slope: PERCENTAGE per day
            start_price = recent_prices[0][1]
            end_price = recent_prices[-1][1]
            days = len(recent_prices) - 1
            
            if days > 0 and start_price > 0:
                price_change_pct = ((end_price - start_price) / start_price) * 100
                slope_pct_per_day = price_change_pct / days
                slope_pct_abs = abs(slope_pct_per_day)
            else:
                slope_pct_per_day = 0
                slope_pct_abs = 0
            
            if position.get('violent_dip_count', 0) == 0:
                # First dip: needs to be steep enough (at least 5% per day drop)
                if slope_pct_abs > 5.0:
                    is_violent = True
                    position['first_dip_slope'] = slope_pct_abs
                    reason = f"slope {slope_pct_abs:.1f}%/day (first dip)"
            else:
                # Second dip: Compare slope to first dip's slope
                first_dip_slope = position.get('first_dip_slope', 0)
                if first_dip_slope > 0:
                    slope_ratio = slope_pct_abs / first_dip_slope
                    
                    # If current drop is at least 50% as steep as first dip → violent
                    if slope_ratio >= 0.5 and slope_pct_abs > 3.0:
                        is_violent = True
                        reason = f"slope {slope_pct_abs:.1f}%/day vs {first_dip_slope:.1f}%/day (ratio: {slope_ratio:.0%})"
            
            if is_violent:
                position['in_violent_dip'] = True
                position['violent_dip_count'] += 1
                position['dip_start_date'] = current_date_ts
                position['dip_start_idx'] = current_idx
                print(f"      🔻 DIP #{position['violent_dip_count']} for {position['ticker']} [{reputation['category']}]: {reason}")
    
    # Check if recovering from violent dip
    if position['in_violent_dip']:
        dip_start_idx = position['dip_start_idx']
        current_idx = len(position['price_history']) - 1
        
        if current_idx > dip_start_idx:
            dip_low = min([p for _, p in position['price_history'][dip_start_idx:current_idx + 1]])
            recovery_pct = ((close_price - dip_low) / dip_low) * 100
            
            # Recovery detected: at least 3% up from the low
            if recovery_pct > 3.0:
                peak = position['highest_price']
                if close_price > peak * 0.98:  # Within 2% of old peak
                    position['failed_recovery'] = False
                else:
                    position['failed_recovery'] = True
                
                position['in_violent_dip'] = False
    
    # DECISION: Sell on second violent dip after failed recovery
    if position['violent_dip_count'] >= 2 and position['in_violent_dip'] and position['failed_recovery']:
        print(f"      🚨 TREND REVERSED - EXITING {position['ticker']} [{reputation['category']}]")
        return (True, 'trend_reversal', close_price)
    
    return (False, None, None)

def backtest_with_reputation():
    """
    Backtest the trend following strategy with reputation system.
    
    TWO-PASS APPROACH:
    1. First pass: Build reputation scores by tracking all historical outcomes
    2. Second pass: Run strategy with reputation-adjusted parameters
    """
    
    print(f"\n{'='*120}")
    print("REPUTATION-BASED TREND FOLLOWING STRATEGY")
    print(f"{'='*120}\n")
    
    # Load insider trades data
    with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/expanded_insider_trades.json', 'r') as f:
        data = json.load(f)
    
    tickers = [stock['ticker'] for stock in data['data']]
    
    global progress_counter
    progress_counter = 0
    
    print(f"🔄 Loading stock data for {len(tickers)} tickers...")
    # Prepare args: (ticker, total_count)
    ticker_args = [(t, len(tickers)) for t in tickers]
    
    with Pool(cpu_count()) as pool:
        results = pool.map(fetch_ticker_data, ticker_args)
    
    print()  # New line after progress
    
    price_cache = {}
    for ticker, history in results:
        if history is not None:
            price_cache[ticker] = history
    
    print(f"   ✅ Loaded {len(price_cache)} stocks with price data\n")
    
    # Build all trades list
    all_trades = []
    for stock_data in data['data']:
        ticker = stock_data['ticker']
        
        if ticker not in price_cache:
            continue
        
        company = stock_data['company_name']
        
        for trade in stock_data['trades']:
            if trade.get('value', '').startswith('+'):
                trade_date = trade['trade_date']
                
                if 'filing_date' in trade and trade['filing_date']:
                    filing_date = trade['filing_date'].split()[0]
                else:
                    filing_date = trade_date
                
                entry_date = filing_date
                trade_value = parse_value(trade['value'])
                
                all_trades.append({
                    'ticker': ticker,
                    'company': company,
                    'trade_date': trade_date,
                    'entry_date': entry_date,
                    'insider': trade['insider_name'],
                    'role': trade.get('role', ''),
                    'value': trade_value
                })
    
    all_trades.sort(key=lambda x: x['entry_date'])
    
    if not all_trades:
        print("No trades found!")
        return []
    
    # ===== PASS 1: BUILD REPUTATION SCORES =====
    print(f"{'='*120}")
    print("PASS 1: BUILDING REPUTATION SCORES")
    print(f"{'='*120}\n")
    
    reputation_tracker = ReputationTracker()
    
    for trade in all_trades:
        ticker = trade['ticker']
        
        if ticker not in price_cache:
            continue
        
        history = price_cache[ticker]
        entry_date = trade['entry_date']
        
        current_date_ts = pd.Timestamp(entry_date)
        if current_date_ts not in history.index:
            available_dates = sorted([d for d in history.index if d >= current_date_ts])
            if not available_dates:
                continue
            actual_entry_date = available_dates[0]
        else:
            actual_entry_date = current_date_ts
        
        if actual_entry_date not in history.index:
            continue
        
        entry_price = history.loc[actual_entry_date, 'Close']
        
        # Get peak price within 30 days
        peak_price, days_to_peak = get_peak_price_in_window(history, actual_entry_date, days=30)
        
        # Record outcome for reputation
        reputation_tracker.record_purchase_outcome(
            ticker=ticker,
            insider=trade['insider'],
            purchase_date=entry_date,
            entry_price=entry_price,
            peak_price_30d=peak_price,
            days_to_peak=days_to_peak
        )
    
    # Print reputation report
    reputation_tracker.print_reputation_report()
    
    # ===== PASS 2: RUN BACKTEST WITH REPUTATION =====
    print(f"{'='*120}")
    print("PASS 2: RUNNING BACKTEST WITH REPUTATION-BASED ADJUSTMENTS")
    print(f"{'='*120}\n")
    
    start_date = all_trades[0]['entry_date']
    end_date = '2026-02-13'
    
    all_business_days = generate_business_days(start_date, end_date)
    
    open_positions = defaultdict(list)
    closed_trades = []
    pending_trades = list(all_trades)
    
    base_position_size = 1000
    
    for day_idx, current_date in enumerate(all_business_days):
        if day_idx % 50 == 0:
            print(f"📆 {current_date} (Day {day_idx+1}/{len(all_business_days)}) | Open: {sum(len(v) for v in open_positions.values())} | Closed: {len(closed_trades)}")
        
        # Open new positions
        trades_to_open = [t for t in pending_trades if t['entry_date'] == current_date]
        
        for trade in trades_to_open:
            ticker = trade['ticker']
            
            if ticker not in price_cache:
                pending_trades.remove(trade)
                continue
            
            history = price_cache[ticker]
            
            current_date_ts = pd.Timestamp(current_date)
            if current_date_ts not in history.index:
                available_dates = sorted([d for d in history.index if d >= current_date_ts])
                if not available_dates:
                    pending_trades.remove(trade)
                    continue
                actual_entry_date = available_dates[0].strftime('%Y-%m-%d')
            else:
                actual_entry_date = current_date
            
            actual_entry_ts = pd.Timestamp(actual_entry_date)
            entry_price = history.loc[actual_entry_ts, 'Close']
            
            # Get reputation for this ticker
            reputation = reputation_tracker.get_reputation(ticker)
            
            # FILTER: Skip neutral/poor reputation stocks entirely
            if reputation['position_multiplier'] == 0.0:
                print(f"   ⏭️  SKIPPING {ticker} [{reputation['category']}] - poor track record")
                pending_trades.remove(trade)
                continue
            
            # Adjust position size based on reputation
            position_size = base_position_size * reputation['position_multiplier']
            shares = position_size / entry_price
            
            if reputation['category'] != 'unknown':
                print(f"   📊 Opening {ticker} [{reputation['category']}]: Size=${position_size:.0f}")
            
            position = {
                'ticker': ticker,
                'company': trade['company'],
                'trade_date': trade['trade_date'],
                'entry_date': actual_entry_date,
                'entry_price': entry_price,
                'amount_invested': position_size,
                'shares': shares,
                'insider': trade['insider'],
                'role': trade['role'],
                'highest_price': entry_price,
                'days_held': 0,
                'violent_dip_count': 0,
                'in_violent_dip': False,
                'failed_recovery': False,
                'catalyst_detected': False,
                'consecutive_up_days': 0,
                'days_since_peak': 0,
                'first_dip_slope': 0,
                'last_close': entry_price,
                'peak_date': actual_entry_ts,
                'peak_idx': 0,
                'catalyst_price': 0,
                'dip_start_date': None,
                'dip_start_idx': 0,
                'price_history': [(actual_entry_ts, entry_price)],
                'reputation': reputation  # Store reputation data
            }
            
            open_positions[ticker].append(position)
            pending_trades.remove(trade)
        
        # Check all open positions for exit signals
        for ticker in list(open_positions.keys()):
            if ticker not in price_cache:
                continue
            
            history = price_cache[ticker]
            
            positions_to_close = []
            
            for pos in open_positions[ticker]:
                pos['days_held'] += 1
                
                # Get current reputation (may have been updated)
                reputation = reputation_tracker.get_reputation(ticker)
                
                should_exit, reason, exit_price = detect_trend_reversal(pos, current_date, history, reputation)
                
                if should_exit:
                    return_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
                    profit_loss = pos['amount_invested'] * (return_pct / 100)
                    returned_amount = pos['amount_invested'] + profit_loss
                    
                    closed_trades.append({
                        'ticker': ticker,
                        'company': pos['company'],
                        'trade_date': pos['trade_date'],
                        'entry_date': pos['entry_date'],
                        'entry_price': pos['entry_price'],
                        'exit_date': current_date,
                        'exit_price': exit_price,
                        'exit_reason': reason,
                        'amount_invested': pos['amount_invested'],
                        'returned_amount': returned_amount,
                        'profit_loss': profit_loss,
                        'return_pct': return_pct,
                        'shares': pos['shares'],
                        'days_held': pos['days_held'],
                        'highest_price': pos['highest_price'],
                        'peak_gain': ((pos['highest_price'] - pos['entry_price']) / pos['entry_price']) * 100,
                        'reputation_category': reputation['category'],
                        'reputation_score': reputation['score'],
                        'stop_loss_multiplier': reputation['stop_loss_multiplier'],
                        'position_multiplier': reputation['position_multiplier']
                    })
                    
                    positions_to_close.append(pos)
            
            for pos in positions_to_close:
                open_positions[ticker].remove(pos)
            
            if not open_positions[ticker]:
                del open_positions[ticker]
    
    # Close remaining positions
    print(f"\n{'='*120}")
    print("CLOSING REMAINING OPEN POSITIONS")
    print(f"{'='*120}\n")
    
    for ticker, positions in open_positions.items():
        if ticker not in price_cache:
            continue
        
        history = price_cache[ticker]
        end_date_ts = pd.Timestamp(end_date)
        available_dates = sorted([d for d in history.index if d <= end_date_ts])
        
        if not available_dates:
            continue
        
        final_date = available_dates[-1]
        final_price = history.loc[final_date, 'Close']
        
        for pos in positions:
            reputation = reputation_tracker.get_reputation(ticker)
            
            return_pct = ((final_price - pos['entry_price']) / pos['entry_price']) * 100
            profit_loss = pos['amount_invested'] * (return_pct / 100)
            returned_amount = pos['amount_invested'] + profit_loss
            
            closed_trades.append({
                'ticker': ticker,
                'company': pos['company'],
                'trade_date': pos['trade_date'],
                'entry_date': pos['entry_date'],
                'entry_price': pos['entry_price'],
                'exit_date': final_date.strftime('%Y-%m-%d'),
                'exit_price': final_price,
                'exit_reason': 'end_of_period',
                'amount_invested': pos['amount_invested'],
                'returned_amount': returned_amount,
                'profit_loss': profit_loss,
                'return_pct': return_pct,
                'shares': pos['shares'],
                'days_held': pos['days_held'],
                'highest_price': pos['highest_price'],
                'peak_gain': ((pos['highest_price'] - pos['entry_price']) / pos['entry_price']) * 100,
                'reputation_category': reputation['category'],
                'reputation_score': reputation['score'],
                'stop_loss_multiplier': reputation['stop_loss_multiplier'],
                'position_multiplier': reputation['position_multiplier']
            })
    
    # Calculate results
    if not closed_trades:
        print("❌ No trades were executed!")
        return []
    
    df = pd.DataFrame(closed_trades)
    
    total_invested = df['amount_invested'].sum()
    total_returned = df['returned_amount'].sum()
    total_profit = df['profit_loss'].sum()
    roi = (total_profit / total_invested) * 100
    
    winning_trades = df[df['return_pct'] > 0]
    losing_trades = df[df['return_pct'] <= 0]
    
    win_rate = len(winning_trades) / len(df) * 100
    avg_return = df['return_pct'].mean()
    median_return = df['return_pct'].median()
    avg_days_held = df['days_held'].mean()
    avg_peak_gain = df['peak_gain'].mean()
    
    print(f"\n{'='*120}")
    print("FINAL RESULTS - REPUTATION-BASED STRATEGY")
    print(f"{'='*120}")
    print(f"Total Trades: {len(df)}")
    print(f"  Winning: {len(winning_trades)} ({win_rate:.1f}%)")
    print(f"  Losing: {len(losing_trades)} ({100-win_rate:.1f}%)")
    print(f"\nAverage Return per Trade: {avg_return:+.2f}%")
    print(f"Median Return per Trade: {median_return:+.2f}%")
    print(f"Average Peak Gain: {avg_peak_gain:+.2f}%")
    print(f"Average Days Held: {avg_days_held:.0f} days")
    print(f"\n💰 PORTFOLIO PERFORMANCE:")
    print(f"   Total Invested: ${total_invested:,.2f}")
    print(f"   Total Returned: ${total_returned:,.2f}")
    print(f"   Net Profit/Loss: ${total_profit:,.2f}")
    print(f"   ROI: {roi:+.2f}%")
    
    # Exit reason breakdown
    print(f"\n📊 EXIT REASONS:")
    for reason in df['exit_reason'].unique():
        count = len(df[df['exit_reason'] == reason])
        avg_return = df[df['exit_reason'] == reason]['return_pct'].mean()
        print(f"   {reason}: {count} trades (avg return: {avg_return:+.2f}%)")
    
    # Reputation category breakdown
    print(f"\n🏆 PERFORMANCE BY REPUTATION:")
    for category in ['excellent', 'good', 'neutral', 'poor', 'unknown']:
        cat_trades = df[df['reputation_category'] == category]
        if len(cat_trades) > 0:
            cat_roi = cat_trades['profit_loss'].sum() / cat_trades['amount_invested'].sum() * 100
            cat_win_rate = len(cat_trades[cat_trades['return_pct'] > 0]) / len(cat_trades) * 100
            print(f"   {category.upper():<12} {len(cat_trades):>4} trades | ROI: {cat_roi:>+7.2f}% | Win Rate: {cat_win_rate:>5.1f}%")
    
    best_trade = df.loc[df['return_pct'].idxmax()]
    print(f"\n🏆 Best Trade: {best_trade['ticker']} [{best_trade['reputation_category']}] - {best_trade['return_pct']:+.1f}%")
    print(f"   ${best_trade['entry_price']:.2f} → ${best_trade['exit_price']:.2f} ({int(best_trade['days_held'])} days)")
    
    worst_trade = df.loc[df['return_pct'].idxmin()]
    print(f"\n💀 Worst Trade: {worst_trade['ticker']} [{worst_trade['reputation_category']}] - {worst_trade['return_pct']:+.1f}%")
    print(f"   ${worst_trade['entry_price']:.2f} → ${worst_trade['exit_price']:.2f} ({int(worst_trade['days_held'])} days)")
    
    print(f"\n{'='*120}\n")
    
    output_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_reputation_results.csv'
    df.to_csv(output_path, index=False)
    print(f"✅ Results saved to: {output_path}")
    
    # Also save reputation data
    rep_data = []
    for ticker in reputation_tracker.ticker_scores.keys():
        rep = reputation_tracker.get_reputation(ticker)
        rep_data.append({
            'ticker': ticker,
            'category': rep['category'],
            'score': rep['score'],
            'avg_score': rep['avg_score'],
            'total_purchases': rep['total_purchases'],
            'avg_gain': rep['avg_gain'],
            'stop_loss_multiplier': rep['stop_loss_multiplier'],
            'position_multiplier': rep['position_multiplier']
        })
    
    rep_df = pd.DataFrame(rep_data)
    rep_output = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/ticker_reputation_scores.csv'
    rep_df.to_csv(rep_output, index=False)
    print(f"✅ Reputation scores saved to: {rep_output}\n")
    
    return closed_trades

if __name__ == '__main__':
    backtest_with_reputation()
