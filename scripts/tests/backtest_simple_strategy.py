#!/usr/bin/env python3
"""
Simple Insider Trading Strategy
================================
Rules:
1. Buy on every insider purchase event with 5% TRAILING stop loss
2. If already holding the stock, DON'T re-buy on new insider events
3. Close all positions at end of period
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


def get_price_at_date(ticker, target_date, days_forward=5):
    """Get stock price on or after target date"""
    try:
        ticker_data = PRICE_CACHE.get(ticker)
        if ticker_data is None or ticker_data.empty:
            return None
        
        target = pd.Timestamp(target_date).tz_localize(None)  # Remove timezone for comparison
        ticker_data_no_tz = ticker_data.copy()
        ticker_data_no_tz.index = ticker_data_no_tz.index.tz_localize(None)  # Remove timezone from index
        
        # Try to find price on exact date or within next few days
        for i in range(days_forward):
            check_date = target + pd.Timedelta(days=i)
            if check_date in ticker_data_no_tz.index:
                return ticker_data_no_tz.loc[check_date, 'Close']
        
        # If not found, get closest future price
        future_prices = ticker_data_no_tz[ticker_data_no_tz.index >= target]
        if not future_prices.empty:
            return future_prices.iloc[0]['Close']
        
        return None
    except Exception as e:
        return None


def get_current_price(ticker):
    """Get most recent price"""
    try:
        ticker_data = PRICE_CACHE.get(ticker)
        if ticker_data is None or ticker_data.empty:
            return None
        return float(ticker_data.iloc[-1]['Close'])
    except:
        return None


def apply_trailing_stop(position, end_date, stop_loss_pct):
    """
    Check daily prices from last_checked_date to end_date for trailing stop loss.
    Returns: (closed_trade_dict or None, updated_position)
    """
    ticker = position['ticker']
    history = PRICE_CACHE.get(ticker)
    if history is None or history.empty:
        return None, position

    hist = history.copy()
    if getattr(hist.index, 'tz', None) is not None:
        hist.index = hist.index.tz_localize(None)

    start_ts = pd.Timestamp(position['last_checked_date'])
    end_ts = pd.Timestamp(end_date)
    if end_ts <= start_ts:
        return None, position
    window = hist[(hist.index > start_ts) & (hist.index <= end_ts)]

    for date, row in window.iterrows():
        high_price = float(row['High'])
        low_price = float(row['Low'])

        if high_price > position['highest_price']:
            position['highest_price'] = high_price

        trailing_stop_price = position['highest_price'] * (1 - stop_loss_pct / 100)

        if low_price <= trailing_stop_price:
            exit_date = date.strftime('%Y-%m-%d')
            exit_price = trailing_stop_price
            return_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
            returned_amount = position['amount_invested'] * (1 + return_pct / 100)

            closed_trade = {
                'ticker': position['ticker'],
                'company': position['company'],
                'entry_date': position['entry_date'],
                'entry_price': position['entry_price'],
                'exit_date': exit_date,
                'exit_price': exit_price,
                'shares': position['shares'],
                'amount_invested': position['amount_invested'],
                'returned_amount': returned_amount,
                'profit_loss': returned_amount - position['amount_invested'],
                'return_pct': return_pct,
                'exit_reason': 'stop_loss',
                'insider_name': position['insider_name'],
                'insider_value': position['insider_value'],
                'peak_price': position['highest_price']
            }

            return closed_trade, None

    position['last_checked_date'] = end_date
    return None, position


# Global cache for price data
PRICE_CACHE = {}


def backtest_simple_strategy(json_file, position_size=1000, stop_loss_pct=5.0):
    """
    Backtest simple strategy: buy once per insider event, don't re-buy if holding
    """
    
    # Load the data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    stocks = data['data']
    
    print("\nPre-loading historical data for all tickers...")

    earliest_trade_by_ticker = {}
    for stock in stocks:
        ticker = stock['ticker']
        for trade in stock['trades']:
            trade_date = trade['trade_date']
            if ticker not in earliest_trade_by_ticker or trade_date < earliest_trade_by_ticker[ticker]:
                earliest_trade_by_ticker[ticker] = trade_date

    for stock in stocks:
        ticker = stock['ticker']
        try:
            start_date = earliest_trade_by_ticker.get(ticker)
            if start_date:
                start_dt = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
                end_dt = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                hist = yf.Ticker(ticker).history(start=start_dt, end=end_dt)
            else:
                hist = yf.Ticker(ticker).history(period='1y')
            if not hist.empty:
                PRICE_CACHE[ticker] = hist
                print(f"  ✓ {ticker}")
            else:
                print(f"  ✗ {ticker} (no data)")
        except Exception as e:
            print(f"  ✗ {ticker} ({str(e)[:30]})")
    
    print(f"\nLoaded data for {len(PRICE_CACHE)} tickers\n")
    
    # Track all insider events chronologically
    all_events = []
    
    for stock in stocks:
        ticker = stock['ticker']
        company = stock.get('company_name', ticker)
        
        if ticker not in PRICE_CACHE:
            continue
        
        for trade in stock['trades']:
            all_events.append({
                'ticker': ticker,
                'company': company,
                'date': trade['trade_date'],
                'insider_name': trade['insider_name'],
                'value': parse_value(trade.get('value', '')),
                'shares': trade.get('qty', trade.get('shares', ''))
            })
    
    # Sort by date
    all_events.sort(key=lambda x: x['date'])
    
    print(f"Total insider events to process: {len(all_events)}")
    if all_events:
        print(f"Date range: {all_events[0]['date']} to {all_events[-1]['date']}\n")
    
    print("=" * 80)
    print("SIMPLE INSIDER STRATEGY BACKTEST")
    print("=" * 80)
    print("Rules:")
    print("  - Buy on every insider purchase event")
    print("  - 5% TRAILING stop loss on all positions")
    print("  - Trailing stop follows highest price reached")
    print("  - DON'T re-buy if already holding the stock")
    print(f"  - Position size: ${position_size:,.0f}")
    print("=" * 80)
    print()
    
    # Track open positions
    open_positions = {}  # ticker -> {entry_date, entry_price, shares, amount_invested}
    closed_trades = []
    
    # Process each insider event
    skipped_no_price = 0
    skipped_already_holding = 0
    
    for event in all_events:
        ticker = event['ticker']
        trade_date = event['date']

        # Get entry price (2 business days after insider trade)
        entry_date = get_business_days_later(trade_date, 2)

        # Update trailing stop for all open positions up to this event date
        positions_to_close = []
        for pos_ticker, pos in list(open_positions.items()):
            closed_trade, updated_pos = apply_trailing_stop(pos, entry_date, stop_loss_pct)
            if closed_trade:
                print(f"📉 STOP LOSS {pos_ticker}: ${pos['entry_price']:.2f} → ${closed_trade['exit_price']:.2f} = {closed_trade['return_pct']:.1f}%")
                closed_trades.append(closed_trade)
                positions_to_close.append(pos_ticker)
            else:
                open_positions[pos_ticker] = updated_pos

        for pos_ticker in positions_to_close:
            del open_positions[pos_ticker]
        
        entry_price = get_price_at_date(ticker, entry_date)
        
        if entry_price is None:
            skipped_no_price += 1
            continue
        
        # Check if we're already holding this stock
        if ticker in open_positions:
            # Skip - we don't re-buy if already holding
            skipped_already_holding += 1
            continue
        
        # Open new position
        shares = position_size / entry_price
        open_positions[ticker] = {
            'ticker': ticker,
            'entry_date': entry_date,
            'entry_price': entry_price,
            'shares': shares,
            'amount_invested': position_size,
            'company': event['company'],
            'insider_name': event['insider_name'],
            'insider_value': event['value'],
            'highest_price': entry_price,
            'last_checked_date': entry_date
        }
        
        print(f"💰 BUY {ticker} @ ${entry_price:.2f} on {entry_date}")
    
    print(f"\n📊 Events skipped - no price: {skipped_no_price}, already holding: {skipped_already_holding}")
    
    # Close remaining positions at current price
    print("\n" + "=" * 80)
    print("CLOSING REMAINING OPEN POSITIONS")
    print("=" * 80)
    
    for ticker, pos in open_positions.items():
        history = PRICE_CACHE.get(ticker)
        if history is None or history.empty:
            continue

        hist = history.copy()
        if getattr(hist.index, 'tz', None) is not None:
            hist.index = hist.index.tz_localize(None)

        last_date = hist.index.max().strftime('%Y-%m-%d')

        closed_trade, updated_pos = apply_trailing_stop(pos, last_date, stop_loss_pct)
        if closed_trade:
            status = "✅" if closed_trade['profit_loss'] >= 0 else "❌"
            print(f"{status} CLOSED {ticker}: ${pos['entry_price']:.2f} → ${closed_trade['exit_price']:.2f} = {closed_trade['return_pct']:+.1f}%")
            closed_trades.append(closed_trade)
            continue

        exit_price = get_current_price(ticker)
        if exit_price is None:
            continue
        
        exit_date = datetime.now().strftime('%Y-%m-%d')
        return_pct = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100
        returned_amount = pos['amount_invested'] * (1 + return_pct / 100)
        profit_loss = returned_amount - pos['amount_invested']
        
        status = "✅" if profit_loss >= 0 else "❌"
        print(f"{status} CLOSED {ticker}: ${pos['entry_price']:.2f} → ${exit_price:.2f} = {return_pct:+.1f}%")
        
        closed_trades.append({
            'ticker': ticker,
            'company': pos['company'],
            'entry_date': pos['entry_date'],
            'entry_price': pos['entry_price'],
            'exit_date': exit_date,
            'exit_price': exit_price,
            'shares': pos['shares'],
            'amount_invested': pos['amount_invested'],
            'returned_amount': returned_amount,
            'profit_loss': profit_loss,
            'return_pct': return_pct,
            'exit_reason': 'end_of_period',
            'insider_name': pos['insider_name'],
            'insider_value': pos['insider_value'],
            'peak_price': pos.get('highest_price', pos['entry_price'])
        })
    
    # Print summary
    if closed_trades:
        print("\n" + "=" * 80)
        print("FINAL RESULTS")
        print("=" * 80)
        
        winning_trades = [t for t in closed_trades if t['profit_loss'] > 0]
        losing_trades = [t for t in closed_trades if t['profit_loss'] <= 0]
        
        total_invested = sum(t['amount_invested'] for t in closed_trades)
        total_returned = sum(t['returned_amount'] for t in closed_trades)
        net_profit = total_returned - total_invested
        
        print(f"\nTotal Trades: {len(closed_trades)}")
        print(f"  Winning: {len(winning_trades)} ({len(winning_trades)/len(closed_trades)*100:.1f}%)")
        print(f"  Losing: {len(losing_trades)} ({len(losing_trades)/len(closed_trades)*100:.1f}%)")
        
        avg_return = sum(t['return_pct'] for t in closed_trades) / len(closed_trades)
        print(f"\nAverage Return per Trade: {avg_return:+.2f}%")
        
        print(f"\n💰 PORTFOLIO PERFORMANCE:")
        print(f"   Total Invested: ${total_invested:,.2f}")
        print(f"   Total Returned: ${total_returned:,.2f}")
        print(f"   Net Profit/Loss: ${net_profit:,.2f}")
        print(f"   ROI: {(net_profit / total_invested * 100):+.2f}%")
        
        # Best and worst
        best = max(closed_trades, key=lambda x: x['return_pct'])
        worst = min(closed_trades, key=lambda x: x['return_pct'])
        
        print(f"\n🏆 Best Trade: {best['ticker']} - {best['return_pct']:+.1f}%")
        print(f"   ${best['entry_price']:.2f} → ${best['exit_price']:.2f}")
        print(f"   Profit: ${best['profit_loss']:,.2f}")
        
        print(f"\n💀 Worst Trade: {worst['ticker']} - {worst['return_pct']:+.1f}%")
        print(f"   ${worst['entry_price']:.2f} → ${worst['exit_price']:.2f}")
        print(f"   Loss: ${worst['profit_loss']:,.2f}")
    
    print("\n" + "=" * 80 + "\n")
    
    return closed_trades


if __name__ == '__main__':
    json_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/full_history_insider_trades.json'
    
    results = backtest_simple_strategy(
        json_file=json_file,
        position_size=1000,
        stop_loss_pct=5.0
    )
    
    # Save results
    if results:
        import csv
        output_file = '/Users/sagiv.oron/Documents/scripts_playground/stocks/output CSVs/backtest_simple_results.csv'
        
        all_fields = set()
        for result in results:
            all_fields.update(result.keys())
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(all_fields))
            writer.writeheader()
            writer.writerows(results)
        
        print(f"✅ Results saved to: {output_file}")
