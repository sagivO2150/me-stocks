#!/usr/bin/env python3
"""
Smart Multi-Factor Insider Trading Strategy
============================================
Implements intelligent filtering and position management based on:
1. Insider quality (CEO/CFO > Directors)
2. Multiple insiders buying together
3. Stock technical position (down from highs = better)
4. Scale-out exit strategy (take profits + trailing stop)
"""

import json
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
import sys


def get_business_days_later(date_str, days=2):
    """Add N business days to a date"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    business_days_added = 0
    current_date = date
    
    while business_days_added < days:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:
            business_days_added += 1
    
    return current_date.strftime('%Y-%m-%d')


def parse_value(value_str):
    """Convert '+$69,297,690' to 69297690.0"""
    if not value_str:
        return 0.0
    cleaned = value_str.replace('+', '').replace('$', '').replace(',', '').replace('-', '')
    try:
        return float(cleaned)
    except:
        return 0.0


def get_role_weight(role):
    """
    Assign weights to insider roles based on their knowledge/conviction.
    CEO/CFO know the most, 10% owners might be financial investors.
    """
    role_lower = role.lower()
    
    if any(x in role_lower for x in ['ceo', 'chief executive', 'president']):
        return 3.0
    elif any(x in role_lower for x in ['cfo', 'chief financial']):
        return 3.0
    elif any(x in role_lower for x in ['coo', 'cto', 'chief operating', 'chief technology']):
        return 2.5
    elif 'director' in role_lower or 'dir' in role_lower:
        return 1.0
    elif '10%' in role_lower:
        return 0.5  # Often passive investors
    else:
        return 1.0


def calculate_conviction_score(ticker_data, trade, all_trades_same_day):
    """
    Calculate conviction score for a trade based on multiple factors.
    Higher score = more conviction.
    """
    score = 0
    reasons = []
    
    # Factor 1: Insider role quality
    role = trade.get('role', '')
    role_weight = get_role_weight(role)
    if role_weight >= 3.0:
        score += 3
        reasons.append(f"CEO/CFO purchase (+3)")
    elif role_weight >= 2.0:
        score += 2
        reasons.append(f"C-level purchase (+2)")
    
    # Factor 2: Purchase size
    value = parse_value(trade.get('value', '0'))
    if value >= 10_000_000:
        score += 3
        reasons.append(f"Large purchase $10M+ (+3)")
    elif value >= 5_000_000:
        score += 2
        reasons.append(f"Significant purchase $5M+ (+2)")
    elif value >= 1_000_000:
        score += 1
        reasons.append(f"Material purchase $1M+ (+1)")
    
    # Factor 3: Multiple insiders same day
    if len(all_trades_same_day) >= 4:
        score += 3
        reasons.append(f"{len(all_trades_same_day)} insiders buying together (+3)")
    elif len(all_trades_same_day) >= 2:
        score += 2
        reasons.append(f"{len(all_trades_same_day)} insiders buying together (+2)")
    
    return score, reasons


def get_stock_technical_position(ticker, check_date):
    """
    Check if stock is down from 52-week high (good for buying dip).
    Returns: (distance_from_high_pct, current_price, high_52w, pass_filter)
    """
    try:
        check_dt = datetime.strptime(check_date, '%Y-%m-%d')
        lookback_start = (check_dt - timedelta(days=400)).strftime('%Y-%m-%d')
        
        stock = yf.Ticker(ticker)
        history = stock.history(start=lookback_start, end=check_date)
        
        if history.empty or len(history) < 200:
            return None, None, None, False
        
        # Get 52-week high
        high_52w = history['High'].max()
        current_price = history['Close'].iloc[-1]
        
        distance_pct = ((current_price - high_52w) / high_52w) * 100
        
        # Prefer stocks down from highs (buying the dip)
        pass_filter = distance_pct < -10  # At least 10% below 52w high
        
        return distance_pct, current_price, high_52w, pass_filter
        
    except Exception as e:
        return None, None, None, False


def check_price_spike(ticker, entry_date, transaction_date):
    """
    Check if stock spiked too much between transaction and entry date.
    If it's already up 10%+, we're chasing and should skip.
    """
    try:
        trans_dt = datetime.strptime(transaction_date, '%Y-%m-%d')
        entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
        start_date = (trans_dt - timedelta(days=5)).strftime('%Y-%m-%d')
        end_date = (entry_dt + timedelta(days=2)).strftime('%Y-%m-%d')
        
        stock = yf.Ticker(ticker)
        history = stock.history(start=start_date, end=end_date)
        
        if history.empty:
            return None, False
        
        history.index = pd.to_datetime(history.index).strftime('%Y-%m-%d')
        
        # Find price on transaction date
        if transaction_date not in history.index:
            dates_before = [d for d in history.index if d <= transaction_date]
            if not dates_before:
                return None, False
            transaction_date = dates_before[-1]
        
        # Find price on entry date
        if entry_date not in history.index:
            dates_after = [d for d in history.index if d >= entry_date]
            if not dates_after:
                return None, False
            entry_date = dates_after[0]
        
        trans_price = history.loc[transaction_date, 'Close']
        entry_price = history.loc[entry_date, 'Close']
        
        spike_pct = ((entry_price - trans_price) / trans_price) * 100
        
        # If stock already up 10%+, we're chasing
        pass_filter = spike_pct < 10
        
        return spike_pct, pass_filter
        
    except Exception as e:
        return None, False


def simulate_scale_out_trade(ticker, entry_date, max_days=90):
    """
    Simulate scaled exit strategy:
    - Sell 33% at +8%
    - Sell 33% at +15%
    - Trailing 5% stop on remaining 34%
    
    Returns weighted average return across all tranches.
    """
    try:
        entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
        start_date = (entry_dt - timedelta(days=5)).strftime('%Y-%m-%d')
        today = datetime.now()
        max_end_date = entry_dt + timedelta(days=max_days)
        end_date = min(today, max_end_date).strftime('%Y-%m-%d')
        
        stock = yf.Ticker(ticker)
        history = stock.history(start=start_date, end=end_date)
        
        if history.empty:
            return {'success': False, 'error': 'No price data'}
        
        history.index = pd.to_datetime(history.index).strftime('%Y-%m-%d')
        
        if entry_date not in history.index:
            available_dates = sorted([d for d in history.index if d >= entry_date])
            if not available_dates:
                return {'success': False, 'error': 'No price data after entry date'}
            entry_date = available_dates[0]
        
        entry_price = history.loc[entry_date, 'Close']
        
        # Track positions
        positions = {
            'tranche1': {'size': 0.33, 'exit_price': None, 'exit_day': None, 'target': 1.08},
            'tranche2': {'size': 0.33, 'exit_price': None, 'exit_day': None, 'target': 1.15},
            'tranche3': {'size': 0.34, 'exit_price': None, 'exit_day': None, 'target': None}  # Trailing stop
        }
        
        peak_price = entry_price
        trailing_stop_price = entry_price * 0.95
        
        days_after_entry = [d for d in history.index if d >= entry_date]
        
        for i, date in enumerate(days_after_entry[1:], 1):
            high_price = history.loc[date, 'High']
            low_price = history.loc[date, 'Low']
            close_price = history.loc[date, 'Close']
            
            # Check tranche 1 exit (+8%)
            if positions['tranche1']['exit_price'] is None:
                if high_price >= entry_price * positions['tranche1']['target']:
                    positions['tranche1']['exit_price'] = entry_price * positions['tranche1']['target']
                    positions['tranche1']['exit_day'] = i
            
            # Check tranche 2 exit (+15%)
            if positions['tranche2']['exit_price'] is None:
                if high_price >= entry_price * positions['tranche2']['target']:
                    positions['tranche2']['exit_price'] = entry_price * positions['tranche2']['target']
                    positions['tranche2']['exit_day'] = i
            
            # Update trailing stop for tranche 3
            if positions['tranche3']['exit_price'] is None:
                if high_price > peak_price:
                    peak_price = high_price
                    trailing_stop_price = peak_price * 0.95
                
                # Check if trailing stop hit
                if low_price <= trailing_stop_price:
                    positions['tranche3']['exit_price'] = trailing_stop_price
                    positions['tranche3']['exit_day'] = i
        
        # Handle positions still open
        last_date = days_after_entry[-1]
        last_price = history.loc[last_date, 'Close']
        days_held = len(days_after_entry) - 1
        
        for tranche in positions.values():
            if tranche['exit_price'] is None:
                tranche['exit_price'] = last_price
                tranche['exit_day'] = days_held
        
        # Calculate weighted return
        total_return = 0
        for name, tranche in positions.items():
            tranche_return = ((tranche['exit_price'] - entry_price) / entry_price) * 100
            weighted_return = tranche_return * tranche['size']
            total_return += weighted_return
        
        # Determine exit reason
        if all(t['exit_day'] == days_held for t in positions.values()):
            exit_reason = 'still_holding'
        elif all(t['exit_price'] is not None and t['exit_day'] < days_held for t in positions.values()):
            exit_reason = 'all_tranches_exited'
        else:
            exit_reason = 'partial_exit'
        
        return {
            'success': True,
            'entry_price': round(entry_price, 2),
            'exit_price_weighted': round(sum(t['exit_price'] * t['size'] for t in positions.values()), 2),
            'return_pct': round(total_return, 2),
            'days_held': days_held,
            'exit_reason': exit_reason,
            'tranche1_exit': round(((positions['tranche1']['exit_price'] - entry_price) / entry_price) * 100, 1),
            'tranche2_exit': round(((positions['tranche2']['exit_price'] - entry_price) / entry_price) * 100, 1),
            'tranche3_exit': round(((positions['tranche3']['exit_price'] - entry_price) / entry_price) * 100, 1),
            'peak_price': round(peak_price, 2)
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def backtest_smart_strategy(json_file, min_conviction_score=5, use_technical_filters=True):
    """
    Backtest the smart multi-factor strategy.
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    results = []
    total_trades = 0
    filtered_out = 0
    winning_trades = 0
    losing_trades = 0
    total_return = 0.0
    
    filter_reasons = defaultdict(int)
    
    print(f"{'='*80}")
    print(f"SMART MULTI-FACTOR STRATEGY BACKTEST")
    print(f"{'='*80}")
    print(f"Parameters:")
    print(f"  - Minimum conviction score: {min_conviction_score}")
    print(f"  - Technical filters: {'Enabled' if use_technical_filters else 'Disabled'}")
    print(f"  - Exit strategy: Scale out (33% @ +8%, 33% @ +15%, 34% trailing stop)")
    print(f"\n{'='*80}\n")
    
    for stock_data in data['data']:
        ticker = stock_data['ticker']
        company = stock_data['company_name']
        all_trades = stock_data['trades']
        
        # Group trades by date to find clustered buying
        trades_by_date = defaultdict(list)
        for trade in all_trades:
            if trade.get('value', '').startswith('+'):
                trades_by_date[trade['trade_date']].append(trade)
        
        stock_had_signals = False
        
        for trade_date, same_day_trades in trades_by_date.items():
            entry_date = get_business_days_later(trade_date, 2)
            
            # For each trade on this date, calculate conviction
            for trade in same_day_trades:
                conviction_score, reasons = calculate_conviction_score(
                    stock_data, trade, same_day_trades
                )
                
                # Filter 1: Conviction score
                if conviction_score < min_conviction_score:
                    filter_reasons['Low conviction score'] += 1
                    continue
                
                # Filter 2: Technical position (if enabled)
                if use_technical_filters:
                    dist_from_high, current_price, high_52w, tech_pass = get_stock_technical_position(
                        ticker, entry_date
                    )
                    
                    if not tech_pass and dist_from_high is not None:
                        filter_reasons['Not down enough from high'] += 1
                        continue
                
                # Filter 3: Check if already spiked (chasing)
                if use_technical_filters:
                    spike_pct, spike_pass = check_price_spike(ticker, trade_date, entry_date)
                    if not spike_pass and spike_pct is not None:
                        filter_reasons['Already spiked (chasing)'] += 1
                        continue
                
                # Passed all filters - print signal
                if not stock_had_signals:
                    print(f"\n{'='*80}")
                    print(f"{ticker} - {company}")
                    stock_had_signals = True
                
                insider = trade['insider_name']
                value = trade['value']
                
                print(f"\n✅ SIGNAL PASSED FILTERS (Score: {conviction_score})")
                print(f"   Insider: {insider} ({trade.get('role', 'Unknown')})")
                print(f"   Purchase: {value} on {trade_date}")
                print(f"   Entry date: {entry_date}")
                for reason in reasons:
                    print(f"   • {reason}")
                
                if use_technical_filters and dist_from_high is not None:
                    print(f"   • Stock {dist_from_high:.1f}% from 52w high")
                if use_technical_filters and spike_pct is not None:
                    print(f"   • Price change since transaction: {spike_pct:+.1f}%")
                
                # Simulate trade
                result = simulate_scale_out_trade(ticker, entry_date, max_days=90)
                
                if result['success']:
                    total_trades += 1
                    return_pct = result['return_pct']
                    total_return += return_pct
                    
                    if return_pct > 0:
                        winning_trades += 1
                        emoji = "💰"
                    else:
                        losing_trades += 1
                        emoji = "📉"
                    
                    print(f"\n   {emoji} RESULT:")
                    print(f"      Entry: ${result['entry_price']} | Peak: ${result['peak_price']}")
                    print(f"      Exit (weighted avg): ${result['exit_price_weighted']}")
                    print(f"      Return: {return_pct:+.2f}% over {result['days_held']} days")
                    print(f"      Tranches: T1={result['tranche1_exit']:+.1f}% | "
                          f"T2={result['tranche2_exit']:+.1f}% | T3={result['tranche3_exit']:+.1f}%")
                    
                    results.append({
                        'ticker': ticker,
                        'company': company,
                        'insider': insider,
                        'role': trade.get('role', ''),
                        'trade_date': trade_date,
                        'entry_date': entry_date,
                        'value': value,
                        'conviction_score': conviction_score,
                        'dist_from_52w_high': round(dist_from_high, 1) if dist_from_high else None,
                        'spike_pct': round(spike_pct, 1) if spike_pct else None,
                        **result
                    })
                else:
                    print(f"   ⚠️  Could not simulate: {result.get('error', 'Unknown error')}")
                    filtered_out += 1
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"\nFiltering Results:")
    print(f"  Total opportunities considered: {sum(filter_reasons.values()) + total_trades + filtered_out}")
    print(f"  Filtered out: {sum(filter_reasons.values())}")
    for reason, count in sorted(filter_reasons.items(), key=lambda x: x[1], reverse=True):
        print(f"    • {reason}: {count}")
    print(f"  Passed filters but no data: {filtered_out}")
    print(f"  TRADED: {total_trades}")
    
    if total_trades > 0:
        print(f"\nTrading Results:")
        print(f"  Winning Trades: {winning_trades} ({winning_trades/total_trades*100:.1f}%)")
        print(f"  Losing Trades: {losing_trades} ({losing_trades/total_trades*100:.1f}%)")
        
        avg_return = total_return / total_trades
        print(f"\n  Average Return per Trade: {avg_return:+.2f}%")
        print(f"  Total Return (sum): {total_return:+.2f}%")
        
        if results:
            returns = [r['return_pct'] for r in results]
            print(f"\n  Best Trade: {max(returns):+.2f}%")
            print(f"  Worst Trade: {min(returns):+.2f}%")
            
            best_trade = max(results, key=lambda x: x.get('return_pct', -999))
            worst_trade = min(results, key=lambda x: x.get('return_pct', 999))
            
            print(f"\n🏆 Best Example: {best_trade['ticker']} - {best_trade['insider']}")
            print(f"   Entry: ${best_trade['entry_price']} → Exit: ${best_trade['exit_price_weighted']} = {best_trade['return_pct']:+.2f}%")
            print(f"   Conviction score: {best_trade['conviction_score']}")
            
            print(f"\n💀 Worst Example: {worst_trade['ticker']} - {worst_trade['insider']}")
            print(f"   Entry: ${worst_trade['entry_price']} → Exit: ${worst_trade['exit_price_weighted']} = {worst_trade['return_pct']:+.2f}%")
            print(f"   Conviction score: {worst_trade['conviction_score']}")
    
    print(f"\n{'='*80}")
    
    if total_trades > 0:
        if avg_return > 2.0:
            print(f"✅ VERDICT: STRONG STRATEGY")
            print(f"   Average return {avg_return:.2f}% significantly better than naive approach (1.93%)")
        elif avg_return > 0:
            print(f"✅ VERDICT: PROFITABLE but marginal")
            print(f"   Average return {avg_return:.2f}% per trade")
        else:
            print(f"❌ VERDICT: LOSING STRATEGY")
            print(f"   Average loss {avg_return:.2f}% per trade")
    else:
        print(f"⚠️  VERDICT: Filters too strict - no trades passed")
    
    print(f"{'='*80}\n")
    
    return results


if __name__ == '__main__':
    json_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/top_monthly_insider_trades.json'
    
    # Run with smart filters
    results = backtest_smart_strategy(
        json_file=json_file,
        min_conviction_score=5,  # Require decent conviction
        use_technical_filters=True  # Enable all smart filters
    )
    
    # Save results
    if results:
        import csv
        output_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_smart_strategy_results.csv'
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        
        print(f"✅ Detailed results saved to: {output_file}")
        
        # Print comparison
        print(f"\n{'='*80}")
        print(f"STRATEGY COMPARISON")
        print(f"{'='*80}")
        print(f"{'Strategy':<30} {'Trades':<10} {'Win Rate':<12} {'Avg Return':<15}")
        print(f"{'-'*80}")
        
        if results:
            smart_trades = len(results)
            smart_wins = len([r for r in results if r['return_pct'] > 0])
            smart_avg = sum(r['return_pct'] for r in results) / len(results)
            
            print(f"{'Naive (fixed 5% stop)':<30} {80:<10} {32.5:<12.1f} {1.93:<15.2f}")
            print(f"{'Trailing stop':<30} {80:<10} {62.0:<12.1f} {1.76:<15.2f}")
            print(f"{'Smart Multi-Factor':<30} {smart_trades:<10} {smart_wins/smart_trades*100:<12.1f} {smart_avg:<15.2f}")
        
        print(f"{'='*80}\n")
