#!/usr/bin/env python3
"""
Test the IPO conviction bot on BSAI to verify logic before full run
"""

import json
import pandas as pd
from datetime import datetime, timedelta
import sys

# Add parent directory to path
sys.path.append('/Users/sagiv.oron/Documents/scripts_playground/stocks/scripts/backtests')

# Import the detector classes
from backtest_ipo_conviction_bot import (
    load_cache_data, 
    RiseFallDetector, 
    parse_value, 
    is_c_level,
    get_ipo_date,
    calculate_all_time_low_pct,
    should_sell_on_bleedout,
    is_acceptable_correction
)

def test_bsai():
    """Test BSAI specifically"""
    
    print("="*80)
    print("TESTING BSAI - IPO CONVICTION BOT")
    print("="*80)
    print()
    
    # Load data
    print("📊 Loading data...")
    with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/expanded_insider_trades.json', 'r') as f:
        data = json.load(f)
    
    price_cache = load_cache_data()
    
    # Find BSAI
    bsai_trades = None
    for stock in data['data']:
        if stock['ticker'] == 'BSAI':
            bsai_trades = stock['trades']
            break
    
    if not bsai_trades:
        print("❌ BSAI not found in data")
        return
    
    print(f"✅ Found BSAI with {len(bsai_trades)} trades\n")
    
    # Get price history
    if 'BSAI' not in price_cache:
        print("❌ BSAI price data not in cache")
        return
    
    history = price_cache['BSAI']
    
    print(f"📈 BSAI price history: {len(history)} days")
    print(f"   First date: {history.index[0].date()}")
    print(f"   Last date: {history.index[-1].date()}")
    print(f"   IPO price: ${history['Close'].iloc[0]:.2f}")
    print()
    
    # Look for the specific trade mentioned
    print("🔍 Looking for insider purchase around May 2025...")
    for trade in bsai_trades:
        trade_date = trade.get('trade_date', '')
        filing_date = trade.get('filing_date', '')
        insider = trade.get('insider_name', '')
        title = trade.get('title', '')
        value = parse_value(trade.get('value', '0'))
        
        if '2025-05' in trade_date or '2025-05' in filing_date:
            print(f"   Found: {insider} ({title})")
            print(f"   Trade date: {trade_date}")
            print(f"   Filing date: {filing_date}")
            print(f"   Value: ${value:,.0f}")
            print()
            
            # Check if this meets our criteria
            if value < 20000:
                print(f"   ⚠️  Value ${value:,.0f} < $20K - SKIPPED")
                continue
            
            # Get IPO date
            ipo_date = get_ipo_date(history)
            print(f"   IPO Date: {ipo_date.date()}")
            
            # Check 3 month rule
            trade_dt = pd.Timestamp(trade_date)
            three_months_after = ipo_date + timedelta(days=90)
            print(f"   3 months after IPO: {three_months_after.date()}")
            
            if trade_dt < three_months_after:
                print(f"   ⚠️  Trade is within 3 months of IPO - SKIPPED")
                continue
            
            # Get price at trade date
            if trade_dt not in history.index:
                nearest = history.index[history.index >= trade_dt]
                if len(nearest) == 0:
                    print("   ❌ No price data after trade date")
                    continue
                trade_dt = nearest[0]
            
            trade_price = history.loc[trade_dt, 'Close']
            print(f"   Price at trade: ${trade_price:.2f}")
            
            # Calculate all-time low %
            history_up_to_trade = history[history.index <= trade_dt]
            pct_from_low = calculate_all_time_low_pct(trade_price, history_up_to_trade)
            print(f"   % from all-time low: {pct_from_low:.2f}%")
            
            if abs(pct_from_low) < 5:
                print(f"   ✅ HIGH CONVICTION - Near all-time low!")
            else:
                print(f"   ⚠️  Not at all-time low - SKIPPED")
                continue
            
            # Check C-level
            is_c = is_c_level(title)
            position = 4000 if is_c else 2000
            print(f"   C-Level: {is_c}")
            print(f"   Position size: ${position}")
            print()
            
            # Detect rise/fall events
            print("📊 Detecting rise/fall events...")
            history_from_trade = history[history.index >= trade_dt]
            
            detector = RiseFallDetector(history_from_trade)
            events = detector.detect_events(min_days=2)
            
            print(f"   Found {len(events)} events\n")
            
            # Show first 10 events
            print("   First 10 events:")
            for i, event in enumerate(events[:10]):
                print(f"   {i+1}. {event['type']:>4} {event['start_date'].date()} to {event['end_date'].date()} "
                      f"({event['days']} days) {event['change_pct']:+.1f}%")
            
            print()
            
            # Check first event
            if events[0]['type'] == 'DOWN':
                print("   ⚠️  First event is DOWN - waiting for rise...")
                next_rise = detector.get_next_event(trade_dt, event_type='RISE')
                if next_rise:
                    entry_date = next_rise['start_date']
                    entry_price = next_rise['start_price']
                    print(f"   ✅ Entry on rise: {entry_date.date()} at ${entry_price:.2f}")
                else:
                    print("   ❌ No rise event found")
                    continue
            else:
                entry_date = events[0]['start_date']
                entry_price = events[0]['start_price']
                print(f"   ✅ Entry immediately: {entry_date.date()} at ${entry_price:.2f}")
            
            print()
            
            # Track through events
            print("📈 Tracking position...")
            shares = position / entry_price
            
            events_from_entry = [e for e in events if e['start_date'] >= entry_date]
            
            had_massive_rise = False
            last_rise = None
            
            for i, event in enumerate(events_from_entry[:15]):  # Show first 15
                marker = ""
                
                if event['type'] == 'RISE':
                    last_rise = event
                    if event['change_pct'] > 500:
                        had_massive_rise = True
                        marker = " 🚀 MASSIVE RISE!"
                
                elif event['type'] == 'DOWN':
                    # Check if acceptable correction
                    if last_rise and is_acceptable_correction(event, last_rise):
                        marker = " ✓ Acceptable correction"
                    else:
                        # Check bleedout
                        prev_events = events_from_entry[:i]
                        if should_sell_on_bleedout(event, prev_events):
                            marker = " 💀 BLEEDOUT - SELL!"
                
                current_price = event['end_price']
                current_value = shares * current_price
                current_pnl = current_value - position
                current_pnl_pct = (current_pnl / position) * 100
                
                print(f"   {i+1:2}. {event['type']:>4} {event['start_date'].date()} to {event['end_date'].date()} "
                      f"({event['days']:2} days) {event['change_pct']:+7.1f}% | "
                      f"P&L: {current_pnl_pct:+7.1f}%{marker}")
                
                if '💀' in marker:
                    print(f"\n   🎯 EXIT TRIGGERED!")
                    print(f"   Exit date: {event['end_date'].date()}")
                    print(f"   Exit price: ${event['end_price']:.2f}")
                    print(f"   Final P&L: {current_pnl_pct:+.1f}%")
                    break
            
            print()
            print("="*80)

if __name__ == '__main__':
    test_bsai()
