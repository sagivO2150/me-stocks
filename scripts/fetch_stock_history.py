#!/usr/bin/env python3
"""
Fetch Stock History Data
========================
This script fetches historical stock price data using yfinance for chart visualization.
It returns the last 1 year of daily closing prices along with current price and 24h change.
"""

import yfinance as yf
import sys
import json
from datetime import datetime, timedelta


def fetch_stock_history(ticker_symbol, period="1y"):
    """
    Fetch historical price data for a given ticker.
    
    Args:
        ticker_symbol: Stock ticker (e.g., 'AAPL', 'GME')
        period: Time period for history (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
    
    Returns:
        JSON object with:
        - ticker: Symbol
        - current_price: Latest price
        - change_24h: Price change over last trading day
        - change_24h_pct: Percentage change
        - history: Array of {date, close} objects
        - success: Boolean
        - error: Error message if failed
    """
    try:
        # Create ticker object
        stock = yf.Ticker(ticker_symbol)
        
        # For short periods, use intraday intervals for more data points
        interval_map = {
            '1d': '5m',   # 5-minute intervals for 1 day
            '5d': '15m',  # 15-minute intervals for 5 days
        }
        
        interval = interval_map.get(period, '1d')  # Default to daily data
        
        # Get historical data
        history_data = stock.history(period=period, interval=interval)
        
        if history_data.empty:
            return {
                "success": False,
                "error": f"No data found for ticker: {ticker_symbol}",
                "ticker": ticker_symbol
            }
        
        # Get current price (last close)
        current_price = float(history_data['Close'].iloc[-1])
        
        # Calculate 24h change (comparing last 2 trading days)
        if len(history_data) >= 2:
            previous_price = float(history_data['Close'].iloc[-2])
            change_24h = current_price - previous_price
            change_24h_pct = (change_24h / previous_price) * 100
        else:
            change_24h = 0
            change_24h_pct = 0
        
        # Format history data for chart (Date and Close only)
        history_list = []
        for date, row in history_data.iterrows():
            # For intraday data, include time; for daily data, just date
            if interval in ['5m', '15m', '30m', '1h']:
                date_str = date.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = date.strftime("%Y-%m-%d")
            
            history_list.append({
                "date": date_str,
                "close": float(row['Close']),
                "volume": int(row['Volume'])
            })
        
        # Get additional info
        try:
            info = stock.info
            company_name = info.get('longName', ticker_symbol)
            market_cap = info.get('marketCap', 'N/A')
            pe_ratio = info.get('trailingPE', 'N/A')
        except:
            company_name = ticker_symbol
            market_cap = 'N/A'
            pe_ratio = 'N/A'
        
        return {
            "success": True,
            "ticker": ticker_symbol,
            "company_name": company_name,
            "current_price": round(current_price, 2),
            "change_24h": round(change_24h, 2),
            "change_24h_pct": round(change_24h_pct, 2),
            "market_cap": market_cap,
            "pe_ratio": pe_ratio,
            "history": history_list,
            "period": period
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "ticker": ticker_symbol
        }


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python fetch_stock_history.py <TICKER> [PERIOD]"
        }))
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"
    
    result = fetch_stock_history(ticker, period)
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
