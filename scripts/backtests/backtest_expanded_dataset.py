#!/usr/bin/env python3
"""
Backtest the reputation system strategy on the FULL expanded dataset.
This tests the strategy on ALL 3,194 tickers with insider purchases.

Based on: backtest_reputation_system.py (commit c15d297560b2a726dff7d6193e0ca24db690c503)
Modified to use: expanded_insider_trades.json (all SEC companies with purchases)
"""

import json
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def load_insider_data():
    """Load insider trades from expanded dataset."""
    data_path = Path(__file__).parent.parent.parent / "output CSVs" / "expanded_insider_trades.json"
    
    print("=" * 80)
    print("LOADING EXPANDED INSIDER DATASET")
    print("=" * 80)
    
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    metadata = data.get('metadata', {})
    print(f"\nDataset Statistics:")
    print(f"  Total Tickers:   {metadata.get('total_tickers', 0):,}")
    print(f"  Total Purchases: {metadata.get('total_purchases', 0):,}")
    print(f"  Total Value:     ${metadata.get('total_value', 0):,.0f}")
    print(f"  Source:          {metadata.get('source', 'Unknown')}")
    print(f"  Time Period:     {metadata.get('time_period', 'Unknown')}")
    print()
    
    return data['data']

def calculate_reputation_score(ticker_data):
    """
    Calculate reputation score based on insider trading patterns.
    
    Returns:
        dict with 'score' (0-100), 'grade' ('Excellent'/'Good'/'Fair'/'Poor'), 
        and component scores
    """
    
    trades = ticker_data.get('trades', [])
    
    if not trades:
        return {'score': 0, 'grade': 'Poor', 'components': {}}
    
    # Component 1: Purchase Frequency (0-25 points)
    purchase_count = len(trades)
    if purchase_count >= 20:
        frequency_score = 25
    elif purchase_count >= 10:
        frequency_score = 20
    elif purchase_count >= 5:
        frequency_score = 15
    else:
        frequency_score = min(purchase_count * 3, 15)
    
    # Component 2: Total Value (0-25 points)
    total_value = ticker_data.get('total_value', 0)
    if total_value >= 100_000_000:  # $100M+
        value_score = 25
    elif total_value >= 50_000_000:  # $50M+
        value_score = 20
    elif total_value >= 10_000_000:  # $10M+
        value_score = 15
    elif total_value >= 1_000_000:   # $1M+
        value_score = 10
    else:
        value_score = 5
    
    # Component 3: Unique Insiders (0-25 points)
    unique_insiders = ticker_data.get('unique_insiders', 0)
    if unique_insiders >= 10:
        insider_score = 25
    elif unique_insiders >= 5:
        insider_score = 20
    elif unique_insiders >= 3:
        insider_score = 15
    else:
        insider_score = min(unique_insiders * 5, 15)
    
    # Component 4: Recent Activity (0-25 points)
    recent_trades = [t for t in trades if t.get('filing_date')]
    if recent_trades:
        try:
            latest_dates = []
            for t in recent_trades:
                date_str = t['filing_date'].split()[0]  # Take just YYYY-MM-DD part
                latest_dates.append(datetime.strptime(date_str, '%Y-%m-%d'))
            
            latest_date = max(latest_dates)
            days_since = (datetime.now() - latest_date).days
            
            if days_since <= 90:      # Within 3 months
                recency_score = 25
            elif days_since <= 180:   # Within 6 months
                recency_score = 20
            elif days_since <= 365:   # Within 1 year
                recency_score = 15
            else:
                recency_score = 10
        except:
            recency_score = 10
    else:
        recency_score = 10
    
    # Calculate total score
    total_score = frequency_score + value_score + insider_score + recency_score
    
    # Assign grade
    if total_score >= 80:
        grade = 'Excellent'
    elif total_score >= 60:
        grade = 'Good'
    elif total_score >= 40:
        grade = 'Fair'
    else:
        grade = 'Poor'
    
    return {
        'score': total_score,
        'grade': grade,
        'components': {
            'frequency': frequency_score,
            'value': value_score,
            'insiders': insider_score,
            'recency': recency_score
        }
    }

def get_stock_data(ticker, start_date, end_date, max_retries=3):
    """Fetch stock data with retries."""
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            
            if not hist.empty:
                return hist
                
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  ⚠️  Failed to fetch {ticker}: {e}")
    
    return pd.DataFrame()

def check_explosive_catalyst(hist, entry_date, lookback_days=5):
    """
    Check if there was an explosive move (>20% gain in 3-5 days) before entry.
    """
    if hist.empty:
        return False, None
    
    try:
        entry_idx = hist.index.get_indexer([entry_date], method='ffill')[0]
        if entry_idx < lookback_days:
            return False, None
        
        lookback_start = entry_idx - lookback_days
        window = hist.iloc[lookback_start:entry_idx + 1]
        
        if len(window) < 3:
            return False, None
        
        low_price = window['Low'].min()
        entry_price = window['Close'].iloc[-1]
        
        gain_pct = ((entry_price - low_price) / low_price) * 100
        
        return gain_pct >= 20, gain_pct
        
    except:
        return False, None

def detect_trend_reversal(hist, entry_idx, current_idx):
    """
    Detect if trend has reversed using second dip comparison.
    Must wait 2 days grace period before checking.
    """
    days_held = current_idx - entry_idx
    
    if days_held < 2:  # Grace period
        return False, None
    
    try:
        entry_price = hist['Close'].iloc[entry_idx]
        peak_price = hist['Close'].iloc[entry_idx:current_idx + 1].max()
        
        if peak_price <= entry_price * 1.05:  # No meaningful rally
            return False, None
        
        # Find first dip from peak
        after_peak_idx = hist['Close'].iloc[entry_idx:current_idx + 1].idxmax()
        peak_idx_num = hist.index.get_indexer([after_peak_idx])[0]
        
        if peak_idx_num >= current_idx - 1:
            return False, None
        
        # Calculate first dip
        first_dip_window = hist.iloc[peak_idx_num:current_idx]
        if len(first_dip_window) < 2:
            return False, None
        
        first_dip_start = first_dip_window['Close'].iloc[0]
        first_dip_low = first_dip_window['Low'].min()
        first_dip_size = ((first_dip_start - first_dip_low) / first_dip_start) * 100
        
        # Check for recovery attempt
        recovery_high = first_dip_window['High'].max()
        recovery_pct = ((recovery_high - first_dip_low) / first_dip_low) * 100
        
        if recovery_pct < 5:  # No recovery attempt
            return False, None
        
        # Find second dip
        recovery_idx = first_dip_window['High'].idxmax()
        recovery_idx_num = hist.index.get_indexer([recovery_idx])[0]
        
        if recovery_idx_num >= current_idx:
            return False, None
        
        second_dip_window = hist.iloc[recovery_idx_num:current_idx + 1]
        if len(second_dip_window) < 2:
            return False, None
        
        second_dip_start = second_dip_window['Close'].iloc[0]
        current_price = second_dip_window['Close'].iloc[-1]
        second_dip_size = ((second_dip_start - current_price) / second_dip_start) * 100
        
        # Calculate slopes (percentage per day)
        first_dip_days = len(first_dip_window)
        second_dip_days = len(second_dip_window)
        
        first_slope = first_dip_size / max(first_dip_days, 1)
        second_slope = second_dip_size / max(second_dip_days, 1)
        
        # Reversal conditions
        is_steep = second_slope >= 3.0  # At least 3%/day decline
        is_comparable = second_slope >= (first_slope * 0.5)  # At least 50% of first dip
        
        return (is_steep and is_comparable), second_slope
        
    except Exception as e:
        return False, None

def backtest_ticker(ticker_data, reputation_score):
    """
    Backtest a single ticker using the trend-following strategy.
    """
    ticker = ticker_data['ticker']
    trades = ticker_data.get('trades', [])
    
    if not trades:
        return []
    
    # Get date range
    try:
        filing_dates = []
        for t in trades:
            if not t.get('filing_date'):
                continue
            date_str = t['filing_date'].split()[0]  # Take just YYYY-MM-DD part
            filing_dates.append(datetime.strptime(date_str, '%Y-%m-%d'))
        
        if not filing_dates:
            return []
        
        start_date = min(filing_dates) - timedelta(days=30)
        end_date = datetime.now()
        
    except Exception as e:
        return []
    
    # Fetch stock data
    hist = get_stock_data(ticker, start_date, end_date)
    
    if hist.empty or len(hist) < 10:
        return []
    
    closed_trades = []
    
    for trade in trades:
        try:
            # Parse filing date (handle both formats: YYYY-MM-DD and YYYY-MM-DD HH:MM:SS)
            date_str = trade['filing_date'].split()[0]  # Take just YYYY-MM-DD part
            filing_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Find entry date (filing date or next available)
            entry_idx = hist.index.get_indexer([filing_date], method='ffill')[0]
            if entry_idx < 0 or entry_idx >= len(hist):
                continue
            
            entry_date = hist.index[entry_idx]
            entry_price = hist['Close'].iloc[entry_idx]
            
            # Filter: Skip penny stocks (< $5)
            if entry_price < 5:
                continue
            
            # Check for explosive catalyst
            has_catalyst, catalyst_gain = check_explosive_catalyst(hist, entry_date)
            if not has_catalyst:
                continue
            
            # Simulate holding
            exit_date = None
            exit_price = None
            exit_reason = None
            peak_gain = 0
            
            stop_loss_threshold = entry_price * 0.95  # -5%
            days_since_peak = 0
            peak_price = entry_price
            peak_date = entry_date
            
            for i in range(entry_idx + 1, len(hist)):
                current_date = hist.index[i]
                current_price = hist['Close'].iloc[i]
                
                # Track peak
                if current_price > peak_price:
                    peak_price = current_price
                    peak_date = current_date
                    days_since_peak = 0
                else:
                    days_since_peak += 1
                
                current_gain = ((current_price - entry_price) / entry_price) * 100
                peak_gain = max(peak_gain, current_gain)
                
                # Exit Rule 1: Stop Loss (-5%)
                if current_price <= stop_loss_threshold:
                    exit_date = current_date
                    exit_price = current_price
                    exit_reason = 'stop_loss'
                    break
                
                # Exit Rule 2: Trend Reversal (second dip)
                is_reversal, slope = detect_trend_reversal(hist, entry_idx, i)
                if is_reversal:
                    exit_date = current_date
                    exit_price = current_price
                    exit_reason = 'trend_reversal'
                    break
                
                # Exit Rule 3: Catalyst Expiration (15 days since peak OR 15% drawdown)
                drawdown = ((peak_price - current_price) / peak_price) * 100
                if days_since_peak >= 15 or drawdown >= 15:
                    exit_date = current_date
                    exit_price = current_price
                    exit_reason = 'catalyst_expiration'
                    break
            
            # If still holding at end of data
            if exit_date is None:
                exit_date = hist.index[-1]
                exit_price = hist['Close'].iloc[-1]
                exit_reason = 'end_of_period'
            
            # Calculate return
            return_pct = ((exit_price - entry_price) / entry_price) * 100
            days_held = (exit_date - entry_date).days
            
            closed_trades.append({
                'ticker': ticker,
                'reputation_score': reputation_score['score'],
                'reputation_grade': reputation_score['grade'],
                'entry_date': entry_date.strftime('%Y-%m-%d'),
                'entry_price': round(entry_price, 2),
                'exit_date': exit_date.strftime('%Y-%m-%d'),
                'exit_price': round(exit_price, 2),
                'return_pct': round(return_pct, 2),
                'peak_gain': round(peak_gain, 2),
                'days_held': days_held,
                'exit_reason': exit_reason,
                'catalyst_gain': round(catalyst_gain, 2) if catalyst_gain else 0
            })
            
        except Exception as e:
            continue
    
    return closed_trades

def main():
    """Run backtest on expanded dataset."""
    
    # Load data
    insider_data = load_insider_data()
    
    print("=" * 80)
    print("CALCULATING REPUTATION SCORES")
    print("=" * 80)
    print()
    
    # Calculate reputation scores
    ticker_reputations = {}
    for ticker_data in insider_data:
        ticker = ticker_data['ticker']
        reputation = calculate_reputation_score(ticker_data)
        ticker_reputations[ticker] = reputation
    
    # Group by reputation grade
    by_grade = {}
    for ticker, rep in ticker_reputations.items():
        grade = rep['grade']
        by_grade[grade] = by_grade.get(grade, 0) + 1
    
    print("Reputation Distribution:")
    for grade in ['Excellent', 'Good', 'Fair', 'Poor']:
        count = by_grade.get(grade, 0)
        pct = (count / len(ticker_reputations)) * 100
        print(f"  {grade:12} {count:4} ({pct:5.1f}%)")
    print()
    
    # Run backtests
    print("=" * 80)
    print("RUNNING BACKTESTS")
    print("=" * 80)
    print()
    
    all_trades = []
    
    for i, ticker_data in enumerate(insider_data, 1):
        ticker = ticker_data['ticker']
        reputation = ticker_reputations[ticker]
        
        if i % 50 == 0:
            print(f"Progress: {i}/{len(insider_data)} tickers processed...")
        
        trades = backtest_ticker(ticker_data, reputation)
        all_trades.extend(trades)
    
    print(f"\nCompleted: {len(insider_data)} tickers backtested")
    print()
    
    if not all_trades:
        print("❌ No trades matched strategy criteria")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(all_trades)
    
    # Save results
    output_path = Path(__file__).parent.parent.parent / "output CSVs" / "backtest_expanded_dataset_results.csv"
    df.to_csv(output_path, index=False)
    
    # Calculate statistics
    print("=" * 80)
    print("BACKTEST RESULTS - EXPANDED DATASET (ALL SEC COMPANIES)")
    print("=" * 80)
    print()
    
    total_trades = len(df)
    winning_trades = len(df[df['return_pct'] > 0])
    win_rate = (winning_trades / total_trades) * 100
    
    avg_return = df['return_pct'].mean()
    median_return = df['return_pct'].median()
    total_return = df['return_pct'].sum()
    
    best_trade = df.loc[df['return_pct'].idxmax()]
    worst_trade = df.loc[df['return_pct'].idxmin()]
    
    print(f"Overall Performance:")
    print(f"  Total Trades:     {total_trades:,}")
    print(f"  Winning Trades:   {winning_trades:,} ({win_rate:.1f}%)")
    print(f"  Average Return:   {avg_return:+.2f}%")
    print(f"  Median Return:    {median_return:+.2f}%")
    print(f"  ROI (sum):        {total_return:+.2f}%")
    print()
    
    print(f"Best Trade:  {best_trade['ticker']:6} {best_trade['return_pct']:+8.1f}%  ({best_trade['entry_date']} → {best_trade['exit_date']})")
    print(f"Worst Trade: {worst_trade['ticker']:6} {worst_trade['return_pct']:+8.1f}%  ({worst_trade['entry_date']} → {worst_trade['exit_date']})")
    print()
    
    # By reputation grade
    print("Performance by Reputation Grade:")
    print()
    for grade in ['Excellent', 'Good', 'Fair', 'Poor']:
        grade_df = df[df['reputation_grade'] == grade]
        
        if len(grade_df) == 0:
            continue
        
        grade_trades = len(grade_df)
        grade_wins = len(grade_df[grade_df['return_pct'] > 0])
        grade_win_rate = (grade_wins / grade_trades) * 100
        grade_avg = grade_df['return_pct'].mean()
        grade_roi = grade_df['return_pct'].sum()
        
        print(f"  {grade}:")
        print(f"    Trades:      {grade_trades:,}")
        print(f"    Win Rate:    {grade_win_rate:.1f}%")
        print(f"    Avg Return:  {grade_avg:+.2f}%")
        print(f"    ROI:         {grade_roi:+.2f}%")
        print()
    
    # By exit reason
    print("Exit Reason Breakdown:")
    for reason in df['exit_reason'].unique():
        reason_df = df[df['exit_reason'] == reason]
        count = len(reason_df)
        pct = (count / total_trades) * 100
        avg_ret = reason_df['return_pct'].mean()
        print(f"  {reason:20} {count:5} ({pct:5.1f}%)  Avg: {avg_ret:+7.2f}%")
    print()
    
    print(f"✅ Results saved to: {output_path}")
    print()

if __name__ == '__main__':
    main()
