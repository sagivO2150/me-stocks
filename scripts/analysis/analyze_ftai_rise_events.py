#!/usr/bin/env python3
"""
Analyze FTAI stock for rise events between 04/06/2024 and 21/11/2024.
A rise event is defined as a continuous period where the stock price is increasing,
from a local minimum to a local maximum.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import List, Dict
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font


def identify_rise_events(df: pd.DataFrame, min_days: int = 4, min_growth_pct: float = 2.0, min_decline_pct: float = 1.5, min_recovery_pct: float = 2.0) -> List[Dict]:
    """
    Identify rise events in stock price data.
    
    A rise event starts at a local minimum and ends at a local maximum.
    A rise event only ends when there are 2 CONSECUTIVE days of MEANINGFUL decline.
    Small recoveries after declines don't reset the counter - only strong recoveries do.
    
    Args:
        df: DataFrame with Date index and Close prices
        min_days: Minimum number of trading days for a valid rise event (default: 4)
        min_growth_pct: Minimum growth percentage for a valid rise event (default: 2.0%)
        min_decline_pct: Minimum decline percentage per day to count as meaningful dip (default: 1.5%)
        min_recovery_pct: Minimum recovery percentage to reset consecutive dips counter (default: 2.0%)
        
    Returns:
        List of dictionaries containing start_date, end_date, and growth_pct
    """
    rise_events = []
    
    if len(df) < 3:
        return rise_events
    
    # Track the current rise event
    in_rise_event = False
    current_start_idx = None
    current_start_price = None
    peak_idx = None
    peak_price = None
    consecutive_dips = 0
    
    # Track bottom hunting - finding the local minimum after a decline
    hunting_bottom = True
    potential_bottom_idx = 0
    potential_bottom_price = df['Close'].iloc[0]
    
    for i in range(len(df)):
        current_price = df['Close'].iloc[i]
        
        if hunting_bottom:
            # We're looking for a local minimum (bottom)
            # Keep tracking the lowest price
            if current_price <= potential_bottom_price:
                potential_bottom_idx = i
                potential_bottom_price = current_price
            
            # If price starts going up, we found the bottom
            if i > 0 and current_price > df['Close'].iloc[i - 1]:
                # Start a rise event from the bottom
                in_rise_event = True
                hunting_bottom = False
                current_start_idx = potential_bottom_idx
                current_start_price = potential_bottom_price
                peak_idx = i
                peak_price = current_price
                consecutive_dips = 0
            continue
        
        # We're in a rise event - check if price went up or down compared to previous day
        prev_price = df['Close'].iloc[i - 1]
        
        if current_price > prev_price:
            # Price went up - check if it's a meaningful recovery
            recovery_pct = ((current_price - prev_price) / prev_price) * 100
            
            if recovery_pct >= min_recovery_pct:
                # Meaningful recovery - reset consecutive dips counter
                consecutive_dips = 0
            # else: Small recovery after decline - keep counter as is
            
            # Update peak if this is a new high
            if current_price > peak_price:
                peak_idx = i
                peak_price = current_price
                consecutive_dips = 0  # New peak always resets counter
                
        elif current_price < prev_price:
            # Price went down - check if it's a meaningful decline
            decline_pct = ((prev_price - current_price) / prev_price) * 100
            
            if decline_pct >= min_decline_pct:
                # Meaningful decline - increment counter
                consecutive_dips += 1
            # else: Minor dip/plateau - keep counter as is (don't increment, don't reset)
            
            # If we have 2 consecutive dips, end the rise event
            if consecutive_dips >= 2 and peak_idx > current_start_idx:
                start_date = df.index[current_start_idx]
                end_date = df.index[peak_idx]
                growth_pct = ((peak_price - current_start_price) / current_start_price) * 100
                # Count trading days, not calendar days
                days_duration = peak_idx - current_start_idx + 1
                
                # Only add if meets minimum thresholds
                if days_duration >= min_days and growth_pct >= min_growth_pct:
                    rise_events.append({
                        'start_date': start_date.strftime('%Y-%m-%d'),
                        'end_date': end_date.strftime('%Y-%m-%d'),
                        'days': days_duration,
                        'growth_pct': round(growth_pct, 2)
                    })
                
                # Start hunting for the next bottom
                in_rise_event = False
                hunting_bottom = True
                potential_bottom_idx = i
                potential_bottom_price = current_price
                consecutive_dips = 0
        else:
            # Price unchanged - don't increment consecutive dips
            pass
    
    # Handle the last rise event if it's still active at the end
    if in_rise_event and peak_idx is not None and peak_idx > current_start_idx:
        start_date = df.index[current_start_idx]
        end_date = df.index[peak_idx]
        growth_pct = ((peak_price - current_start_price) / current_start_price) * 100
        # Count trading days, not calendar days
        days_duration = peak_idx - current_start_idx + 1
        
        # Only add if meets minimum thresholds
        if days_duration >= min_days and growth_pct >= min_growth_pct:
            rise_events.append({
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'days': days_duration,
                'growth_pct': round(growth_pct, 2)
            })
    
    return rise_events


def main():
    """Main function to analyze FTAI stock and identify rise events."""
    ticker = "FTAI"
    start_date = "2024-06-04"
    end_date = "2025-01-27"
    
    print(f"Fetching {ticker} data from {start_date} to {end_date}...")
    
    try:
        # Fetch stock data
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date)
        
        if df.empty:
            print(f"No data found for {ticker} in the specified date range.")
            return
        
        print(f"Retrieved {len(df)} trading days of data")
        print(f"Date range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
        print(f"Price range: ${df['Close'].min():.2f} to ${df['Close'].max():.2f}")
        print()
        
        # Identify rise events
        rise_events = identify_rise_events(df)
        
        print(f"Found {len(rise_events)} rise events:")
        print()
        
        # Create combined list with rise events and down periods
        combined_events = []
        
        for i, rise_event in enumerate(rise_events):
            # Add the rise event
            combined_events.append({
                'event_type': 'RISE',
                'start_date': rise_event['start_date'],
                'end_date': rise_event['end_date'],
                'days': rise_event['days'],
                'change_pct': rise_event['growth_pct']
            })
            
            # Calculate down period to next rise (if not the last rise event)
            if i < len(rise_events) - 1:
                # Find the dates in the dataframe
                current_end_str = rise_event['end_date']
                next_start_str = rise_events[i + 1]['start_date']
                
                # Get the peak price at end of current rise
                peak_mask = df.index.strftime('%Y-%m-%d') == current_end_str
                peak_price = df.loc[peak_mask, 'Close'].iloc[0]
                
                # Get the bottom price at start of next rise
                bottom_mask = df.index.strftime('%Y-%m-%d') == next_start_str
                bottom_price = df.loc[bottom_mask, 'Close'].iloc[0]
                
                # Calculate decline percentage
                decline_pct = ((peak_price - bottom_price) / peak_price) * 100
                
                # Calculate number of trading days
                peak_idx = df.index[peak_mask][0]
                bottom_idx = df.index[bottom_mask][0]
                down_period_df = df.loc[peak_idx:bottom_idx]
                down_days = len(down_period_df) - 1  # Exclude the start date since it's the peak
                
                if down_days > 0:
                    combined_events.append({
                        'event_type': 'DOWN',
                        'start_date': rise_event['end_date'],
                        'end_date': rise_events[i + 1]['start_date'],
                        'days': down_days,
                        'change_pct': -round(decline_pct, 2)
                    })
        
        # Create DataFrame from combined events
        results_df = pd.DataFrame(combined_events)
        
        if not results_df.empty:
            # Print results
            for idx, event in enumerate(combined_events, 1):
                if event['event_type'] == 'RISE':
                    print(f"{idx}. RISE: {event['start_date']} → {event['end_date']} ({event['days']} days): +{event['change_pct']}%")
                else:
                    print(f"{idx}. DOWN: {event['start_date']} → {event['end_date']} ({event['days']} days): {event['change_pct']}%")
            
            # Save to CSV
            output_file = "output CSVs/ftai_rise_events.csv"
            results_df.to_csv(output_file, index=False)
            print()
            print(f"Results saved to: {output_file}")
            
            # Save to Excel with colors
            excel_file = "output CSVs/ftai_rise_events.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.title = "FTAI Rise Events"
            
            # Define colors
            green_fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
            red_fill = PatternFill(start_color="FFB6C1", end_color="FFB6C1", fill_type="solid")
            header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
            bold_font = Font(bold=True)
            
            # Write headers
            headers = ['Event Type', 'Start Date', 'End Date', 'Days', 'Change %']
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_idx, value=header)
                cell.fill = header_fill
                cell.font = bold_font
            
            # Write data with colors
            for row_idx, event in enumerate(combined_events, 2):
                ws.cell(row=row_idx, column=1, value=event['event_type'])
                ws.cell(row=row_idx, column=2, value=event['start_date'])
                ws.cell(row=row_idx, column=3, value=event['end_date'])
                ws.cell(row=row_idx, column=4, value=event['days'])
                ws.cell(row=row_idx, column=5, value=event['change_pct'])
                
                # Apply color to entire row
                fill = green_fill if event['event_type'] == 'RISE' else red_fill
                for col_idx in range(1, 6):
                    ws.cell(row=row_idx, column=col_idx).fill = fill
            
            # Adjust column widths
            ws.column_dimensions['A'].width = 12
            ws.column_dimensions['B'].width = 12
            ws.column_dimensions['C'].width = 12
            ws.column_dimensions['D'].width = 8
            ws.column_dimensions['E'].width = 10
            
            wb.save(excel_file)
            print(f"Colored Excel file saved to: {excel_file}")
            
            # Summary statistics for rise events only
            rise_only = [e for e in combined_events if e['event_type'] == 'RISE']
            total_growth = sum([e['change_pct'] for e in rise_only])
            avg_growth = total_growth / len(rise_only) if rise_only else 0
            max_growth = max([e['change_pct'] for e in rise_only]) if rise_only else 0
            
            print()
            print("Summary:")
            print(f"Total growth across all rise events: {total_growth:.2f}%")
            print(f"Average growth per rise event: {avg_growth:.2f}%")
            print(f"Maximum single rise event: {max_growth:.2f}%")
        else:
            print("No rise events found in the specified period.")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
