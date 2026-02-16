#!/usr/bin/env python3
"""
COMPREHENSIVE BACKTEST ACROSS ALL AVAILABLE INSIDER DATA
Run the conservative filter strategy across all stocks we have insider trading data for.

This simulates a production bot that monitors insider trades and tests how the strategy
would perform "in the wild" with the complete dataset.
"""

import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from multiprocessing import Pool, cpu_count
import sys

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
    except Exception as e:
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

def backtest_all_sec_companies():
    """Backtest conservative strategy across entire SEC dataset"""
    
    print(f"\n{'='*100}")
    print("COMPREHENSIVE BACKTEST - ALL STOCKS WITH INSIDER DATA")
    print(f"{'='*100}\n")
    
    # Load insider trades data
    print("📂 Loading insider trades data...")
    with open('/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/merged_insider_trades.json', 'r') as f:
        insider_data = json.load(f)
    
    print(f"   Total stocks with insider data: {len(insider_data['data']):,}")
    
    # PRE-FILTER: Require 2+ unique insiders
    print("\n🔍 Applying pre-filters...")
    filtered_stocks = []
    single_insider_count = 0
    
    for stock_data in insider_data['data']:
        unique_insiders = stock_data.get('unique_insiders', 0)
        if unique_insiders >= 2:
            filtered_stocks.append(stock_data)
        else:
            single_insider_count += 1
    
    print(f"   ✗ Removed {single_insider_count:,} tickers with <2 insiders")
    print(f"   ✅ After insider filter: {len(filtered_stocks):,}/{len(insider_data['data'])} stocks\n")
    
    tickers_to_fetch = [stock['ticker'] for stock in filtered_stocks]
    
    # Fetch stock data in batches with progress tracking
    print(f"🔄 Loading stock data + market caps for {len(tickers_to_fetch):,} tickers...")
    print(f"   Using {cpu_count()} CPU cores for parallel processing\n")
    
    batch_size = 100
    batches = [tickers_to_fetch[i:i+batch_size] for i in range(0, len(tickers_to_fetch), batch_size)]
    
    all_results = []
    for i, batch in enumerate(batches, 1):
        print(f"   Processing batch {i}/{len(batches)} ({len(batch)} tickers)...", end='\r')
        sys.stdout.flush()
        
        with Pool(cpu_count()) as pool:
            batch_results = pool.map(fetch_ticker_data_with_info, batch)
        all_results.extend(batch_results)
    
    print(f"\n   ✅ Completed fetching {len(all_results):,} tickers\n")
    
    # PRE-FILTER: Market cap > $300M
    price_cache = {}
    market_caps = {}
    low_cap_count = 0
    no_data_count = 0
    
    for ticker, history, market_cap in all_results:
        if history is None:
            no_data_count += 1
            continue
            
        if market_cap > 300_000_000:
            price_cache[ticker] = history
            market_caps[ticker] = market_cap
        else:
            low_cap_count += 1
    
    print(f"   ✗ Removed {low_cap_count:,} tickers with market cap < $300M")
    print(f"   ✗ Removed {no_data_count:,} tickers with no price data")
    print(f"   ✅ After market cap filter: {len(price_cache):,} stocks\n")
    
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
        print("❌ No trades found after filtering!")
        return []
    
    print(f"📈 Total insider purchase signals: {len(all_trades):,}")
    print(f"   Unique tickers with signals: {len(set(t['ticker'] for t in all_trades)):,}\n")
    
    start_date = all_trades[0]['entry_date']
    end_date = '2026-02-13'
    
    print(f"📅 Generating business day calendar ({start_date} to {end_date})...")
    all_business_days = generate_business_days(start_date, end_date)
    print(f"   {len(all_business_days):,} business days\n")
    
    open_positions = defaultdict(list)
    closed_trades = []
    pending_trades = list(all_trades)
    skipped_momentum_check = 0
    skipped_no_price = 0
    
    initial_position_size = 1000
    
    print(f"\n{'='*100}")
    print("RUNNING BACKTEST ACROSS ALL AVAILABLE DATA")
    print(f"{'='*100}\n")
    
    for day_idx, current_date in enumerate(all_business_days):
        # Progress update every 50 days
        if day_idx % 50 == 0:
            total_positions = sum(len(v) for v in open_positions.values())
            print(f"📆 {current_date} | Day {day_idx+1:>4}/{len(all_business_days)} | "
                  f"Open: {total_positions:>3} | Closed: {len(closed_trades):>4} | "
                  f"Skipped: {skipped_momentum_check:>3}")
        
        # Open trades for this date
        trades_to_open = [t for t in pending_trades if t['entry_date'] == current_date]
        
        for trade in trades_to_open:
            ticker = trade['ticker']
            
            if ticker not in price_cache:
                pending_trades.remove(trade)
                skipped_no_price += 1
                continue
            
            history = price_cache[ticker]
            
            current_date_ts = pd.Timestamp(current_date)
            if current_date_ts not in history.index:
                available_dates = sorted([d for d in history.index if d >= current_date_ts])
                if not available_dates:
                    pending_trades.remove(trade)
                    skipped_no_price += 1
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
            
            # Calculate position size based on insider activity
            recent_purchase_count = count_recent_insider_purchases(ticker, current_date, all_insider_purchases, days_back=14)
            
            position_multiplier = 1.0
            if recent_purchase_count >= 5:
                position_multiplier = 2.0
            elif recent_purchase_count >= 3:
                position_multiplier = 1.5
            
            # Check if we already have a winning position
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
                'days_held': 0,
                'market_cap': market_caps.get(ticker, 0)
            }
            
            open_positions[ticker].append(position)
            pending_trades.remove(trade)
        
        # Check all open positions for exit conditions
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
                
                # Track highest price for trailing stop
                if high_price > pos['highest_price']:
                    pos['highest_price'] = high_price
                
                current_profit_pct = ((close_price - pos['entry_price']) / pos['entry_price']) * 100
                
                # Grace period: don't exit in first 5 days
                grace_period = 5
                if pos['days_held'] <= grace_period:
                    continue
                
                # Profit cushion: don't apply stop if we're up >3%
                profit_cushion = 3.0
                if current_profit_pct > profit_cushion:
                    continue
                
                # Dynamic trailing stop loss
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
                        'entry_date': pos['entry_date'],
                        'entry_price': pos['entry_price'],
                        'exit_date': current_date,
                        'exit_price': actual_exit_price,
                        'exit_reason': 'stop_loss',
                        'amount_invested': pos['amount_invested'],
                        'returned_amount': returned_amount,
                        'profit_loss': profit_loss,
                        'return_pct': return_pct,
                        'days_held': pos['days_held'],
                        'highest_price': pos['highest_price'],
                        'market_cap': pos['market_cap']
                    })
                    
                    positions_to_close.append(pos)
            
            for pos in positions_to_close:
                open_positions[ticker].remove(pos)
            
            if not open_positions[ticker]:
                del open_positions[ticker]
    
    # Close remaining positions at end of period
    print(f"\n{'='*100}")
    print("CLOSING REMAINING OPEN POSITIONS")
    print(f"{'='*100}\n")
    
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
                'entry_date': pos['entry_date'],
                'entry_price': pos['entry_price'],
                'exit_date': final_date.strftime('%Y-%m-%d'),
                'exit_price': final_price,
                'exit_reason': 'end_of_period',
                'amount_invested': pos['amount_invested'],
                'returned_amount': returned_amount,
                'profit_loss': profit_loss,
                'return_pct': return_pct,
                'days_held': pos['days_held'],
                'highest_price': pos['highest_price'],
                'market_cap': pos['market_cap']
            })
    
    # COMPREHENSIVE ANALYSIS
    print(f"\n{'='*100}")
    print("COMPREHENSIVE ANALYSIS - ALL AVAILABLE INSIDER DATA")
    print(f"{'='*100}\n")
    
    if not closed_trades:
        print("❌ No trades were executed!")
        return []
    
    df = pd.DataFrame(closed_trades)
    
    # Overall Performance
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
    
    print("📊 OVERALL PERFORMANCE")
    print(f"   Total Trades Executed: {len(df):,}")
    print(f"   Winning Trades: {len(winning_trades):,} ({win_rate:.1f}%)")
    print(f"   Losing Trades: {len(losing_trades):,} ({100-win_rate:.1f}%)")
    print(f"\n   Average Return per Trade: {avg_return:+.2f}%")
    print(f"   Median Return per Trade: {median_return:+.2f}%")
    print(f"   Average Days Held: {avg_days_held:.0f} days")
    print(f"\n💰 PORTFOLIO PERFORMANCE:")
    print(f"   Total Capital Deployed: ${total_invested:,.2f}")
    print(f"   Total Returned: ${total_returned:,.2f}")
    print(f"   Net Profit/Loss: ${total_profit:,.2f}")
    print(f"   Overall ROI: {roi:+.2f}%")
    
    # Distribution Analysis
    print(f"\n📈 RETURN DISTRIBUTION")
    print(f"   Returns > +50%: {len(df[df['return_pct'] > 50]):,} trades")
    print(f"   Returns +20% to +50%: {len(df[(df['return_pct'] > 20) & (df['return_pct'] <= 50)]):,} trades")
    print(f"   Returns +10% to +20%: {len(df[(df['return_pct'] > 10) & (df['return_pct'] <= 20)]):,} trades")
    print(f"   Returns 0% to +10%: {len(df[(df['return_pct'] > 0) & (df['return_pct'] <= 10)]):,} trades")
    print(f"   Returns -10% to 0%: {len(df[(df['return_pct'] > -10) & (df['return_pct'] <= 0)]):,} trades")
    print(f"   Returns < -10%: {len(df[df['return_pct'] <= -10]):,} trades")
    
    # Best and Worst
    best_trade = df.loc[df['return_pct'].idxmax()]
    worst_trade = df.loc[df['return_pct'].idxmin()]
    
    print(f"\n🏆 BEST TRADE")
    print(f"   {best_trade['ticker']} ({best_trade['company']})")
    print(f"   Entry: ${best_trade['entry_price']:.2f} → Exit: ${best_trade['exit_price']:.2f}")
    print(f"   Return: {best_trade['return_pct']:+.1f}% over {int(best_trade['days_held'])} days")
    print(f"   Market Cap: ${best_trade['market_cap']/1e9:.1f}B")
    
    print(f"\n💀 WORST TRADE")
    print(f"   {worst_trade['ticker']} ({worst_trade['company']})")
    print(f"   Entry: ${worst_trade['entry_price']:.2f} → Exit: ${worst_trade['exit_price']:.2f}")
    print(f"   Return: {worst_trade['return_pct']:+.1f}% over {int(worst_trade['days_held'])} days")
    print(f"   Market Cap: ${worst_trade['market_cap']/1e9:.1f}B")
    
    # Funnel Analysis
    print(f"\n🔍 FILTERING FUNNEL")
    print(f"   Total Stocks with Insider Data: {len(insider_data['data']):,}")
    print(f"   → ≥2 Unique Insiders: {len(filtered_stocks):,}")
    print(f"   → Market Cap >$300M: {len(price_cache):,}")
    print(f"   → Generated {len(all_trades):,} trade signals")
    print(f"   → Skipped {skipped_momentum_check:,} due to >20% drawdown")
    print(f"   → Executed {len(df):,} trades")
    
    # Save minimal summary to file
    summary = {
        'total_trades': len(df),
        'win_rate': win_rate,
        'avg_return': avg_return,
        'roi': roi,
        'total_profit': total_profit,
        'unique_tickers_traded': df['ticker'].nunique(),
        'date_range': f"{start_date} to {end_date}"
    }
    
    summary_path = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/sec_dataset_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✅ Summary saved to: {summary_path}")
    print(f"\n{'='*100}\n")
    
    return closed_trades

if __name__ == '__main__':
    backtest_all_sec_companies()
