#!/usr/bin/env python3
#testcommit
"""
Adaptive Filter Backtest: Learn which stocks are bad by tracking performance
- 3 consecutive stop losses in <10 days → blacklist for 90 days
- Win rate < 30% after 5+ trades → reduce position size by 50%
"""

import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from multiprocessing import Pool, cpu_count

def fetch_ticker_data(ticker):
    """Fetch historical data for a ticker"""
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(start='2022-03-16', end='2026-02-14')
        if not history.empty:
            # Remove timezone to avoid comparison issues
            history.index = history.index.tz_localize(None)
            return (ticker, history)
    except:
        pass
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

def count_recent_insider_purchases(ticker, check_date, all_insider_purchases, days_back=14):
    """Count how many insider purchases happened in the last N days"""
    check_dt = datetime.strptime(check_date, '%Y-%m-%d')
    count = 0
    
    for purchase in all_insider_purchases.get(ticker, []):
        purchase_dt = datetime.strptime(purchase['filing_date'], '%Y-%m-%d')
        days_diff = (check_dt - purchase_dt).days
        
        if 0 <= days_diff <= days_back:
            count += 1
    
    return count

def backtest_adaptive():
    """Backtest with adaptive filtering - learn from bad stocks"""
    
    with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/merged_insider_trades.json', 'r') as f:
        data = json.load(f)
    
    tickers = [stock['ticker'] for stock in data['data']]
    
    print(f"🔄 Loading stock data for {len(tickers)} tickers in parallel...")
    with Pool(cpu_count()) as pool:
        results = pool.map(fetch_ticker_data, tickers)
    
    price_cache = {ticker: history for ticker, history in results if history is not None}
    print(f"\n✅ Loaded data for {len(price_cache)} tickers\n")
    
    # Build insider purchase timeline
    all_insider_purchases = defaultdict(list)
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
                
                purchase_info = {
                    'trade_date': trade_date,
                    'filing_date': entry_date,
                    'insider': trade['insider_name'],
                    'value': trade_value
                }
                
                all_insider_purchases[ticker].append(purchase_info)
                
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
    
    start_date = all_trades[0]['entry_date']
    end_date = '2026-02-13'
    
    print(f"📅 Generating business day calendar ({start_date} to {end_date})...")
    all_business_days = generate_business_days(start_date, end_date)
    print(f"   {len(all_business_days)} business days\n")
    
    # Adaptive tracking
    ticker_performance = defaultdict(lambda: {
        'consecutive_stop_losses': 0,
        'last_stop_loss_date': None,
        'total_trades': 0,
        'wins': 0,
        'blacklisted_until': None,
        'position_multiplier': 1.0
    })
    
    open_positions = defaultdict(list)
    closed_trades = []
    pending_trades = list(all_trades)
    
    initial_position_size = 1000
    
    print(f"{'='*80}")
    print("ADAPTIVE FILTER BACKTEST - LEARNING FROM BAD STOCKS")
    print(f"{'='*80}\n")
    
    for day_idx, current_date in enumerate(all_business_days):
        if day_idx % 50 == 0:
            blacklisted_count = sum(1 for t, p in ticker_performance.items() 
                                   if p['blacklisted_until'] and p['blacklisted_until'] >= current_date)
            print(f"📆 {current_date} (Day {day_idx+1}/{len(all_business_days)}) | Open: {sum(len(v) for v in open_positions.values())} | Blacklisted: {blacklisted_count}")
        
        # Remove blacklists that have expired
        current_dt = datetime.strptime(current_date, '%Y-%m-%d')
        
        # Open trades for this date
        trades_to_open = [t for t in pending_trades if t['entry_date'] == current_date]
        
        for trade in trades_to_open:
            ticker = trade['ticker']
            
            if ticker not in price_cache:
                continue
            
            # Check if blacklisted
            perf = ticker_performance[ticker]
            if perf['blacklisted_until']:
                blacklist_dt = datetime.strptime(perf['blacklisted_until'], '%Y-%m-%d')
                if current_dt < blacklist_dt:
                    continue  # Skip this trade
                else:
                    perf['blacklisted_until'] = None  # Expired
                    perf['consecutive_stop_losses'] = 0  # Reset
            
            history = price_cache[ticker]
            
            current_date_ts = pd.Timestamp(current_date)
            
            if current_date_ts not in history.index:
                available_dates = sorted([d for d in history.index if d >= current_date_ts])
                if not available_dates:
                    continue
                actual_entry_date = available_dates[0].strftime('%Y-%m-%d')
            else:
                actual_entry_date = current_date
            
            entry_price = history.loc[pd.Timestamp(actual_entry_date), 'Close']
            
            # Calculate position size
            recent_purchase_count = count_recent_insider_purchases(ticker, current_date, all_insider_purchases, days_back=14)
            
            position_multiplier = perf['position_multiplier']
            if recent_purchase_count >= 5:
                position_multiplier *= 2.0
            elif recent_purchase_count >= 3:
                position_multiplier *= 1.5
            
            for pos in open_positions[ticker]:
                if pd.Timestamp(current_date) in history.index:
                    current_price = history.loc[pd.Timestamp(current_date), 'Close']
                    current_profit_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                    if current_profit_pct > 15:
                        position_multiplier *= 0.5
                        break
            
            position_size = initial_position_size * position_multiplier
            shares = position_size / entry_price
            
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
                'days_held': 0
            }
            
            open_positions[ticker].append(position)
            pending_trades.remove(trade)
        
        # Check all open positions
        for ticker in list(open_positions.keys()):
            if ticker not in price_cache:
                continue
            
            history = price_cache[ticker]
            
            current_date_ts = pd.Timestamp(current_date)
            if current_date_ts not in history.index:
                continue
            
            close_price = history.loc[current_date_ts, 'Close']
            high_price = history.loc[current_date_ts, 'High']
            
            if pd.isna(high_price):
                high_price = close_price
            
            positions_to_close = []
            
            for pos in open_positions[ticker]:
                pos['days_held'] += 1
                
                if high_price > pos['highest_price']:
                    pos['highest_price'] = high_price
                
                current_profit_pct = ((close_price - pos['entry_price']) / pos['entry_price']) * 100
                
                grace_period = 5
                if pos['days_held'] <= grace_period:
                    continue
                
                profit_cushion = 3.0
                if current_profit_pct > profit_cushion:
                    continue
                
                dynamic_stop_pct = 5.0
                if pos['days_held'] > 20:
                    dynamic_stop_pct = 7.5
                if pos['days_held'] > 60:
                    dynamic_stop_pct = 10.0
                
                trailing_stop_price = pos['highest_price'] * (1 - dynamic_stop_pct / 100)
                
                if close_price <= trailing_stop_price:
                    actual_exit_price = min(trailing_stop_price, close_price)
                    
                    return_pct = ((actual_exit_price - pos['entry_price']) / pos['entry_price']) * 100
                    profit_loss = pos['amount_invested'] * (return_pct / 100)
                    returned_amount = pos['amount_invested'] + profit_loss
                    
                    closed_trades.append({
                        'ticker': ticker,
                        'company': pos['company'],
                        'trade_date': pos['trade_date'],
                        'entry_date': pos['entry_date'],
                        'entry_price': pos['entry_price'],
                        'exit_date': current_date,
                        'exit_price': actual_exit_price,
                        'exit_reason': 'stop_loss',
                        'amount_invested': pos['amount_invested'],
                        'returned_amount': returned_amount,
                        'profit_loss': profit_loss,
                        'return_pct': return_pct,
                        'shares': pos['shares'],
                        'days_held': pos['days_held'],
                        'highest_price': pos['highest_price'],
                        'insider': pos['insider'],
                        'role': pos['role']
                    })
                    
                    # ADAPTIVE TRACKING
                    perf = ticker_performance[ticker]
                    perf['total_trades'] += 1
                    
                    if return_pct > 0:
                        perf['wins'] += 1
                        perf['consecutive_stop_losses'] = 0
                    else:
                        perf['consecutive_stop_losses'] += 1
                        perf['last_stop_loss_date'] = current_date
                    
                    # 3 STRIKES RULE
                    if perf['consecutive_stop_losses'] >= 3 and pos['days_held'] < 10:
                        blacklist_until = (current_dt + timedelta(days=90)).strftime('%Y-%m-%d')
                        perf['blacklisted_until'] = blacklist_until
                        print(f"🚫 BLACKLISTED {ticker} until {blacklist_until} (3 quick stop losses)")
                    
                    # WIN RATE RULE
                    if perf['total_trades'] >= 5:
                        win_rate = perf['wins'] / perf['total_trades']
                        if win_rate < 0.30:
                            perf['position_multiplier'] = 0.5
                            print(f"⚠️  REDUCED {ticker} position size to 50% (win rate: {win_rate*100:.0f}%)")
                    
                    positions_to_close.append(pos)
            
            for pos in positions_to_close:
                open_positions[ticker].remove(pos)
            
            if not open_positions[ticker]:
                del open_positions[ticker]
    
    # Close remaining positions
    print(f"\n{'='*80}")
    print("CLOSING REMAINING OPEN POSITIONS")
    print(f"{'='*80}\n")
    
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
            return_pct = ((final_price - pos['entry_price']) / pos['entry_price']) * 100
            profit_loss = pos['amount_invested'] * (return_pct / 100)
            returned_amount = pos['amount_invested'] + profit_loss
            
            closed_trades.append({
                'ticker': ticker,
                'company': pos['company'],
                'trade_date': pos['trade_date'],
                'entry_date': pos['entry_date'],
                'entry_price': pos['entry_price'],
                'exit_date': final_date,
                'exit_price': final_price,
                'exit_reason': 'end_of_period',
                'amount_invested': pos['amount_invested'],
                'returned_amount': returned_amount,
                'profit_loss': profit_loss,
                'return_pct': return_pct,
                'shares': pos['shares'],
                'days_held': pos['days_held'],
                'highest_price': pos['highest_price'],
                'peak_price': pos['highest_price'],
                'insider': pos['insider'],
                'role': pos['role']
            })
    
    # Calculate results
    df = pd.DataFrame(closed_trades)
    
    total_invested = df['amount_invested'].sum()
    total_returned = df['returned_amount'].sum()
    total_profit = df['profit_loss'].sum()
    roi = (total_profit / total_invested) * 100
    
    winning_trades = df[df['return_pct'] > 0]
    losing_trades = df[df['return_pct'] <= 0]
    
    avg_return = df['return_pct'].mean()
    avg_days_held = df['days_held'].mean()
    
    print(f"\n{'='*80}")
    print("FINAL RESULTS - ADAPTIVE FILTER STRATEGY")
    print(f"{'='*80}")
    print(f"Total Trades: {len(df)}")
    print(f"  Winning: {len(winning_trades)} ({len(winning_trades)/len(df)*100:.1f}%)")
    print(f"  Losing: {len(losing_trades)} ({len(losing_trades)/len(df)*100:.1f}%)")
    print(f"\nAverage Return per Trade: {avg_return:+.2f}%")
    print(f"Average Days Held: {avg_days_held:.0f} days")
    print(f"\n💰 PORTFOLIO PERFORMANCE:")
    print(f"   Total Invested: ${total_invested:,.2f}")
    print(f"   Total Returned: ${total_returned:,.2f}")
    print(f"   Net Profit/Loss: ${total_profit:,.2f}")
    print(f"   ROI: {roi:+.2f}%")
    
    best_trade = df.loc[df['return_pct'].idxmax()]
    print(f"\n🏆 Best Trade: {best_trade['ticker']} - {best_trade['return_pct']:+.1f}%")
    print(f"   ${best_trade['entry_price']:.2f} → ${best_trade['exit_price']:.2f} ({int(best_trade['days_held'])} days)")
    
    worst_trade = df.loc[df['return_pct'].idxmin()]
    print(f"\n💀 Worst Trade: {worst_trade['ticker']} - {worst_trade['return_pct']:+.1f}%")
    print(f"   ${worst_trade['entry_price']:.2f} → ${worst_trade['exit_price']:.2f} ({int(worst_trade['days_held'])} days)")
    
    # Blacklist summary
    blacklisted_tickers = [t for t, p in ticker_performance.items() if p['blacklisted_until']]
    reduced_tickers = [t for t, p in ticker_performance.items() if p['position_multiplier'] < 1.0]
    
    print(f"\n📊 ADAPTIVE FILTER STATS:")
    print(f"   Blacklisted tickers: {len(blacklisted_tickers)}")
    if blacklisted_tickers:
        print(f"   {', '.join(blacklisted_tickers[:10])}")
    print(f"   Reduced position tickers: {len(reduced_tickers)}")
    if reduced_tickers:
        print(f"   {', '.join(reduced_tickers[:10])}")
    
    print(f"\n{'='*80}\n")
    
    output_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_adaptive_filter_results.csv'
    df.to_csv(output_path, index=False)
    print(f"✅ Results saved to: {output_path}")
    
    return closed_trades

if __name__ == '__main__':
    backtest_adaptive()
