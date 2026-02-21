#!/usr/bin/env python3
"""
ATR-Based Insider Conviction Strategy
Uses dynamic stop losses based on ATR and historical volatility patterns.

Three-Phase Sell Strategy:
- Phase A (Days 1-5): 1.5 × 14-day ATR (blind protection)
- Phase B (After first mid-rise): 1.2 × Average Historical Mid-Fall from similar rises
- Phase C (Cumulative rise > 30%): Chandelier Exit using deepest mid-fall from top 25% rises

USAGE:
  # Run on single stock:
  .venv/bin/python scripts/backtests/backtest_atr_strategy.py --ticker BLNE
  
  # Run on all stocks:
  .venv/bin/python scripts/backtests/backtest_atr_strategy.py
"""

import pandas as pd
from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional, Tuple
from enum import Enum
import argparse
import sys
import os


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


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR) for the given price data."""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr


def load_historical_volatility(ticker: str) -> Optional[Dict]:
    """Load historical rise/fall patterns from JSON file."""
    json_file = f'output CSVs/{ticker.lower()}_rise_volatility_analysis.json'
    
    if not os.path.exists(json_file):
        return None
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        return data
    except:
        return None


def get_average_mid_fall_for_rise_group(volatility_data: Dict, target_rise_pct: float, 
                                        margin_pct: float = 20.0, 
                                        is_insider_trade: bool = False,
                                        tier_multiplier: float = 1.2) -> Tuple[float, bool]:
    """
    Find rises within margin_pct of target_rise_pct and calculate average mid-fall.
    SIGNAL-SENSITIVE: Prioritizes insider-backed historical rises for insider trades.
    
    Args:
        volatility_data: Historical volatility analysis
        target_rise_pct: The rise percentage to match
        margin_pct: Percentage margin for matching (default 20%)
        is_insider_trade: If True, prioritize insider-backed historical rises
        tier_multiplier: Multiplier to apply if using general history for insider trade
    
    Returns:
        Tuple of (average_mid_fall_pct, used_insider_history)
    """
    if not volatility_data:
        return 5.0, False  # Default fallback
    
    rise_events = volatility_data.get('rise_events', {})
    
    lower_bound = target_rise_pct * (1 - margin_pct / 100)
    upper_bound = target_rise_pct * (1 + margin_pct / 100)
    
    # Separate insider-backed and general rises
    insider_falls = []
    general_falls = []
    
    for rise_pct_key, event_data in rise_events.items():
        rise_pct = event_data.get('rise_percentage', 0)
        
        if lower_bound <= rise_pct <= upper_bound:
            mid_falls = event_data.get('mid_falls', {})
            has_insiders = len(event_data.get('insiders', [])) > 0
            
            for fall_pct_key in mid_falls.keys():
                try:
                    fall_pct = abs(float(fall_pct_key))
                    if has_insiders:
                        insider_falls.append(fall_pct)
                    else:
                        general_falls.append(fall_pct)
                except:
                    continue
    
    # Signal-Sensitive Phase B Logic
    if is_insider_trade and insider_falls:
        # Priority: Use actual insider-backed historical rises
        avg_fall = sum(insider_falls) / len(insider_falls)
        return avg_fall, True  # Used insider history
    elif is_insider_trade and general_falls:
        # Fallback: Inflate general history with tier multiplier
        avg_fall = (sum(general_falls) / len(general_falls)) * tier_multiplier
        return avg_fall, False  # Used inflated general history
    elif general_falls:
        # Non-insider trade: use general history
        avg_fall = sum(general_falls) / len(general_falls)
        return avg_fall, False
    else:
        return 5.0, False  # Default fallback


def detect_conviction_level(insiders_list: List[Dict]) -> Dict:
    """
    Detect conviction level based on insider characteristics.
    
    Returns:
        Dict with:
        - tier: 'OMEGA', 'CONVICTION', or 'SPRINT'
        - phase_a_atr_mult: ATR multiplier for Phase A (shock absorber)
        - phase_b_mult: Multiplier for Phase B floor calculation
        - confirmation_days: Days to wait for uptrend confirmation
        - chase_cap: Max % above insider price allowed
        - signal_validity_days: Trading days before signal expires
    """
    if not insiders_list:
        return {
            'tier': 'SPRINT',
            'phase_a_atr_mult': 1.5,
            'phase_b_mult': 1.2,
            'confirmation_days': 3,
            'chase_cap': 0.10,
            'signal_validity_days': 10
        }
    
    # Calculate total investment
    total_investment = sum(abs(insider.get('value', 0)) for insider in insiders_list)
    
    # Check for executive titles (CFO, CEO)
    executive_titles = ['cfo', 'chief financial', 'ceo', 'chief executive']
    
    # Check if any executive made a significant individual purchase
    max_executive_investment = 0
    for insider in insiders_list:
        title = insider.get('title', '').lower()
        value = abs(insider.get('value', 0))
        
        # DEBUG
        is_exec = any(exec_title in title for exec_title in executive_titles)
        if is_exec and value > 20000:
            print(f"    [CONVICTION DEBUG] {insider.get('insider_name', 'Unknown')}: {title} - ${value:,.0f}")
        
        if is_exec:
            max_executive_investment = max(max_executive_investment, value)
    
    # TIER 1: OMEGA - CFO/CEO individual buy >$25k
    if max_executive_investment >= 25000:
        return {
            'tier': 'OMEGA',
            'phase_a_atr_mult': 3.0,  # Wide shock absorber
            'phase_b_mult': 4.0,      # Expect structural volatility
            'confirmation_days': 0,    # Flash entry - buy next open
            'chase_cap': 0.25,         # Allow 25% chase
            'signal_validity_days': 10 # Signal expires after 10 trading days
        }
    
    # TIER 2: CONVICTION - Multiple insiders OR moderate ITI ($10k+)
    elif len(insiders_list) >= 2 or total_investment >= 10000:
        return {
            'tier': 'CONVICTION',
            'phase_a_atr_mult': 2.0,
            'phase_b_mult': 2.5,
            'confirmation_days': 1,    # Fast entry - 1-day confirm
            'chase_cap': 0.15,
            'signal_validity_days': 15 # Longer validity for group conviction
        }
    
    # TIER 3: SPRINT - Low conviction, quick opportunities
    else:
        return {
            'tier': 'SPRINT',
            'phase_a_atr_mult': 1.5,
            'phase_b_mult': 1.2,
            'confirmation_days': 3,    # Safe entry - 3-day confirm
            'chase_cap': 0.10,
            'signal_validity_days': 20 # More patient for low conviction
        }


def check_entry_gate(current_price: float, insider_avg_price: float, chase_cap: float) -> Tuple[bool, str]:
    """
    Check if current price is within acceptable chase range of insider purchase price.
    
    Args:
        current_price: Current stock price
        insider_avg_price: Average price insiders paid
        chase_cap: Maximum allowed chase percentage (e.g., 0.25 for 25%)
    
    Returns:
        Tuple of (is_valid, message)
    """
    if insider_avg_price <= 0:
        return True, "No insider price reference"
    
    chase_pct = (current_price - insider_avg_price) / insider_avg_price
    
    if chase_pct > chase_cap:
        return False, f"❌ Chase Cap Exceeded: {chase_pct:.1%} (max {chase_cap:.0%})"
    
    return True, f"✓ Chase OK: {chase_pct:+.1%}"


def get_omega_multiplier(volatility_data: Dict) -> float:
    """
    Calculate Omega multiplier based on deepest mid-falls in top 25% of rises.
    
    Returns the average of the deepest mid-fall from each of the top 25% rises.
    """
    if not volatility_data:
        return 6.87  # BLNE default from example
    
    rise_events = volatility_data.get('rise_events', {})
    
    # Sort rises by percentage (descending)
    sorted_rises = sorted(
        [(float(k), v) for k, v in rise_events.items()],
        key=lambda x: x[0],
        reverse=True
    )
    
    # Get top 25%
    top_25_pct_count = max(1, len(sorted_rises) // 4)
    top_rises = sorted_rises[:top_25_pct_count]
    
    deepest_falls = []
    
    for rise_pct, event_data in top_rises:
        mid_falls = event_data.get('mid_falls', {})
        if mid_falls:
            # Find deepest fall for this rise
            deepest = max([abs(float(k)) for k in mid_falls.keys()])
            deepest_falls.append(deepest)
    
    if not deepest_falls:
        return 6.87  # Default fallback
    
    return sum(deepest_falls) / len(deepest_falls)


class TradingState:
    """Track the current state of our live trading simulation with ATR-based stops."""
    
    def __init__(self, ticker: str, volatility_data: Optional[Dict] = None):
        self.ticker = ticker
        self.volatility_data = volatility_data
        
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
        self.prev_fall_had_insiders = False
        
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
        self.peak_since_entry = 0
        self.peak_price_since_entry = 0
        
        # ATR-specific tracking
        self.atr_at_entry = None
        self.current_floor = None
        self.current_phase = None  # 'A', 'B', or 'C'
        self.cumulative_rise_pct = 0
        self.mid_rises_since_entry = []
        self.mid_falls_since_entry = []
        self.last_price = None
        self.in_mid_rise = False
        self.mid_rise_start_price = None
        self.omega_multiplier = None
        self.conviction_tier = None  # Full tier info dict
        
        # Insider purchase tracking for chase cap and signal expiry
        self.insider_purchase_prices = []
        self.most_recent_insider_date = None  # Track most recent insider purchase date
        
        # Event tracking
        self.all_events = []
    
    def update_phase(self, current_price: float, prev_price: float, date: datetime):
        """Update market phase using FIRST DIP → RECOVERY → SECOND DIP pattern."""
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
            has_insider_support = bool(self.insiders_bought_in_fall or self.insiders_bought_in_rise)
            required_up_days = 3 if has_insider_support else 2
            
            if self.consecutive_up_days >= required_up_days:
                days_since_last_peak = 999
                
                if days_since_last_peak >= 0:
                    lookback = 4 if has_insider_support else 3
                    
                    if len(self.price_history) >= lookback:
                        bottom_date, bottom_price = self.price_history[-lookback]
                        actual_start_date = bottom_date
                        actual_start_price = bottom_price
                    else:
                        actual_start_date = date
                        actual_start_price = prev_price
                    
                    # Record completed FALL event
                    if self.phase == MarketPhase.FALLING and self.trend_start_date:
                        fall_days = (actual_start_date - self.trend_start_date).days
                        fall_pct = ((self.trend_low_price - self.trend_start_price) / self.trend_start_price) * 100
                        
                        if not self.in_position:
                            self.prev_fall_pct = abs(fall_pct)
                            self.prev_fall_start_price = self.trend_start_price
                        
                        fall_start_naive = self.trend_start_date.tz_localize(None) if hasattr(self.trend_start_date, 'tz_localize') else self.trend_start_date
                        fall_end_naive = actual_start_date.tz_localize(None) if hasattr(actual_start_date, 'tz_localize') else actual_start_date
                        
                        fall_insiders = [
                            i for i in self.insiders_bought_in_fall 
                            if fall_start_naive <= pd.to_datetime(i['date']).tz_localize(None) <= fall_end_naive
                        ]
                        
                        self.prev_fall_had_insiders = len(fall_insiders) > 0
                        
                        self.all_events.append({
                            'event_type': 'DOWN',
                            'start_date': self.trend_start_date,
                            'end_date': actual_start_date,
                            'days': fall_days,
                            'change_pct': fall_pct,
                            'start_price': self.trend_start_price,
                            'end_price': self.trend_low_price,
                            'insiders': fall_insiders
                        })
                    
                    # Start rise
                    self.phase = MarketPhase.RISING
                    self.trend_start_date = actual_start_date
                    self.trend_start_price = actual_start_price
                    self.trend_peak_price = current_price
                    self.trend_peak_date = date
                    self.first_dip_date = None
                    self.first_dip_price = None
                    self.in_recovery = False
                    
                    self.insiders_bought_in_rise = []
        
        elif self.phase == MarketPhase.RISING:
            if current_price > self.trend_peak_price:
                self.trend_peak_price = current_price
                self.trend_peak_date = date
                self.first_dip_date = None
                self.first_dip_price = None
                self.dip_low_price = None
                self.in_recovery = False
            
            # FALL DETECTION
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
                        
                        # Record completed RISE event
                        rise_days = (actual_rise_end - self.trend_start_date).days
                        rise_pct = ((self.trend_peak_price - self.trend_start_price) / self.trend_start_price) * 100
                        
                        rise_start_naive = self.trend_start_date.tz_localize(None) if hasattr(self.trend_start_date, 'tz_localize') else self.trend_start_date
                        rise_end_naive = actual_rise_end.tz_localize(None) if hasattr(actual_rise_end, 'tz_localize') else actual_rise_end
                        peak_naive = self.trend_peak_date.tz_localize(None) if hasattr(self.trend_peak_date, 'tz_localize') else self.trend_peak_date
                        
                        rise_insiders = [
                            i for i in self.insiders_bought_in_rise
                            if pd.to_datetime(i['date']).tz_localize(None) <= peak_naive
                        ]
                        
                        insiders_after_peak = [
                            i for i in self.insiders_bought_in_rise
                            if pd.to_datetime(i['date']).tz_localize(None) > peak_naive
                        ]
                        
                        if insiders_after_peak:
                            self.insiders_bought_in_fall.extend(insiders_after_peak)
                        
                        self.all_events.append({
                            'event_type': 'RISE',
                            'start_date': self.trend_start_date,
                            'end_date': actual_rise_end,
                            'days': rise_days,
                            'change_pct': rise_pct,
                            'start_price': self.trend_start_price,
                            'end_price': None,
                            'peak_price': self.trend_peak_price,
                            'insiders': rise_insiders
                        })
                        
                        self.insiders_bought_in_rise = []
                        
                        self.trend_start_date = self.trend_peak_date
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
        
        if self.phase == MarketPhase.FALLING and self.trend_start_price and not self.in_position:
            self.prev_fall_pct = ((self.trend_start_price - current_price) / self.trend_start_price) * 100
    
    def record_insider_purchase(self, date_str: str, trade_info: Dict):
        """Record an insider purchase occurring today."""
        trade_data = {
            'date': date_str,
            'price': trade_info['price'],
            'insider_name': trade_info['insider_name'],
            'value': trade_info['value'],
            'title': trade_info.get('title', ''),  # CRITICAL: Need title for conviction detection
            'stock_price': trade_info.get('stock_price', trade_info['price'])
        }
        
        # Track insider purchase price for chase cap
        stock_price = trade_data['stock_price']
        if stock_price > 0:
            self.insider_purchase_prices.append(stock_price)
        
        # Track most recent insider date for signal expiry
        from pandas import to_datetime
        insider_date = to_datetime(date_str)
        if self.most_recent_insider_date is None or insider_date > self.most_recent_insider_date:
            self.most_recent_insider_date = insider_date
        
        if self.phase == MarketPhase.FALLING:
            self.insiders_bought_in_fall.append(trade_data)
        elif self.phase == MarketPhase.RISING:
            self.insiders_bought_in_rise.append(trade_data)
        
        if self.shopping_spree_peak_price is None or trade_data['stock_price'] > self.shopping_spree_peak_price:
            self.shopping_spree_peak_price = trade_data['stock_price']
    
    def check_buy_signal(self, current_date: datetime, current_price: float, atr: float) -> Optional[Dict]:
        """Check if we should buy based on current state with tiered conviction logic."""
        if self.in_position:
            return None
        
        if self.phase != MarketPhase.RISING:
            return None
        
        if not self.insiders_bought_in_fall:
            return None
        
        # Detect conviction tier for all insider purchases
        all_insider_purchases = self.insiders_bought_in_fall + self.insiders_bought_in_rise
        tier_info = detect_conviction_level(all_insider_purchases)
        
        # SIGNAL EXPIRY CHECK: Reject stale signals
        if self.most_recent_insider_date is not None:
            import numpy as np
            # Calculate TRADING DAYS between most recent insider buy and now
            days_since_signal = np.busday_count(
                self.most_recent_insider_date.date(),
                current_date.date()
            )
            
            signal_validity = tier_info['signal_validity_days']
            
            if days_since_signal > signal_validity:
                # Signal is stale - log rejection and return
                print(f"    ⏰ Signal Expired: {days_since_signal} trading days old (max {signal_validity} for {tier_info['tier']})")
                print(f"    Last insider buy: {self.most_recent_insider_date.strftime('%Y-%m-%d')}, Current: {current_date.strftime('%Y-%m-%d')}")
                return None
        
        # Dynamic confirmation days based on tier
        required_days = tier_info['confirmation_days']
        if self.insiders_bought_in_rise and self.insiders_bought_in_fall:
            # Shopping spree needs at least the tier's confirmation
            required_days = max(required_days, tier_info['confirmation_days'])
        
        if self.consecutive_up_days < required_days:
            return None
        
        # CHASE CAP GATE: Calculate average insider purchase price
        if self.insider_purchase_prices:
            avg_insider_price = sum(self.insider_purchase_prices) / len(self.insider_purchase_prices)
            is_valid, gate_msg = check_entry_gate(current_price, avg_insider_price, tier_info['chase_cap'])
            
            if not is_valid:
                # Log the rejection (visible in debug mode)
                print(f"    {gate_msg} | Insider avg: ${avg_insider_price:.2f}, Current: ${current_price:.2f}")
                return None
        
        total_investment = sum(abs(t['value']) for t in self.insiders_bought_in_fall)
        
        # SCENARIO 1: Shopping Spree
        if self.insiders_bought_in_rise and self.insiders_bought_in_fall and self.shopping_spree_peak_price:
            target = self.shopping_spree_peak_price
            
            if target > current_price:
                all_insider_purchases = self.insiders_bought_in_rise + self.insiders_bought_in_fall
                
                # Already have tier_info from earlier
                
                self.in_position = True
                self.entry_date = current_date
                self.entry_price = current_price
                self.target_price = target
                self.buy_type = 'shopping_spree'
                self.peak_since_entry = 0
                self.peak_price_since_entry = current_price
                self.atr_at_entry = atr
                self.current_phase = 'A'
                # SHOCK ABSORBER: Use tier-specific ATR multiplier
                self.current_floor = current_price - (tier_info['phase_a_atr_mult'] * atr)
                self.cumulative_rise_pct = 0
                self.mid_rises_since_entry = []
                self.mid_falls_since_entry = []
                self.last_price = current_price
                self.conviction_tier = tier_info  # Store full tier info
                
                self.insiders_bought_in_rise = []
                self.insiders_bought_in_fall = []
                self.shopping_spree_peak_price = None
                self.insider_purchase_prices = []  # Reset for next trade
                self.most_recent_insider_date = None  # Reset signal date
                
                return {
                    'buy_date': current_date,
                    'entry_price': current_price,
                    'target_price': target,
                    'buy_type': 'shopping_spree',
                    'num_insiders': len(all_insider_purchases),
                    'prev_fall_pct': self.prev_fall_pct,
                    'atr_at_entry': atr,
                    'initial_floor': self.current_floor,
                    'conviction_level': tier_info['tier'],
                    'phase_a_mult': tier_info['phase_a_atr_mult'],
                    'phase_b_mult': tier_info['phase_b_mult']
                }
        
        # SCENARIO 2: Absorption Buy
        elif self.insiders_bought_in_fall and not self.insiders_bought_in_rise:
            if total_investment >= 5000:
                target_gain_pct = abs(self.prev_fall_pct)
                
                # Already have tier_info from earlier
                
                self.in_position = True
                self.entry_date = current_date
                self.entry_price = current_price
                self.target_price = current_price * (1 + target_gain_pct / 100)
                self.buy_type = 'absorption_buy'
                self.peak_since_entry = 0
                self.peak_price_since_entry = current_price
                self.atr_at_entry = atr
                self.current_phase = 'A'
                # SHOCK ABSORBER: Use tier-specific ATR multiplier
                self.current_floor = current_price - (tier_info['phase_a_atr_mult'] * atr)
                self.cumulative_rise_pct = 0
                self.mid_rises_since_entry = []
                self.mid_falls_since_entry = []
                self.last_price = current_price
                self.conviction_tier = tier_info  # Store full tier info
                
                self.insiders_bought_in_rise = []
                self.insiders_bought_in_fall = []
                self.shopping_spree_peak_price = None
                self.insider_purchase_prices = []  # Reset for next trade
                self.most_recent_insider_date = None  # Reset signal date
                
                return {
                    'buy_date': current_date,
                    'entry_price': current_price,
                    'target_price': self.target_price,
                    'buy_type': 'absorption_buy',
                    'num_insiders': len(self.insiders_bought_in_fall),
                    'fall_pct': self.prev_fall_pct,
                    'total_investment': total_investment,
                    'atr_at_entry': atr,
                    'initial_floor': self.current_floor,
                    'conviction_level': tier_info['tier'],
                    'phase_a_mult': tier_info['phase_a_atr_mult'],
                    'phase_b_mult': tier_info['phase_b_mult']
                }
        
        return None
    
    def update_atr_floor(self, current_date: datetime, current_price: float):
        """Update the ATR-based floor based on current phase and price action."""
        if not self.in_position:
            return
        
        # Count TRADING DAYS only (exclude weekends/holidays)
        import numpy as np
        days_held = np.busday_count(self.entry_date.date(), current_date.date())
        
        # Update peak
        if current_price > self.peak_price_since_entry:
            self.peak_price_since_entry = current_price
        
        # Calculate cumulative rise
        self.cumulative_rise_pct = ((self.peak_price_since_entry - self.entry_price) / self.entry_price) * 100
        
        # Track mid-rises and mid-falls
        if self.last_price is not None:
            daily_change_pct = ((current_price - self.last_price) / self.last_price) * 100
            
            # Track mid-rises
            if daily_change_pct > 0:
                if not self.in_mid_rise:
                    self.in_mid_rise = True
                    self.mid_rise_start_price = self.last_price
            elif daily_change_pct < -1.0 and self.in_mid_rise:
                # Mid-rise ended
                mid_rise_pct = ((self.last_price - self.mid_rise_start_price) / self.mid_rise_start_price) * 100
                if mid_rise_pct >= 1.0:
                    self.mid_rises_since_entry.append(mid_rise_pct)
                self.in_mid_rise = False
                self.mid_rise_start_price = None
            
            # Track mid-falls
            if daily_change_pct <= -1.0:
                self.mid_falls_since_entry.append(abs(daily_change_pct))
        
        self.last_price = current_price
        
        # PHASE A: Days 1-5 - Shock Absorber with tier-specific ATR multiplier
        if days_held <= 5:
            self.current_phase = 'A'
            # Use tier-specific shock absorber
            phase_a_mult = self.conviction_tier['phase_a_atr_mult'] if self.conviction_tier else 1.5
            new_floor = self.peak_price_since_entry - (phase_a_mult * self.atr_at_entry)
            self.current_floor = max(self.current_floor, new_floor)
        
        # PHASE B: After first mid-rise - Signal-Sensitive Pattern Matching
        elif len(self.mid_rises_since_entry) >= 1 and self.cumulative_rise_pct < 30:
            self.current_phase = 'B'
            
            # Get tier info
            is_insider_trade = self.conviction_tier is not None
            tier_mult = self.conviction_tier['phase_b_mult'] if self.conviction_tier else 1.2
            
            # SIGNAL-SENSITIVE: Prioritize insider-backed historical rises
            avg_historical_fall, used_insider_history = get_average_mid_fall_for_rise_group(
                self.volatility_data,
                self.cumulative_rise_pct,
                margin_pct=20.0,
                is_insider_trade=is_insider_trade,
                tier_multiplier=tier_mult
            )
            
            # If we used insider history, apply standard buffer (1.2x)
            # If we used inflated general history, it's already multiplied
            multiplier = 1.2 if used_insider_history else 1.0
            buffer_pct = multiplier * avg_historical_fall
            new_floor = self.peak_price_since_entry * (1 - buffer_pct / 100)
            
            # DEBUG: Show Phase B floor calculation for critical trades
            if hasattr(current_date, 'year') and current_date.year == 2025 and current_date.month in [11, 12]:
                if self.ticker == 'BLNE' and days_held >= 5:
                    history_type = "Insider" if used_insider_history else "General"
                    tier_name = self.conviction_tier['tier'] if self.conviction_tier else "N/A"
                    print(f"  [Phase B {current_date.strftime('%Y-%m-%d')}] Peak=${self.peak_price_since_entry:.2f}, {history_type} Fall={avg_historical_fall:.1f}%, Mult={multiplier:.1f}×, Buffer={buffer_pct:.1f}%, Floor=${new_floor:.2f} | Tier:{tier_name}")
            
            self.current_floor = max(self.current_floor, new_floor)
        
        # PHASE C: Cumulative rise > 30% - Omega Phase (Chandelier Exit)
        elif self.cumulative_rise_pct >= 30:
            self.current_phase = 'C'
            
            # Calculate Omega multiplier if not already done
            if self.omega_multiplier is None:
                self.omega_multiplier = get_omega_multiplier(self.volatility_data)
            
            # Use 4x the average mid-fall as the volatility buffer
            volatility_buffer_pct = 4.0 * self.omega_multiplier
            
            # Ratchet floor stays exactly volatility_buffer_pct below peak
            new_floor = self.peak_price_since_entry * (1 - volatility_buffer_pct / 100)
            self.current_floor = max(self.current_floor, new_floor)
    
    def check_sell_signal(self, current_date: datetime, current_price: float) -> Optional[Tuple[str, float]]:
        """Check if we should sell based on ATR floor."""
        if not self.in_position:
            return None
        
        # Update the floor first
        self.update_atr_floor(current_date, current_price)
        
        # Calculate current performance
        current_gain_pct = ((current_price - self.entry_price) / self.entry_price) * 100
        self.peak_since_entry = max(self.peak_since_entry, current_gain_pct)
        
        # Count TRADING DAYS only (exclude weekends/holidays)
        import numpy as np
        days_held = np.busday_count(self.entry_date.date(), current_date.date())
        
        # AGGRESSIVE EARLY EXITS (Kill losers fast)
        if days_held >= 30 and current_gain_pct <= -20:
            self.in_position = False
            return ('early_stop_loss', current_price)
        
        if days_held >= 60 and current_gain_pct < 5:
            self.in_position = False
            return ('60day_underperformer', current_price)
        
        if days_held >= 90 and current_gain_pct < 10:
            self.in_position = False
            return ('90day_zombie', current_price)
        
        # ATR FLOOR EXIT
        if current_price <= self.current_floor:
            self.in_position = False
            reason = f'atr_floor_phase_{self.current_phase}'
            return (reason, current_price)
        
        return None


def process_single_stock(ticker: str, stock_data: Dict, price_cache: Dict, 
                        generate_detailed_files: bool = False) -> Optional[Dict]:
    """
    Run the ATR-based insider conviction strategy on a single stock.
    
    Args:
        ticker: Stock ticker symbol
        stock_data: Insider trades data for this stock
        price_cache: Pre-loaded price data from cache
        generate_detailed_files: If True, return events for file generation
    """
    try:
        # Check if we have price data in cache
        if ticker not in price_cache:
            return None
        
        price_df = price_cache[ticker]
        
        if price_df.empty or len(price_df) < 30:
            return None
        
        # Calculate ATR
        atr_series = calculate_atr(price_df, period=14)
        
        # Load historical volatility data
        volatility_data = load_historical_volatility(ticker)
        
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
        state = TradingState(ticker, volatility_data)
        completed_trades = []
        
        debug_mode = (ticker == "BLNE")
        
        if debug_mode:
            print(f"\n🔬 ATR STRATEGY DEBUG for {ticker}:")
            print(f"   Price data: {len(price_df)} days")
            print(f"   Insider trades: {len(insider_trades)} dates")
            if volatility_data:
                print(f"   Historical volatility data loaded: {volatility_data.get('total_rise_events', 0)} rise events")
            else:
                print(f"   ⚠️  No historical volatility data found")
            print()
        
        for i in range(1, len(price_df)):
            current_date = price_df.index[i]
            current_price = price_df['Close'].iloc[i]
            prev_price = price_df['Close'].iloc[i-1]
            date_str = current_date.strftime('%Y-%m-%d')
            current_atr = atr_series.iloc[i]
            
            state.update_phase(current_price, prev_price, current_date)
            
            if date_str in insider_trades:
                for trade_info in insider_trades[date_str]:
                    trade_info_with_price = trade_info.copy()
                    trade_info_with_price['stock_price'] = current_price
                    state.record_insider_purchase(date_str, trade_info_with_price)
            
            if state.in_position:
                sell_signal = state.check_sell_signal(current_date, current_price)
                if sell_signal:
                    reason, exit_price = sell_signal
                    days_held = (current_date - state.entry_date).days
                    return_pct = ((exit_price - state.entry_price) / state.entry_price) * 100
                    profit = state.position_size * (return_pct / 100)
                    
                    if debug_mode:
                        print(f"   💰 SELL: {date_str} @ ${exit_price:.2f}")
                        print(f"   Phase: {state.current_phase}, Floor: ${state.current_floor:.2f}")
                        print(f"   Return: {return_pct:+.2f}% ({days_held} days)")
                        print(f"   Reason: {reason}")
                        print(f"   Mid-rises: {len(state.mid_rises_since_entry)}, Mid-falls: {len(state.mid_falls_since_entry)}")
                        print()
                    
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
                        'peak_gain': round(state.peak_since_entry, 2),
                        'buy_type': state.buy_type,
                        'atr_at_entry': round(state.atr_at_entry, 2),
                        'exit_phase': state.current_phase,
                        'cumulative_rise': round(state.cumulative_rise_pct, 2),
                        'mid_rises_count': len(state.mid_rises_since_entry),
                        'mid_falls_count': len(state.mid_falls_since_entry)
                    }
                    
                    completed_trades.append(trade)
                    
                    state.insiders_bought_in_fall = []
                    state.insiders_bought_in_rise = []
                    state.shopping_spree_peak_price = None
            else:
                if not pd.isna(current_atr):
                    buy_signal = state.check_buy_signal(current_date, current_price, current_atr)
                    if buy_signal and debug_mode:
                        print(f"   🎯 BUY: {date_str} @ ${current_price:.2f}")
                        print(f"   Type: {buy_signal['buy_type']}")
                        print(f"   Target: ${buy_signal['target_price']:.2f}")
                        print(f"   ATR: ${buy_signal['atr_at_entry']:.2f}")
                        print(f"   Initial Floor: ${buy_signal['initial_floor']:.2f}")
                        print(f"   🔥 Conviction: {buy_signal.get('conviction_level', 'UNKNOWN')} | Phase A: {buy_signal.get('phase_a_mult', 0):.1f}× ATR | Phase B: {buy_signal.get('phase_b_mult', 0):.1f}×")
                        print()
        
        # Handle open position at end
        if state.in_position:
            if debug_mode:
                print(f"   ⚠️  Position still open at end!")
                print(f"   Entry: {state.entry_date.strftime('%Y-%m-%d')} @ ${state.entry_price:.2f}")
                print(f"   Final: {price_df.index[-1].strftime('%Y-%m-%d')} @ ${price_df['Close'].iloc[-1]:.2f}")
                print(f"   Phase: {state.current_phase}, Floor: ${state.current_floor:.2f}")
                print()
            
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
                'peak_gain': round(state.peak_since_entry, 2),
                'buy_type': state.buy_type,
                'atr_at_entry': round(state.atr_at_entry, 2),
                'exit_phase': state.current_phase,
                'cumulative_rise': round(state.cumulative_rise_pct, 2),
                'mid_rises_count': len(state.mid_rises_since_entry),
                'mid_falls_count': len(state.mid_falls_since_entry)
            }
            
            completed_trades.append(trade)
        
        if not completed_trades:
            return None
        
        # Calculate summary statistics
        total_trades = len(completed_trades)
        winning_trades = [t for t in completed_trades if t['return_pct'] > 0]
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        total_profit = sum(t['profit_loss'] for t in completed_trades)
        total_invested = sum(t['position_size'] for t in completed_trades)
        roi = (total_profit / total_invested * 100) if total_invested > 0 else 0
        
        avg_return = sum(t['return_pct'] for t in completed_trades) / total_trades
        median_return = sorted([t['return_pct'] for t in completed_trades])[len(completed_trades) // 2]
        max_return = max(t['return_pct'] for t in completed_trades)
        min_return = min(t['return_pct'] for t in completed_trades)
        
        avg_days = sum(t['days_held'] for t in completed_trades) / total_trades
        
        result = {
            'ticker': ticker,
            'company_name': stock_data.get('company_name', ticker),
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': total_trades - len(winning_trades),
            'win_rate': round(win_rate, 1),
            'total_profit': round(total_profit, 2),
            'total_invested': total_invested,
            'roi': round(roi, 2),
            'avg_return': round(avg_return, 2),
            'median_return': round(median_return, 2),
            'max_return': round(max_return, 2),
            'min_return': round(min_return, 2),
            'avg_days_held': round(avg_days, 1),
            'trades': completed_trades
        }
        
        if generate_detailed_files:
            # Convert Timestamps to strings for JSON serialization
            events_serializable = []
            for event in state.all_events:
                event_copy = event.copy()
                if 'start_date' in event_copy and hasattr(event_copy['start_date'], 'strftime'):
                    event_copy['start_date'] = event_copy['start_date'].strftime('%Y-%m-%d')
                if 'end_date' in event_copy and hasattr(event_copy['end_date'], 'strftime'):
                    event_copy['end_date'] = event_copy['end_date'].strftime('%Y-%m-%d')
                events_serializable.append(event_copy)
            
            result['events'] = events_serializable
            result['price_df'] = price_df
        
        return result
        
    except Exception as e:
        print(f"❌ Error processing {ticker}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run the ATR-based strategy."""
    parser = argparse.ArgumentParser(description='Run ATR-Based Insider Conviction Strategy')
    parser.add_argument('--ticker', type=str, help='Run backtest for a single ticker')
    parser.add_argument('--limit', type=int, help='Limit number of stocks to test (for testing)')
    args = parser.parse_args()
    
    single_ticker = args.ticker.upper() if args.ticker else None
    stock_limit = args.limit if args.limit else None
    
    print("=" * 80)
    if single_ticker:
        print(f"🔬 ATR STRATEGY - SINGLE STOCK TEST: {single_ticker}")
    elif stock_limit:
        print(f"ATR-BASED INSIDER CONVICTION STRATEGY - LIMITED TO {stock_limit} STOCKS")
    else:
        print("ATR-BASED INSIDER CONVICTION STRATEGY - ALL STOCKS")
    print("=" * 80)
    print()
    
    # Load cached price data
    price_cache = load_cache_data()
    print()
    
    # Load insider trades database
    print("Loading insider trades database...")
    with open('output CSVs/expanded_insider_trades_filtered.json', 'r') as f:
        data = json.load(f)
    
    all_stocks = data.get('data', [])
    
    if not single_ticker:
        all_stocks = all_stocks[:500]
        print(f"⚡ FAST TEST MODE: Processing first 500 stocks only")
    
    print(f"✓ Loaded {len(all_stocks)} stocks from database")
    print()
    
    # SINGLE TICKER MODE
    if single_ticker:
        stock_data = None
        for s in all_stocks:
            if s.get('ticker', '') == single_ticker:
                stock_data = s
                break
        
        if not stock_data:
            # Try full dataset
            all_stocks_full = data.get('data', [])
            for s in all_stocks_full:
                if s.get('ticker', '') == single_ticker:
                    stock_data = s
                    break
        
        if not stock_data:
            print(f"❌ Ticker {single_ticker} not found in database")
            sys.exit(1)
        
        if single_ticker not in price_cache:
            print(f"❌ No price data found for {single_ticker}")
            sys.exit(1)
        
        print(f"🔍 Testing {single_ticker} with ATR strategy...")
        result = process_single_stock(single_ticker, stock_data, price_cache, generate_detailed_files=True)
        
        if not result:
            print(f"⚠️  {single_ticker}: No trades generated")
            sys.exit(0)
        
        print(f"✅ {single_ticker}: {result['total_trades']} trades, {result['roi']:+.2f}% ROI")
        print()
        
        # Generate detailed files if we have events
        if 'events' in result and result['events']:
            print("📝 Generating detailed files...")
            # Note: We're not generating the CSV/XLSX files for ATR strategy
            # (those are specific to the rise/fall detection pattern)
            # The volatility JSON already exists from the original script
            print("   ℹ️  Using existing volatility analysis from original script")
            print()
        
        # Remove events and price_df from result before saving to JSON
        result.pop('events', None)
        result.pop('price_df', None)
        
        # Save to ATR-specific results file
        output_file = 'output CSVs/atr_strategy_results.json'
        
        # SINGLE TICKER MODE: Replace ALL previous data with just this ticker
        # This is the only stock being tested, so it should be the only one in the results
        print(f"🧹 Single-ticker mode: Replacing all previous data with {single_ticker} results")
        
        existing_data = {
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'strategy': 'ATR-Based Insider Conviction',
            'overall_stats': {
                'stocks_analyzed': 1,
                'total_trades': result['total_trades'],
                'winning_trades': result['winning_trades'],
                'overall_win_rate': result['win_rate'],
                'total_profit': result['total_profit'],
                'total_invested': result['total_invested'],
                'overall_roi': result['roi']
            },
            # In single-ticker mode, this ticker is both best and worst (it's the only one)
            'top_25_best': [result] if result['roi'] >= 0 else [],
            'top_25_worst': [result] if result['roi'] < 0 else [],
            'all_results': [result]
        }
        
        # Save updated results
        with open(output_file, 'w') as f:
            json.dump(existing_data, f, indent=2)
        
        print(f"💾 Updated {output_file}")
        print()
        print(f"📊 {single_ticker} TRADE DETAILS:")
        for trade in result['trades']:
            print(f"   Entry: {trade['entry_date']} @ ${trade['entry_price']}")
            print(f"   Exit:  {trade['exit_date']} @ ${trade['exit_price']}")
            print(f"   Return: {trade['return_pct']:+.2f}% ({trade['days_held']} days)")
            print(f"   Phase at exit: {trade['exit_phase']}")
            print(f"   Reason: {trade['sell_reason']}")
            print(f"   Cumulative rise: {trade['cumulative_rise']:.2f}%")
            print()
        
        print("=" * 80)
        print()
        print("🔄 Restart webapp to see changes:")
        print("   ./restart_webapp_stocks.sh")
        return
    
    # FULL RUN MODE
    stocks_to_process = all_stocks[:stock_limit] if stock_limit else all_stocks
    print(f"Processing {len(stocks_to_process)} stocks...")
    results = []
    
    for i, stock_data in enumerate(stocks_to_process):
        ticker = stock_data.get('ticker', '')
        if not ticker:
            continue
        
        print(f"{i}/{len(stocks_to_process)}", flush=True)
        
        result = process_single_stock(ticker, stock_data, price_cache)
        
        if result:
            results.append(result)
    
    print(f"\n✓ Completed processing {len(stocks_to_process)} stocks")
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
    
    print(f"OVERALL STATISTICS (ATR Strategy)")
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
    
    top_25_best = results_sorted[:25]
    top_25_worst = results_sorted[-25:]
    
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
    
    # Save results
    output = {
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'strategy': 'ATR-Based Insider Conviction',
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
        'all_results': results_sorted
    }
    
    output_file = 'output CSVs/atr_strategy_results.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✓ Results saved to: {output_file}")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
