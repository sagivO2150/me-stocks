#!/usr/bin/env python3
"""
Generate PDF Report with Stock Charts and Backtest Results
===========================================================
This script creates a visual PDF report showing:
1. Stock price charts from the webapp's "All Charts" view
2. Overlay of buy/sell signals from backtest results
3. Performance metrics for each stock
"""

import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys

# Color scheme matching the webapp
COLORS = {
    'background': '#1e293b',  # slate-800
    'chart_bg': '#0f172a',    # slate-900
    'grid': '#334155',        # slate-700
    'price_line': '#8b5cf6',  # purple-500 (neutral for price)
    'price_fill': '#6366f1',  # indigo-500 (neutral for price fill)
    'purchase': '#22c55e',    # bright green for profitable trades
    'sale': '#ef4444',        # bright red for losing trades
    'text': '#ffffff',
    'text_secondary': '#94a3b8'  # slate-400
}


def load_backtest_results(csv_path):
    """Load backtest results from CSV and normalize columns"""
    df = pd.read_csv(csv_path)
    
    # Normalize column names across different backtest strategies
    # Some strategies use different column names, so we standardize them
    column_mapping = {
        'exit_price_weighted': 'exit_price',  # Smart strategy uses weighted exit
        'tranche1_exit': 'return_pct',  # Alternative return column
    }
    
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns and new_col not in df.columns:
            df[new_col] = df[old_col]
    
    # Ensure required columns exist
    required_cols = ['ticker', 'entry_date', 'entry_price']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"⚠️  Warning: Missing columns: {missing_cols}")
    
    # Handle profit_loss calculation if missing
    if 'profit_loss' not in df.columns and 'return_pct' in df.columns and 'amount_invested' in df.columns:
        df['profit_loss'] = df['amount_invested'] * (df['return_pct'] / 100)
    elif 'profit_loss' not in df.columns:
        df['profit_loss'] = 0  # Default
    
    # Handle company name if missing
    if 'company' not in df.columns:
        df['company'] = df['ticker']  # Use ticker as fallback
    
    print(f"📊 Loaded {len(df)} trades from backtest results")
    return df


def load_monthly_trades(json_path):
    """Load monthly insider trades data"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    print(f"📈 Loaded {len(data)} stocks from monthly trades")
    return data


def get_stock_data(ticker, period='1y'):
    """Fetch stock price data"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        info = stock.info
        company_name = info.get('longName', ticker)
        return hist, company_name
    except Exception as e:
        print(f"⚠️  Error fetching {ticker}: {e}")
        return None, ticker


def create_chart_with_trades(ax, ticker, stock_data, backtest_trades, company_name):
    """Create a single stock chart with colored trade lines (green=profit, red=loss)"""
    
    # Plot price line
    dates = stock_data.index
    prices = stock_data['Close']
    
    # Determine if stock is up or down (for stats, not color)
    first_price = prices.iloc[0]
    last_price = prices.iloc[-1]
    price_change_pct = ((last_price - first_price) / first_price) * 100
    
    # Use neutral purple/indigo colors for price to avoid conflict with trade lines
    ax.fill_between(dates, prices, alpha=0.2, color=COLORS['price_fill'])
    ax.plot(dates, prices, color=COLORS['price_line'], linewidth=1.5, alpha=0.8, label='Price')
    
    # Convert stock_data index to date-only strings for comparison
    stock_dates = pd.to_datetime(stock_data.index).date
    stock_dates_map = {d: stock_data.index[i] for i, d in enumerate(stock_dates)}
    
    # Track if we've added labels
    profit_label_added = False
    loss_label_added = False
    
    # Draw trade lines from backtest
    for idx, trade in backtest_trades.iterrows():
        try:
            # Entry date/price
            entry_date_str = pd.to_datetime(trade['entry_date']).date()
            entry_price = float(trade['entry_price'])
            
            # Find the matching or nearest date in stock data
            entry_stock_date = None
            if entry_date_str in stock_dates_map:
                entry_stock_date = stock_dates_map[entry_date_str]
            else:
                # Find nearest date within 5 days
                for offset in range(-5, 6):
                    check_date = entry_date_str + timedelta(days=offset)
                    if check_date in stock_dates_map:
                        entry_stock_date = stock_dates_map[check_date]
                        break
            
            # Exit date/price
            if pd.notna(trade.get('exit_date')) and entry_stock_date is not None:
                exit_date_str = pd.to_datetime(trade['exit_date']).date()
                exit_price = float(trade['exit_price'])
                
                # Find the matching or nearest date
                exit_stock_date = None
                if exit_date_str in stock_dates_map:
                    exit_stock_date = stock_dates_map[exit_date_str]
                else:
                    # Find nearest date within 5 days
                    for offset in range(-5, 6):
                        check_date = exit_date_str + timedelta(days=offset)
                        if check_date in stock_dates_map:
                            exit_stock_date = stock_dates_map[check_date]
                            break
                
                if exit_stock_date is not None:
                    # Determine line color based on profit/loss
                    is_profit = trade['return_pct'] > 0
                    line_color = COLORS['purchase'] if is_profit else COLORS['sale']
                    
                    # Draw trade line from entry to exit
                    label = None
                    if is_profit and not profit_label_added:
                        label = f'Profitable Trade'
                        profit_label_added = True
                    elif not is_profit and not loss_label_added:
                        label = f'Losing Trade'
                        loss_label_added = True
                    
                    ax.plot([entry_stock_date, exit_stock_date], 
                           [entry_price, exit_price], 
                           color=line_color, 
                           linewidth=2.5, 
                           alpha=1.0,
                           label=label,
                           solid_capstyle='round')
        
        except Exception as e:
            print(f"  ⚠️  Could not plot trade {idx} for {ticker}: {e}")
            continue
    
    # Formatting
    ax.set_facecolor(COLORS['chart_bg'])
    ax.grid(True, alpha=0.3, color=COLORS['grid'], linestyle='--')
    ax.set_xlabel('Date', color=COLORS['text_secondary'], fontsize=10)
    ax.set_ylabel('Price ($)', color=COLORS['text_secondary'], fontsize=10)
    
    # Title with company info and performance
    title = f"{ticker} - {company_name}\n"
    title += f"Current: ${last_price:.2f} | Period Change: {price_change_pct:+.2f}%"
    ax.set_title(title, color=COLORS['text'], fontsize=12, fontweight='bold', pad=10)
    
    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', color=COLORS['text_secondary'])
    plt.setp(ax.yaxis.get_majorticklabels(), color=COLORS['text_secondary'])
    
    # Legend
    if len(backtest_trades) > 0:
        ax.legend(loc='upper left', fontsize=9, facecolor=COLORS['background'], 
                 edgecolor=COLORS['grid'], labelcolor=COLORS['text'])


def create_summary_page(pdf, all_trades):
    """Create a summary page with overall statistics"""
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor(COLORS['background'])
    ax = fig.add_subplot(111)
    ax.axis('off')
    
    # Title
    title_text = "Backtest Strategy Results\nSummary Report"
    ax.text(0.5, 0.95, title_text, ha='center', va='top', 
           fontsize=24, fontweight='bold', color=COLORS['text'])
    
    # Date
    date_text = f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    ax.text(0.5, 0.88, date_text, ha='center', va='top', 
           fontsize=12, color=COLORS['text_secondary'])
    
    # Calculate statistics
    total_trades = len(all_trades)
    winning_trades = len(all_trades[all_trades['return_pct'] > 0])
    losing_trades = len(all_trades[all_trades['return_pct'] <= 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    avg_return = all_trades['return_pct'].mean()
    total_profit = all_trades['profit_loss'].sum()
    total_invested = all_trades['amount_invested'].sum()
    total_returned = all_trades['returned_amount'].sum()
    roi = (total_profit / total_invested * 100) if total_invested > 0 else 0
    
    best_trade = all_trades.loc[all_trades['return_pct'].idxmax()]
    worst_trade = all_trades.loc[all_trades['return_pct'].idxmin()]
    
    # Statistics text
    y_pos = 0.75
    stats = [
        ("📊 OVERALL PERFORMANCE", ""),
        ("", ""),
        ("Total Trades:", f"{total_trades}"),
        ("Winning Trades:", f"{winning_trades} ({win_rate:.1f}%)"),
        ("Losing Trades:", f"{losing_trades} ({100-win_rate:.1f}%)"),
        ("", ""),
        ("Average Return:", f"{avg_return:+.2f}%"),
        ("Total Invested:", f"${total_invested:,.2f}"),
        ("Total Returned:", f"${total_returned:,.2f}"),
        ("Net Profit/Loss:", f"${total_profit:,.2f}"),
        ("ROI:", f"{roi:+.2f}%"),
        ("", ""),
        ("🏆 BEST TRADE", ""),
        ("Ticker:", f"{best_trade['ticker']} ({best_trade['company']})"),
        ("Return:", f"{best_trade['return_pct']:+.1f}%"),
        ("Profit:", f"${best_trade['profit_loss']:,.2f}"),
        ("", ""),
        ("💀 WORST TRADE", ""),
        ("Ticker:", f"{worst_trade['ticker']} ({worst_trade['company']})"),
        ("Return:", f"{worst_trade['return_pct']:+.1f}%"),
        ("Loss:", f"${worst_trade['profit_loss']:,.2f}"),
    ]
    
    for label, value in stats:
        if label == "":  # Spacer
            y_pos -= 0.02
            continue
            
        if label.startswith("📊") or label.startswith("🏆") or label.startswith("💀"):
            # Section header
            ax.text(0.5, y_pos, label, ha='center', va='top', 
                   fontsize=16, fontweight='bold', color=COLORS['purchase'])
            y_pos -= 0.045
        else:
            # Data row
            ax.text(0.3, y_pos, label, ha='right', va='top', 
                   fontsize=12, color=COLORS['text_secondary'])
            
            # Color code positive/negative values
            value_color = COLORS['text']
            if value and ('+' in value or '-' in value):
                value_color = COLORS['purchase'] if '+' in value else COLORS['sale']
            
            ax.text(0.35, y_pos, value, ha='left', va='top', 
                   fontsize=12, fontweight='bold', color=value_color)
            y_pos -= 0.035
    
    pdf.savefig(fig, facecolor=COLORS['background'])
    plt.close(fig)


def generate_pdf_report(backtest_csv, monthly_json, output_pdf, period='1y'):
    """Generate the full PDF report"""
    
    print("🎨 Starting PDF generation...")
    print("=" * 80)
    
    # Load data
    backtest_df = load_backtest_results(backtest_csv)
    monthly_stocks = load_monthly_trades(monthly_json)
    
    # Get unique tickers from backtest
    tickers = backtest_df['ticker'].unique()
    print(f"\n📋 Processing {len(tickers)} unique stocks...")
    
    # Create PDF
    with PdfPages(output_pdf) as pdf:
        # Summary page first
        print("\n📄 Creating summary page...")
        create_summary_page(pdf, backtest_df)
        
        # Create a chart for each stock
        for i, ticker in enumerate(tickers, 1):
            print(f"\n[{i}/{len(tickers)}] Processing {ticker}...")
            
            # Get trades for this ticker
            ticker_trades = backtest_df[backtest_df['ticker'] == ticker]
            
            # Fetch stock data
            stock_data, company_name = get_stock_data(ticker, period=period)
            
            if stock_data is None or stock_data.empty:
                print(f"  ⚠️  Skipping {ticker} - no data available")
                continue
            
            # Create figure
            fig, ax = plt.subplots(figsize=(11, 8.5))
            fig.patch.set_facecolor(COLORS['background'])
            
            # Create chart
            create_chart_with_trades(ax, ticker, stock_data, ticker_trades, company_name)
            
            # Add trade statistics box
            total_return = ticker_trades['return_pct'].sum()
            num_trades = len(ticker_trades)
            avg_return = ticker_trades['return_pct'].mean()
            total_profit = ticker_trades['profit_loss'].sum()
            
            stats_text = f"Trades: {num_trades} | Avg: {avg_return:+.1f}% | Total: {total_return:+.1f}% | P/L: ${total_profit:,.0f}"
            fig.text(0.5, 0.02, stats_text, ha='center', fontsize=10, 
                    color=COLORS['text'], fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor=COLORS['background'], 
                             edgecolor=COLORS['grid'], linewidth=1))
            
            plt.tight_layout(rect=[0, 0.03, 1, 1])
            pdf.savefig(fig, facecolor=COLORS['background'])
            plt.close(fig)
            
            print(f"  ✅ {ticker} chart completed ({num_trades} trades, {total_return:+.1f}% return)")
        
        # PDF metadata
        d = pdf.infodict()
        d['Title'] = 'Backtest Strategy Results - Chart Report'
        d['Author'] = 'Insider Trading Tracker'
        d['Subject'] = f'Visual analysis of backtest results for {len(tickers)} stocks'
        d['Keywords'] = 'Backtest, Trading, Insider, Strategy, Performance'
        d['CreationDate'] = datetime.now()
    
    print("\n" + "=" * 80)
    print(f"✅ PDF report generated successfully!")
    print(f"📁 Saved to: {output_pdf}")
    print(f"📊 Total pages: {len(tickers) + 1} (1 summary + {len(tickers)} charts)")
    print("=" * 80)


if __name__ == '__main__':
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate PDF report from backtest results')
    parser.add_argument('--strategy', type=str, default='card_counting',
                       choices=['card_counting', 'smart_strategy', 'trailing_stop', 'peak_purchase'],
                       help='Which backtest strategy results to visualize')
    parser.add_argument('--period', type=str, default='1y',
                       choices=['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'],
                       help='Time period for stock charts')
    args = parser.parse_args()
    
    # Map strategy names to file names
    strategy_files = {
        'card_counting': 'backtest_card_counting_results.csv',
        'smart_strategy': 'backtest_smart_strategy_results.csv',
        'trailing_stop': 'backtest_trailing_stop_results.csv',
        'peak_purchase': 'backtest_results.csv'  # Original backtest
    }
    
    # File paths
    base_dir = Path('/Users/sagiv.oron/Documents/scripts_playground/stocks')
    backtest_csv = base_dir / 'output CSVs' / strategy_files[args.strategy]
    monthly_json = base_dir / 'output CSVs' / 'top_monthly_insider_trades.json'
    output_pdf = base_dir / 'output CSVs' / f'backtest_{args.strategy}_visual_report.pdf'
    
    # Check if files exist
    if not backtest_csv.exists():
        print(f"❌ Error: Backtest CSV not found at {backtest_csv}")
        print(f"💡 Run the backtest first: python scripts/tests/backtest_{args.strategy}_strategy.py")
        sys.exit(1)
    
    if not monthly_json.exists():
        print(f"❌ Error: Monthly trades JSON not found at {monthly_json}")
        sys.exit(1)
    
    print(f"🎯 Generating PDF for strategy: {args.strategy.upper()}")
    print(f"📊 Period: {args.period}")
    print()
    
    # Generate report
    generate_pdf_report(
        backtest_csv=str(backtest_csv),
        monthly_json=str(monthly_json),
        output_pdf=str(output_pdf),
        period=args.period
    )
