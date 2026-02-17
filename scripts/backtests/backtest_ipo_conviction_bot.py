#!/usr/bin/env python3
"""
IPO CONVICTION BUY-SELL BOT STRATEGY
=====================================
A sophisticated strategy based on insider purchases at all-time lows with 
rise/fall event tracking for optimal entry and exit timing.

ENTRY RULES:
1. Wait 3 months after IPO before considering trades
2. Only insider purchases >= $20K
3. Stock at all-time low when insider buys = HIGH CONVICTION
   - Regular insider: $2,000 position
   - C-level exec: $4,000 position
4. Don't buy during fall events - wait for rise to start

EXIT RULES:
1. After massive rise (e.g., 600%+), hold through next drop
2. Track days + sharpness of rises (% gain and duration)
3. Allow corrections proportional to rise duration (2 days drop per 5-6 days rise OK)
4. When trend dies down (slower rise %), watch next down trajectory
5. If next down looks like bleedout (long duration + large %), SELL

RISE/FALL DETECTION:
- Track consecutive up/down days
- Calculate % change and duration
- Identify trend reversals
- Compare current trend to previous trends

Based on BSAI example: Insider buy at -99.95% all-time low, 
wait for rise, hold through corrections, sell on bleedout.
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import yfinance as yf

# ===== LOAD CACHE DATA =====

def load_cache_data():
    """Load cached yfinance data from JSON file"""
    cache_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/yfinance_cache_full.json'
    
    print(f"📦 Loading cached data from {cache_file.split('/')[-1]}...")
    
    with open(cache_file, 'r') as f:
        cache = json.load(f)
    
    print(f"   ✅ Loaded cache with {len(cache['data'])} stocks")
    print(f"   📅 Cache created: {cache['metadata']['created']}")
    
    # Convert cache data to pandas DataFrames
    price_cache = {}
    
    for ticker, ticker_data in cache['data'].items():
        df = pd.DataFrame({
            'Open': ticker_data['open'],
            'High': ticker_data['high'],
            'Low': ticker_data['low'],
            'Close': ticker_data['close'],
            'Volume': ticker_data['volume']
        }, index=pd.to_datetime(ticker_data['dates']))
        
        price_cache[ticker] = df
    
    return price_cache

# ===== RISE/FALL EVENT DETECTOR =====

class RiseFallDetector:
    """Detect and track rise/fall events in stock price movements"""
    
    def __init__(self, history):
        """
        Initialize with price history
        
        Args:
            history: pandas DataFrame with OHLCV data
        """
        self.history = history.copy()
        self.events = []
        
    def detect_events(self, min_days=2):
        """
        Detect consecutive rise and fall events
        
        Args:
            min_days: Minimum consecutive days to count as an event
            
        Returns:
            List of events with: type, start_date, end_date, days, change_pct
        """
        if len(self.history) < min_days:
            return []
        
        events = []
        current_trend = None
        trend_start = None
        trend_start_price = None
        
        for i in range(1, len(self.history)):
            prev_close = self.history['Close'].iloc[i-1]
            curr_close = self.history['Close'].iloc[i]
            curr_date = self.history.index[i]
            
            # Determine if this is a rise or fall day
            if curr_close > prev_close:
                new_trend = 'RISE'
            else:
                new_trend = 'DOWN'
            
            # If trend changes, save previous event
            if current_trend is not None and new_trend != current_trend:
                if trend_start is not None:
                    trend_end = self.history.index[i-1]
                    trend_end_price = self.history['Close'].iloc[i-1]
                    days = (trend_end - trend_start).days
                    
                    if days >= min_days:
                        change_pct = ((trend_end_price - trend_start_price) / trend_start_price) * 100
                        
                        events.append({
                            'type': current_trend,
                            'start_date': trend_start,
                            'end_date': trend_end,
                            'days': days,
                            'change_pct': change_pct,
                            'start_price': trend_start_price,
                            'end_price': trend_end_price
                        })
                
                # Start new trend
                current_trend = new_trend
                trend_start = curr_date
                trend_start_price = curr_close
            elif current_trend is None:
                # Initialize first trend
                current_trend = new_trend
                trend_start = self.history.index[i-1]
                trend_start_price = prev_close
        
        # Save final event
        if current_trend is not None and trend_start is not None:
            trend_end = self.history.index[-1]
            trend_end_price = self.history['Close'].iloc[-1]
            days = (trend_end - trend_start).days
            
            if days >= min_days:
                change_pct = ((trend_end_price - trend_start_price) / trend_start_price) * 100
                
                events.append({
                    'type': current_trend,
                    'start_date': trend_start,
                    'end_date': trend_end,
                    'days': days,
                    'change_pct': change_pct,
                    'start_price': trend_start_price,
                    'end_price': trend_end_price
                })
        
        self.events = events
        return events
    
    def get_event_at_date(self, target_date):
        """
        Get the event occurring at a specific date
        
        Args:
            target_date: Date to check (pd.Timestamp or string)
            
        Returns:
            Event dict or None
        """
        target = pd.Timestamp(target_date)
        
        for event in self.events:
            if event['start_date'] <= target <= event['end_date']:
                return event
        
        return None
    
    def get_next_event(self, target_date, event_type=None):
        """
        Get the next event after a specific date
        
        Args:
            target_date: Starting date
            event_type: Optional filter for 'RISE' or 'DOWN'
            
        Returns:
            Event dict or None
        """
        target = pd.Timestamp(target_date)
        
        for event in self.events:
            if event['start_date'] > target:
                if event_type is None or event['type'] == event_type:
                    return event
        
        return None
    
    def get_events_after_date(self, target_date, max_events=10):
        """Get list of events after a date"""
        target = pd.Timestamp(target_date)
        return [e for e in self.events if e['start_date'] > target][:max_events]

# ===== HELPER FUNCTIONS =====

def parse_value(value_str):
    """Parse value string like '+$8,783,283' to float"""
    if not value_str:
        return 0
    cleaned = value_str.replace('+', '').replace('$', '').replace(',', '')
    try:
        return float(cleaned)
    except:
        return 0

def is_c_level(title):
    """Check if insider is C-level executive"""
    if not title:
        return False
    
    title_upper = title.upper()
    c_level_keywords = ['CEO', 'CFO', 'COO', 'CTO', 'CMO', 'CHIEF']
    
    return any(keyword in title_upper for keyword in c_level_keywords)

def get_ipo_date(history):
    """Get IPO date (first trading date) from history"""
    if history.empty:
        return None
    return history.index[0]

def calculate_all_time_low_pct(current_price, history_up_to_date):
    """
    Calculate how far current price is from all-time low
    
    Args:
        current_price: Current price
        history_up_to_date: Price history up to current date
        
    Returns:
        Percentage from all-time low (negative value)
    """
    if history_up_to_date.empty:
        return 0
    
    all_time_low = history_up_to_date['Low'].min()
    
    if all_time_low == 0:
        return 0
    
    pct_from_low = ((current_price - all_time_low) / all_time_low) * 100
    
    return pct_from_low

def should_sell_on_bleedout(current_event, previous_events):
    """
    Determine if current down event is a bleedout worthy of selling
    
    A bleedout is characterized by:
    1. Long duration (>40 days)
    2. Large percentage loss (>60%)
    3. Following a pattern of rising slower (dying trend)
    
    Args:
        current_event: Current DOWN event
        previous_events: List of recent events before current
        
    Returns:
        Boolean
    """
    if current_event['type'] != 'DOWN':
        return False
    
    # Check if this is a significant drop
    if current_event['days'] > 40 and abs(current_event['change_pct']) > 60:
        # Check if previous rise events show dying trend
        recent_rises = [e for e in previous_events[-5:] if e['type'] == 'RISE']
        
        if len(recent_rises) >= 2:
            # Check if rises are getting slower
            last_rise = recent_rises[-1]
            prev_rise = recent_rises[-2]
            
            # If last rise was slower (lower % gain per day)
            last_rate = last_rise['change_pct'] / last_rise['days']
            prev_rate = prev_rise['change_pct'] / prev_rise['days']
            
            if last_rate < prev_rate * 0.7:  # 30% slower
                return True
    
    return False

def is_acceptable_correction(down_event, prior_rise_event):
    """
    Check if a down event is an acceptable correction after a rise
    
    Acceptable if:
    - Down days <= 40% of rise days (e.g., 2 days down after 5 days up)
    - Down % <= 50% of rise %
    
    Args:
        down_event: DOWN event
        prior_rise_event: Previous RISE event
        
    Returns:
        Boolean
    """
    if down_event is None or prior_rise_event is None:
        return False
    
    days_ratio = down_event['days'] / prior_rise_event['days']
    pct_ratio = abs(down_event['change_pct']) / prior_rise_event['change_pct']
    
    return days_ratio <= 0.4 and pct_ratio <= 0.5

# ===== MAIN BACKTEST =====

def backtest_ipo_conviction_bot():
    """Run the IPO conviction buy-sell bot backtest"""
    
    print("="*80)
    print("IPO CONVICTION BUY-SELL BOT STRATEGY")
    print("="*80)
    print()
    
    # Load data
    print("📊 Loading insider trades data...")
    with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/expanded_insider_trades.json', 'r') as f:
        data = json.load(f)
    
    # Load cached price data
    price_cache = load_cache_data()
    print(f"   ✅ Loaded {len(price_cache)} stocks with price data\n")
    
    # Build all trades list
    all_trades = []
    for stock in data['data']:
        ticker = stock['ticker']
        for trade in stock['trades']:
            all_trades.append({
                'ticker': ticker,
                'insider_name': trade.get('insider_name', 'Unknown'),
                'title': trade.get('title', ''),
                'trade_date': trade.get('trade_date', trade.get('transaction_date', '')),
                'filing_date': trade.get('filing_date', ''),
                'transaction_value': parse_value(trade.get('value', '0'))
            })
    
    # Filter: Only purchases >= $20K
    significant_trades = [t for t in all_trades if t['transaction_value'] >= 20000]
    
    print(f"📈 Total insider trades: {len(all_trades):,}")
    print(f"💰 Trades >= $20K: {len(significant_trades):,}")
    print()
    
    # Backtest each trade
    closed_trades = []
    open_positions = []
    
    total_trades = len(significant_trades)
    processed = 0
    
    print(f"🔄 Backtesting {total_trades:,} significant trades...\n")
    
    for trade in significant_trades:
        processed += 1
        
        if processed % 100 == 0:
            print(f"Progress: {processed}/{total_trades}")
        
        ticker = trade['ticker']
        
        # Check if we have price data
        if ticker not in price_cache:
            continue
        
        history = price_cache[ticker]
        
        if history.empty:
            continue
        
        # Get IPO date
        ipo_date = get_ipo_date(history)
        if ipo_date is None:
            continue
        
        # Parse trade date
        try:
            trade_date = pd.Timestamp(trade['trade_date'])
        except:
            continue
        
        # RULE 1: Wait 3 months after IPO
        three_months_after_ipo = ipo_date + timedelta(days=90)
        if trade_date < three_months_after_ipo:
            continue
        
        # Get price at trade date
        if trade_date not in history.index:
            # Find nearest date
            nearest_dates = history.index[history.index >= trade_date]
            if len(nearest_dates) == 0:
                continue
            trade_date = nearest_dates[0]
        
        trade_price = history.loc[trade_date, 'Close']
        
        # Check if at all-time low
        history_up_to_trade = history[history.index <= trade_date]
        pct_from_low = calculate_all_time_low_pct(trade_price, history_up_to_trade)
        
        # HIGH CONVICTION: Within 5% of all-time low
        is_high_conviction = abs(pct_from_low) < 5
        
        if not is_high_conviction:
            continue
        
        # Determine position size
        is_c_exec = is_c_level(trade['title'])
        position_size = 4000 if is_c_exec else 2000
        
        # Detect rise/fall events
        history_from_trade = history[history.index >= trade_date]
        if len(history_from_trade) < 10:
            continue
        
        detector = RiseFallDetector(history_from_trade)
        events = detector.detect_events(min_days=2)
        
        if len(events) == 0:
            continue
        
        # RULE 4: Don't buy during fall - wait for rise
        first_event = events[0]
        
        if first_event['type'] == 'DOWN':
            # Wait for next rise
            next_rise = detector.get_next_event(trade_date, event_type='RISE')
            if next_rise is None:
                continue
            
            entry_date = next_rise['start_date']
            entry_price = next_rise['start_price']
        else:
            # First event is a rise, enter immediately
            entry_date = first_event['start_date']
            entry_price = first_event['start_price']
        
        # Now track through events for exit
        shares = position_size / entry_price
        
        # Track state
        had_massive_rise = False
        last_rise_event = None
        
        exit_date = None
        exit_price = None
        exit_reason = None
        
        events_from_entry = [e for e in events if e['start_date'] >= entry_date]
        
        for i, event in enumerate(events_from_entry):
            # Track rises
            if event['type'] == 'RISE':
                last_rise_event = event
                
                # Check if this is a massive rise (>500%)
                if event['change_pct'] > 500:
                    had_massive_rise = True
            
            # Check downs
            elif event['type'] == 'DOWN':
                # If we just had a massive rise, hold through next drop
                if had_massive_rise and i > 0 and events_from_entry[i-1]['type'] == 'RISE':
                    if events_from_entry[i-1]['change_pct'] > 500:
                        # Hold through this drop
                        had_massive_rise = False  # Reset flag
                        continue
                
                # Check if this is an acceptable correction
                if last_rise_event is not None:
                    if is_acceptable_correction(event, last_rise_event):
                        continue
                
                # Check if this is a bleedout
                prev_events = events_from_entry[:i]
                if should_sell_on_bleedout(event, prev_events):
                    exit_date = event['end_date']
                    exit_price = event['end_price']
                    exit_reason = 'bleedout_sell'
                    break
        
        # If no exit triggered, hold until end of data
        if exit_date is None:
            exit_date = history_from_trade.index[-1]
            exit_price = history_from_trade['Close'].iloc[-1]
            exit_reason = 'end_of_data'
        
        # Calculate returns
        returned_amount = shares * exit_price
        profit_loss = returned_amount - position_size
        return_pct = (profit_loss / position_size) * 100
        days_held = (exit_date - entry_date).days
        
        # Track peak gain
        history_holding_period = history[(history.index >= entry_date) & (history.index <= exit_date)]
        if not history_holding_period.empty:
            peak_price = history_holding_period['High'].max()
            peak_gain = ((peak_price - entry_price) / entry_price) * 100
        else:
            peak_gain = 0
        
        closed_trades.append({
            'ticker': ticker,
            'insider_name': trade['insider_name'],
            'title': trade['title'],
            'is_c_level': is_c_exec,
            'insider_purchase_date': trade['trade_date'],
            'insider_purchase_value': trade['transaction_value'],
            'pct_from_all_time_low': pct_from_low,
            'entry_date': entry_date.strftime('%Y-%m-%d'),
            'entry_price': entry_price,
            'exit_date': exit_date.strftime('%Y-%m-%d'),
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'position_size': position_size,
            'shares': shares,
            'returned_amount': returned_amount,
            'profit_loss': profit_loss,
            'return_pct': return_pct,
            'days_held': days_held,
            'peak_gain': peak_gain
        })
    
    print(f"\n✅ Backtest complete: {len(closed_trades)} trades executed\n")
    
    # Generate results
    if len(closed_trades) == 0:
        print("⚠️  No trades met the criteria\n")
        return []
    
    df = pd.DataFrame(closed_trades)
    
    # Calculate statistics
    total_invested = df['position_size'].sum()
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
    
    print(f"{'='*80}")
    print("FINAL RESULTS - IPO CONVICTION BOT")
    print(f"{'='*80}")
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
        avg_ret = df[df['exit_reason'] == reason]['return_pct'].mean()
        print(f"   {reason}: {count} trades (avg return: {avg_ret:+.2f}%)")
    
    # C-level vs regular
    print(f"\n👔 PERFORMANCE BY INSIDER TYPE:")
    for is_c in [True, False]:
        insider_type = 'C-Level' if is_c else 'Regular'
        subset = df[df['is_c_level'] == is_c]
        if len(subset) > 0:
            subset_roi = subset['profit_loss'].sum() / subset['position_size'].sum() * 100
            subset_win = len(subset[subset['return_pct'] > 0]) / len(subset) * 100
            print(f"   {insider_type:<10} {len(subset):>4} trades | ROI: {subset_roi:>+7.2f}% | Win Rate: {subset_win:>5.1f}%")
    
    # Top 10 performers
    print(f"\n🏆 TOP 10 PERFORMERS:")
    top_10 = df.nlargest(10, 'return_pct')
    for idx, trade in top_10.iterrows():
        print(f"   {trade['ticker']:>6} | {trade['return_pct']:>+8.1f}% | ${trade['entry_price']:.2f} → ${trade['exit_price']:.2f} | {int(trade['days_held'])} days")
    
    # Worst 10
    print(f"\n💀 WORST 10 PERFORMERS:")
    worst_10 = df.nsmallest(10, 'return_pct')
    for idx, trade in worst_10.iterrows():
        print(f"   {trade['ticker']:>6} | {trade['return_pct']:>+8.1f}% | ${trade['entry_price']:.2f} → ${trade['exit_price']:.2f} | {int(trade['days_held'])} days")
    
    print(f"\n{'='*80}\n")
    
    # Save results
    output_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_ipo_conviction_bot_results.csv'
    df.to_csv(output_path, index=False)
    print(f"✅ Results saved to: {output_path}")
    
    # ALSO save to latest file for UI display
    latest_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_latest_results.csv'
    df.to_csv(latest_path, index=False)
    print(f"✅ UI file updated: {latest_path}\n")
    
    return closed_trades

if __name__ == '__main__':
    backtest_ipo_conviction_bot()
