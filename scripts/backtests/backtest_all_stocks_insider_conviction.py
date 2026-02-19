#!/usr/bin/env python3
"""
Run Insider Conviction Strategy on ALL stocks in the database.
This script generates a summary of best/worst performers for the webapp.

For detailed analysis (CSV/XLSX/JSON files), use the on-demand script:
  generate_stock_detailed_analysis.py

Output: JSON file with top 25 best/worst performers + overall ROI

NOTE: Uses cached yfinance data for speed (10-15 seconds vs hours)
"""

import pandas as pd
from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional, Tuple
from enum import Enum


class MarketPhase(Enum):
    """Current market phase we're observing."""
    RISING = "rising"
    FALLING = "falling"
    UNKNOWN = "unknown"


def load_cache_data():
    """Load cached yfinance data from JSON file"""
    cache_file = 'output CSVs/yfinance_cache_full.json'
    
    print("📦 Loading cached price data...")
    
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


class MarketPhase(Enum):
    """Current market phase we're observing."""
    RISING = "rising"
    FALLING = "falling"
    UNKNOWN = "unknown"


class TradingState:
    """Track the current state of our live trading simulation."""
    
    def __init__(self):
        # Market observation
        self.phase = MarketPhase.UNKNOWN
        self.last_peak_date = None
        
        # Price history for rise start detection
        self.price_history = []
        
        # Dip-recovery-dip tracking for fall detection
        self.first_dip_date = None
        self.first_dip_price = None
        self.dip_low_price = None
        self.in_recovery = False
        self.recovery_high = None
        self.consecutive_up_days = 0
        
        # Current trend tracking
        self.trend_start_date = None
        self.trend_start_price = None
        self.trend_peak_price = None
        self.trend_peak_date = None
        self.trend_low_price = float('inf')
        self.trend_low_date = None
        
        # Previous trend memory
        self.prev_fall_pct = 0
        self.prev_rise_pct = 0
        self.prev_rise_start_price = None
        self.prev_rise_peak_price = None
        self.prev_fall_start_price = None
        
        # Insider activity tracking
        self.insiders_bought_in_rise = []
        self.insiders_bought_in_fall = []
        self.shopping_spree_peak_price = None
        
        # Position tracking
        self.in_position = False
        self.entry_date = None
        self.entry_price = None
        self.target_price = None
        self.buy_type = None
        self.position_size = 2000
        self.max_mid_fall_before_target = 0
        self.target_reached = False
        self.peak_since_entry = 0
        
        # Absorption buy specific tracking
        self.rise_start_price = None
        self.in_mid_rise = False
    
    def update_phase(self, current_price: float, prev_price: float, date: datetime):
        """Update market phase using FIRST DIP → RECOVERY → SECOND DIP pattern for fall detection."""
        # Track price history
        self.price_history.append((date, current_price))
        if len(self.price_history) > 4:
            self.price_history.pop(0)
        
        # Treat ±$0.01 as plateau
        price_diff = abs(current_price - prev_price)
        is_plateau = price_diff <= 0.01
        is_up = current_price > prev_price and not is_plateau
        is_down = current_price < prev_price and not is_plateau
        
        # Track consecutive up days
        if is_up:
            self.consecutive_up_days += 1
        else:
            self.consecutive_up_days = 0
        
        if self.phase == MarketPhase.UNKNOWN or self.phase == MarketPhase.FALLING:
            # HUNTING FOR RISE START: Need 2 consecutive up days (or 3 for hot stocks)
            is_hot_stock = bool(self.insiders_bought_in_rise and self.insiders_bought_in_fall)
            required_up_days = 3 if is_hot_stock else 2
            
            if self.consecutive_up_days >= required_up_days:
                days_since_last_peak = 999  # Temporarily disable 15-day gap
                
                if days_since_last_peak >= 0:
                    # Clear old insider data if no recent activity (30+ days)
                    if not self.in_position:
                        days_since_last_purchase = 999
                        for purchase_list in [self.insiders_bought_in_rise, self.insiders_bought_in_fall]:
                            for purchase in purchase_list:
                                purchase_date = pd.to_datetime(purchase['date']).tz_localize(None)
                                current_date_naive = date.tz_localize(None) if hasattr(date, 'tz_localize') else date
                                days_diff = (current_date_naive - purchase_date).days
                                days_since_last_purchase = min(days_since_last_purchase, days_diff)
                        
                        if days_since_last_purchase > 30:
                            self.insiders_bought_in_rise = []
                            self.insiders_bought_in_fall = []
                            self.shopping_spree_peak_price = None
                    
                    # Find the actual rise start
                    lookback = 4 if is_hot_stock else 3
                    
                    if len(self.price_history) >= lookback:
                        bottom_date, bottom_price = self.price_history[-lookback]
                        actual_start_date = bottom_date
                        actual_start_price = bottom_price
                    else:
                        actual_start_date = date
                        actual_start_price = prev_price
                    
                    # Record the completed FALL event if we were falling before
                    if self.phase == MarketPhase.FALLING and self.trend_start_date:
                        fall_pct = ((self.trend_low_price - self.trend_start_price) / self.trend_start_price) * 100
                        
                        if not self.in_position:
                            self.prev_fall_pct = abs(fall_pct)
                            self.prev_fall_start_price = self.trend_start_price
                    
                    # Start rise
                    self.phase = MarketPhase.RISING
                    self.trend_start_date = actual_start_date
                    self.trend_start_price = actual_start_price
                    self.trend_peak_price = current_price
                    self.trend_peak_date = date
                    self.first_dip_date = None
                    self.first_dip_price = None
                    self.in_recovery = False
        
        elif self.phase == MarketPhase.RISING:
            # Update peak if new high
            if current_price > self.trend_peak_price:
                self.trend_peak_price = current_price
                self.trend_peak_date = date
                self.first_dip_date = None
                self.first_dip_price = None
                self.dip_low_price = None
                self.in_recovery = False
            
            # FALL DETECTION: First dip → recovery → second dip
            if is_down:
                decline_from_peak = ((self.trend_peak_price - current_price) / self.trend_peak_price) * 100
                
                if self.first_dip_date is None:
                    if decline_from_peak >= 1.0:
                        self.first_dip_date = date
                        self.first_dip_price = current_price
                        self.dip_low_price = current_price
                        self.in_recovery = False
                elif not self.in_recovery:
                    if current_price < self.dip_low_price:
                        self.dip_low_price = current_price
                elif self.in_recovery:
                    decline_from_recovery = ((self.recovery_high - current_price) / self.recovery_high) * 100
                    if decline_from_recovery >= 1.0:
                        self.prev_rise_pct = ((self.trend_peak_price - self.trend_start_price) / 
                                             self.trend_start_price) * 100
                        self.prev_rise_start_price = self.trend_start_price
                        self.prev_rise_peak_price = self.trend_peak_price
                        self.last_peak_date = self.trend_peak_date
                        
                        # Transition to FALLING
                        self.phase = MarketPhase.FALLING
                        
                        from pandas.tseries.offsets import BDay
                        actual_rise_end = self.first_dip_date - BDay(1)
                        
                        self.trend_start_date = self.first_dip_date
                        self.trend_start_price = self.trend_peak_price
                        self.trend_low_price = current_price
                        self.trend_low_date = date
                        self.consecutive_up_days = 0
                        
                        self.first_dip_date = None
                        self.first_dip_price = None
                        self.dip_low_price = None
                        self.in_recovery = False
            
            elif is_up and self.in_recovery:
                self.first_dip_date = None
                self.first_dip_price = None
                self.dip_low_price = None
                self.in_recovery = False
                self.recovery_high = current_price
            
            elif (is_up or is_plateau) and self.first_dip_date is not None and not self.in_recovery:
                recovery_from_dip = ((current_price - self.dip_low_price) / self.dip_low_price) * 100
                if recovery_from_dip >= 0.0:
                    self.in_recovery = True
                    self.recovery_high = current_price
        
        # Track lowest price during fall
        if self.phase == MarketPhase.FALLING:
            if current_price < self.trend_low_price:
                self.trend_low_price = current_price
                self.trend_low_date = date
        
        # Calculate current fall percentage
        if self.phase == MarketPhase.FALLING and self.trend_start_price and not self.in_position:
            self.prev_fall_pct = ((self.trend_start_price - current_price) / self.trend_start_price) * 100
    
    def record_insider_purchase(self, date_str: str, trade_info: Dict):
        """Record an insider purchase occurring today."""
        trade_data = {
            'date': date_str,
            'price': trade_info['price'],
            'insider_name': trade_info['insider_name'],
            'value': trade_info['value'],
            'stock_price': trade_info.get('stock_price', trade_info['price'])
        }
        
        if self.phase == MarketPhase.RISING:
            self.insiders_bought_in_rise.append(trade_data)
            if self.shopping_spree_peak_price is None or trade_data['stock_price'] > self.shopping_spree_peak_price:
                self.shopping_spree_peak_price = trade_data['stock_price']
        elif self.phase == MarketPhase.FALLING:
            self.insiders_bought_in_fall.append(trade_data)
            if self.shopping_spree_peak_price is None or trade_data['stock_price'] > self.shopping_spree_peak_price:
                self.shopping_spree_peak_price = trade_data['stock_price']
    
    def check_buy_signal(self, current_date: datetime, current_price: float) -> Optional[Dict]:
        """Check if we should buy based on current state (NO HINDSIGHT)."""
        if self.in_position:
            return None
        
        if self.phase != MarketPhase.RISING:
            return None
        
        if not self.insiders_bought_in_fall:
            return None
        
        # For hot stocks, require 3 consecutive up days
        if self.insiders_bought_in_rise and self.insiders_bought_in_fall:
            if self.consecutive_up_days < 3:
                return None
        
        # SCENARIO 1: Shopping Spree
        if self.insiders_bought_in_rise and self.insiders_bought_in_fall and self.shopping_spree_peak_price:
            target = self.shopping_spree_peak_price
            
            if target > current_price:
                self.in_position = True
                self.entry_date = current_date
                self.entry_price = current_price
                self.target_price = target
                self.buy_type = 'shopping_spree'
                self.target_reached = False
                self.max_mid_fall_before_target = 0
                self.peak_since_entry = 0
                
                all_insider_purchases = self.insiders_bought_in_rise + self.insiders_bought_in_fall
                return {
                    'buy_date': current_date,
                    'entry_price': current_price,
                    'target_price': target,
                    'buy_type': 'shopping_spree',
                    'num_insiders': len(all_insider_purchases),
                    'prev_fall_pct': self.prev_fall_pct
                }
        
        # SCENARIO 2: Absorption Buy
        elif self.insiders_bought_in_fall and not self.insiders_bought_in_rise:
            total_investment = sum(abs(t['value']) for t in self.insiders_bought_in_fall)
            
            if total_investment >= 5000:
                target_gain_pct = abs(self.prev_fall_pct)
                
                self.in_position = True
                self.entry_date = current_date
                self.entry_price = current_price
                self.target_price = current_price * (1 + target_gain_pct / 100)
                self.buy_type = 'absorption_buy'
                self.target_reached = False
                self.peak_since_entry = 0
                self.rise_start_price = self.trend_start_price if self.trend_start_price else current_price
                self.in_mid_rise = False
                
                return {
                    'buy_date': current_date,
                    'entry_price': current_price,
                    'target_price': self.target_price,
                    'buy_type': 'absorption_buy',
                    'num_insiders': len(self.insiders_bought_in_fall),
                    'fall_pct': self.prev_fall_pct,
                    'total_investment': total_investment,
                    'rise_start_price': self.rise_start_price
                }
        
        # Clear insider data after checking
        self.insiders_bought_in_rise = []
        self.insiders_bought_in_fall = []
        self.shopping_spree_peak_price = None
        
        return None
    
    def check_sell_signal(self, current_date: datetime, current_price: float, 
                         prev_price: float) -> Optional[Tuple[str, float]]:
        """Check if we should sell based on current conditions (NO HINDSIGHT)."""
        if not self.in_position:
            return None
        
        # Calculate current performance
        current_gain_pct = ((current_price - self.entry_price) / self.entry_price) * 100
        self.peak_since_entry = max(self.peak_since_entry, current_gain_pct)
        
        # ABSORPTION BUY has different sell logic
        if self.buy_type == 'absorption_buy':
            cumulative_rise_pct = ((current_price - self.rise_start_price) / self.rise_start_price) * 100
            
            daily_change_pct = ((current_price - prev_price) / prev_price) * 100
            was_in_mid_rise = self.in_mid_rise
            
            if daily_change_pct > 0:
                self.in_mid_rise = True
            else:
                self.in_mid_rise = False
            
            target_gain_pct = abs(self.prev_fall_pct)
            
            if cumulative_rise_pct >= target_gain_pct:
                self.target_reached = True
                
                if not self.in_mid_rise or (was_in_mid_rise and not self.in_mid_rise):
                    self.in_position = False
                    return ('absorption_target_reached', current_price)
            
            return None
        
        # SHOPPING SPREE sell logic
        if current_gain_pct <= -15:
            self.in_position = False
            return ('stop_loss', current_price)
        
        if not self.target_reached and current_price >= self.target_price:
            self.target_reached = True
        
        daily_change_pct = ((current_price - prev_price) / prev_price) * 100
        if not self.target_reached and daily_change_pct < -1.0:
            self.max_mid_fall_before_target = max(self.max_mid_fall_before_target, 
                                                   abs(daily_change_pct))
        
        if self.target_reached:
            if daily_change_pct < -1.0:
                self.in_position = False
                return ('target_reached_first_dip', current_price)
        
        # Stagnation check
        days_held = (current_date - self.entry_date).days
        if days_held > 60 and not self.target_reached and current_gain_pct < 5:
            self.in_position = False
            return ('stagnation', current_price)
        
        return None


def process_single_stock(ticker: str, stock_data: Dict, price_cache: Dict) -> Optional[Dict]:
    """
    Run the insider conviction strategy on a single stock.
    Returns summary statistics only (no detailed files).
    
    Args:
        ticker: Stock ticker symbol
        stock_data: Insider trades data for this stock
        price_cache: Pre-loaded price data from cache
    """
    try:
        # Check if we have price data in cache
        if ticker not in price_cache:
            return None
        
        price_df = price_cache[ticker]
        
        if price_df.empty or len(price_df) < 30:
            return None
        
        # Get insider trades for this ticker
        insider_trades = {}
        for trade in stock_data.get('trades', []):
            trade_date = trade.get('trade_date', '')
            if trade_date:
                try:
                    price_str = str(trade.get('price', '0')).replace('$', '').replace(',', '')
                    price = float(price_str) if price_str else 0.0
                    
                    value_str = str(trade.get('value', '0')).replace('$', '').replace('+', '').replace(',', '')
                    value = float(value_str) if value_str else 0.0
                    
                    trade_info = {
                        'price': price,
                        'insider_name': trade.get('insider_name', ''),
                        'value': value,
                        'title': trade.get('title', '')
                    }
                    
                    if trade_date not in insider_trades:
                        insider_trades[trade_date] = []
                    insider_trades[trade_date].append(trade_info)
                except:
                    continue
        
        if not insider_trades:
            return None
        
        # Run simulation
        state = TradingState()
        completed_trades = []
        
        for i in range(1, len(price_df)):
            current_date = price_df.index[i]
            current_price = price_df['Close'].iloc[i]
            prev_price = price_df['Close'].iloc[i-1]
            date_str = current_date.strftime('%Y-%m-%d')
            
            state.update_phase(current_price, prev_price, current_date)
            
            if date_str in insider_trades:
                for trade_info in insider_trades[date_str]:
                    trade_info_with_price = trade_info.copy()
                    trade_info_with_price['stock_price'] = current_price
                    state.record_insider_purchase(date_str, trade_info_with_price)
            
            if state.in_position:
                sell_signal = state.check_sell_signal(current_date, current_price, prev_price)
                if sell_signal:
                    reason, exit_price = sell_signal
                    days_held = (current_date - state.entry_date).days
                    return_pct = ((exit_price - state.entry_price) / state.entry_price) * 100
                    profit = state.position_size * (return_pct / 100)
                    
                    trade = {
                        'entry_date': state.entry_date.strftime('%Y-%m-%d'),
                        'entry_price': round(state.entry_price, 2),
                        'exit_date': current_date.strftime('%Y-%m-%d'),
                        'exit_price': round(exit_price, 2),
                        'target_price': round(state.target_price, 2),
                        'days_held': days_held,
                        'return_pct': round(return_pct, 2),
                        'position_size': state.position_size,
                        'profit_loss': round(profit, 2),
                        'sell_reason': reason,
                        'target_reached': 'yes' if state.target_reached else 'no',
                        'peak_gain': round(state.peak_since_entry, 2),
                        'buy_type': state.buy_type
                    }
                    
                    completed_trades.append(trade)
                    
                    state.insiders_bought_in_fall = []
                    state.insiders_bought_in_rise = []
                    state.shopping_spree_peak_price = None
            else:
                buy_signal = state.check_buy_signal(current_date, current_price)
        
        # Handle open position at end
        if state.in_position:
            final_date = price_df.index[-1]
            final_price = price_df['Close'].iloc[-1]
            days_held = (final_date - state.entry_date).days
            return_pct = ((final_price - state.entry_price) / state.entry_price) * 100
            profit = state.position_size * (return_pct / 100)
            
            trade = {
                'entry_date': state.entry_date.strftime('%Y-%m-%d'),
                'entry_price': round(state.entry_price, 2),
                'exit_date': final_date.strftime('%Y-%m-%d'),
                'exit_price': round(final_price, 2),
                'target_price': round(state.target_price, 2),
                'days_held': days_held,
                'return_pct': round(return_pct, 2),
                'position_size': state.position_size,
                'profit_loss': round(profit, 2),
                'sell_reason': 'end_of_period',
                'target_reached': 'yes' if state.target_reached else 'no',
                'peak_gain': round(state.peak_since_entry, 2),
                'buy_type': state.buy_type
            }
            
            completed_trades.append(trade)
        
        if not completed_trades:
            return None
        
        # Calculate summary statistics
        total_trades = len(completed_trades)
        winning_trades = [t for t in completed_trades if t['return_pct'] > 0]
        target_reached_trades = [t for t in completed_trades if t['target_reached'] == 'yes']
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        target_rate = len(target_reached_trades) / total_trades * 100 if total_trades > 0 else 0
        
        total_profit = sum(t['profit_loss'] for t in completed_trades)
        total_invested = sum(t['position_size'] for t in completed_trades)
        roi = (total_profit / total_invested * 100) if total_invested > 0 else 0
        
        avg_return = sum(t['return_pct'] for t in completed_trades) / total_trades
        median_return = sorted([t['return_pct'] for t in completed_trades])[len(completed_trades) // 2]
        max_return = max(t['return_pct'] for t in completed_trades)
        min_return = min(t['return_pct'] for t in completed_trades)
        
        avg_days = sum(t['days_held'] for t in completed_trades) / total_trades
        
        return {
            'ticker': ticker,
            'company_name': stock_data.get('company_name', ticker),
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': total_trades - len(winning_trades),
            'win_rate': round(win_rate, 1),
            'target_rate': round(target_rate, 1),
            'total_profit': round(total_profit, 2),
            'total_invested': total_invested,
            'roi': round(roi, 2),
            'avg_return': round(avg_return, 2),
            'median_return': round(median_return, 2),
            'max_return': round(max_return, 2),
            'min_return': round(min_return, 2),
            'avg_days_held': round(avg_days, 1),
            'trades': completed_trades  # Include individual trades for charts
        }
        
    except Exception as e:
        print(f"❌ Error processing {ticker}: {str(e)}")
        return None


def main():
    """Run the strategy on all stocks and generate summary report."""
    print("=" * 80)
    print("INSIDER CONVICTION STRATEGY - ALL STOCKS ANALYSIS")
    print("=" * 80)
    print()
    
    # Load cached price data
    price_cache = load_cache_data()
    print()
    
    # Load insider trades database
    print("Loading insider trades database...")
    with open('output CSVs/expanded_insider_trades.json', 'r') as f:
        data = json.load(f)
    
    all_stocks = data.get('data', [])
    print(f"✓ Loaded {len(all_stocks)} stocks from database")
    print()
    
    # Process each stock
    total_stocks = len(all_stocks)
    print(f"Processing {total_stocks} stocks...")
    results = []
    
    for i, stock_data in enumerate(all_stocks):
        ticker = stock_data.get('ticker', '')
        if not ticker:
            continue
        
        # Show progress for EVERY stock
        print(f"{i}/{total_stocks}", flush=True)
        
        result = process_single_stock(ticker, stock_data, price_cache)
        
        if result:
            results.append(result)
    
    print(f"\n✓ Completed processing {len(all_stocks)} stocks")
    print(f"✓ Found {len(results)} stocks with trades")
    print()
    print("=" * 80)
    
    if not results:
        print("❌ No results to analyze.")
        return
    
    # Calculate overall statistics
    total_profit = sum(r['total_profit'] for r in results)
    total_invested = sum(r['total_invested'] for r in results)
    overall_roi = (total_profit / total_invested * 100) if total_invested > 0 else 0
    
    total_trades_all = sum(r['total_trades'] for r in results)
    total_winners = sum(r['winning_trades'] for r in results)
    overall_win_rate = (total_winners / total_trades_all * 100) if total_trades_all > 0 else 0
    
    print(f"OVERALL STATISTICS")
    print("-" * 80)
    print(f"Stocks Analyzed:           {len(results)}")
    print(f"Total Trades:              {total_trades_all}")
    print(f"Winning Trades:            {total_winners} ({overall_win_rate:.1f}%)")
    print(f"Total Profit:              ${total_profit:,.2f}")
    print(f"Total Invested:            ${total_invested:,.2f}")
    print(f"Overall ROI:               {overall_roi:+.2f}%")
    print()
    
    # Sort by ROI
    results_sorted = sorted(results, key=lambda x: x['roi'], reverse=True)
    
    # Get top 25 best and worst
    top_25_best = results_sorted[:25]
    top_25_worst = results_sorted[-25:]
    
    # Get tickers of top/worst performers (for filtering detailed trades)
    top_worst_tickers = set([r['ticker'] for r in top_25_best] + [r['ticker'] for r in top_25_worst])
    
    print("TOP 25 BEST PERFORMERS:")
    print("-" * 80)
    print(f"{'Rank':<5} {'Ticker':<8} {'Trades':<7} {'ROI %':<10} {'Win Rate':<10} {'Avg Return':<12}")
    print("-" * 80)
    for i, r in enumerate(top_25_best, 1):
        print(f"{i:<5} {r['ticker']:<8} {r['total_trades']:<7} {r['roi']:+9.2f}% {r['win_rate']:>8.1f}% {r['avg_return']:+11.2f}%")
    print()
    
    print("TOP 25 WORST PERFORMERS:")
    print("-" * 80)
    print(f"{'Rank':<5} {'Ticker':<8} {'Trades':<7} {'ROI %':<10} {'Win Rate':<10} {'Avg Return':<12}")
    print("-" * 80)
    for i, r in enumerate(reversed(top_25_worst), 1):
        print(f"{i:<5} {r['ticker']:<8} {r['total_trades']:<7} {r['roi']:+9.2f}% {r['win_rate']:>8.1f}% {r['avg_return']:+11.2f}%")
    print()
    
    # Remove individual trades from all_results (except top/worst performers)
    # This saves file size - we only need detailed trades for stocks shown in UI
    all_results_lite = []
    for r in results_sorted:
        result_copy = r.copy()
        if result_copy['ticker'] not in top_worst_tickers:
            # Remove trades array for stocks not in top/worst
            result_copy.pop('trades', None)
        all_results_lite.append(result_copy)
    
    # Save results to JSON
    output = {
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'strategy': 'Insider Conviction (No Hindsight)',
        'overall_stats': {
            'stocks_analyzed': len(results),
            'total_trades': total_trades_all,
            'winning_trades': total_winners,
            'overall_win_rate': round(overall_win_rate, 1),
            'total_profit': round(total_profit, 2),
            'total_invested': total_invested,
            'overall_roi': round(overall_roi, 2)
        },
        'top_25_best': top_25_best,
        'top_25_worst': list(reversed(top_25_worst)),
        'all_results': all_results_lite
    }
    
    output_file = 'output CSVs/insider_conviction_all_stocks_results.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✓ Results saved to: {output_file}")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
