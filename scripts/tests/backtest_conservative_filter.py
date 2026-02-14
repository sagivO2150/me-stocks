#!/usr/bin/env python3
"""
Conservative Filter Backtest: Pre-filter stocks before trading
- Market cap > $300M
- Stock hasn't fallen >20% in last 30 days
- Require 2+ unique insiders trading (not just 1)
"""

import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from multiprocessing import Pool, cpu_count

def fetch_ticker_data_with_info(ticker):
    """Fetch historical data and company info for a ticker"""
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(start='2022-03-16', end='2026-02-14')
        
        if not history.empty:
            # Remove timezone to avoid comparison issues
            history.index = history.index.tz_localize(None)
            # Get market cap
            try:
                info = stock.info
                market_cap = info.get('marketCap', 0)
            except:
                market_cap = 0
            
            return (ticker, history, market_cap)
    except:
        pass
    return (ticker, None, 0)

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

def backtest_conservative():
    """Backtest with conservative upfront filters"""
    
    with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/merged_insider_trades.json', 'r') as f:
        data = json.load(f)
    
    # PRE-FILTER: Require 2+ unique insiders
    print("🔍 Applying pre-filters...")
    filtered_stocks = []
    for stock_data in data['data']:
        unique_insiders = stock_data.get('unique_insiders', 0)
        if unique_insiders >= 2:
            filtered_stocks.append(stock_data)
        else:
            print(f"   ✗ {stock_data['ticker']}: Only {unique_insiders} insider(s)")
    
    print(f"\n✅ After insider filter: {len(filtered_stocks)}/{len(data['data'])} stocks\n")
    
    tickers = [stock['ticker'] for stock in filtered_stocks]
    
    print(f"🔄 Loading stock data + market caps for {len(tickers)} tickers...")
    with Pool(cpu_count()) as pool:
        results = pool.map(fetch_ticker_data_with_info, tickers)
    
    # PRE-FILTER: Market cap > $300M
    price_cache = {}
    market_caps = {}
    
    for ticker, history, market_cap in results:
        if history is not None:
            if market_cap > 300_000_000:
                price_cache[ticker] = history
                market_caps[ticker] = market_cap
            else:
                cap_str = f"${market_cap/1e6:.0f}M" if market_cap > 0 else "N/A"
                print(f"   ✗ {ticker}: Market cap {cap_str} < $300M")
    
    print(f"\n✅ After market cap filter: {len(price_cache)} stocks")
    
    # Build insider purchase timeline (only for passing stocks)
    all_insider_purchases = defaultdict(list)
    all_trades = []
    
    for stock_data in filtered_stocks:
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
    
    print(f"\n📅 Generating business day calendar ({start_date} to {end_date})...")
    all_business_days = generate_business_days(start_date, end_date)
    print(f"   {len(all_business_days)} business days\n")
    
    open_positions = defaultdict(list)
    closed_trades = []
    pending_trades = list(all_trades)
    skipped_momentum_check = 0
    
    initial_position_size = 1000
    
    print(f"{'='*80}")
    print("CONSERVATIVE FILTER BACKTEST - PRE-FILTERED QUALITY STOCKS")
    print(f"{'='*80}\n")
    
    for day_idx, current_date in enumerate(all_business_days):
        if day_idx % 50 == 0:
            print(f"📆 {current_date} (Day {day_idx+1}/{len(all_business_days)}) | Open: {sum(len(v) for v in open_positions.values())} | Skipped: {skipped_momentum_check}")
        
        # Open trades for this date
        trades_to_open = [t for t in pending_trades if t['entry_date'] == current_date]
        
        for trade in trades_to_open:
            ticker = trade['ticker']
            
            if ticker not in price_cache:
                continue
            
            history = price_cache[ticker]
            
            current_date_ts = pd.Timestamp(current_date)
            if current_date_ts not in history.index:
                available_dates = sorted([d for d in history.index if d >= current_date_ts])
                if not available_dates:
                    continue
                actual_entry_date = available_dates[0].strftime('%Y-%m-%d')
            else:
                actual_entry_date = current_date
            
            # PRE-FILTER: Check if stock fell >20% in last 30 days
            entry_dt = datetime.strptime(actual_entry_date, '%Y-%m-%d')
            days_back_30 = (entry_dt - timedelta(days=30)).strftime('%Y-%m-%d')
            
            actual_entry_ts = pd.Timestamp(actual_entry_date)
            past_prices = history[(history.index >= days_back_30) & (history.index <= actual_entry_ts)]
            if len(past_prices) > 0:
                high_30d = past_prices['High'].max()
                current_price = history.loc[actual_entry_ts, 'Close']
                drawdown = ((current_price - high_30d) / high_30d) * 100
                
                if drawdown < -20:
                    skipped_momentum_check += 1
                    pending_trades.remove(trade)
                    continue
            
            entry_price = history.loc[actual_entry_ts, 'Close']
            
            # Calculate position size
            recent_purchase_count = count_recent_insider_purchases(ticker, current_date, all_insider_purchases, days_back=14)
            
            position_multiplier = 1.0
            if recent_purchase_count >= 5:
                position_multiplier = 2.0
            elif recent_purchase_count >= 3:
                position_multiplier = 1.5
            
            for pos in open_positions[ticker]:
                if pd.Timestamp(current_date) in history.index:
                    current_price = history.loc[pd.Timestamp(current_date), 'Close']
                    current_profit_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                    if current_profit_pct > 15:
                        position_multiplier = 0.5
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
    print("FINAL RESULTS - CONSERVATIVE FILTER STRATEGY")
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
    
    print(f"\n📊 CONSERVATIVE FILTER STATS:")
    print(f"   Stocks passing all filters: {len(price_cache)}/50")
    print(f"   Skipped due to >20% drawdown: {skipped_momentum_check}")
    
    print(f"\n{'='*80}\n")
    
    output_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_conservative_filter_results.csv'
    df.to_csv(output_path, index=False)
    print(f"✅ Results saved to: {output_path}")
    
    return closed_trades

if __name__ == '__main__':
    backtest_conservative()
