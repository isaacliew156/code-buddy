#!/usr/bin/env python3
"""
Fetch current Maybank (1155.KL) stock price and key metrics from Yahoo Finance.
This script uses the yfinance library to get real-time (delayed ~15 min) stock data.

Usage:
    python get_maybank_price.py
"""

import yfinance as yf
import time
from datetime import datetime

def format_currency(value):
    """Format a value as Malaysian Ringgit."""
    if value is None:
        return "N/A"
    try:
        return f"RM {value:,.2f}"
    except (TypeError, ValueError):
        return str(value)

def format_number(value):
    """Format large numbers with commas."""
    if value is None:
        return "N/A"
    try:
        return f"{value:,.0f}"
    except (TypeError, ValueError):
        return str(value)

def main():
    print("Fetching Maybank (1155.KL) stock data...")
    
    # Create the ticker object
    ticker = yf.Ticker("1155.KL")
    
    # Add a small delay to respect rate limits
    time.sleep(1.5)
    
    # Get basic info
    info = ticker.info
    
    # Get historical data for today's high/low
    hist = ticker.history(period="1d")
    
    # Get current date and time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\nMaybank (1155.KL) Stock Price - {current_time}")
    print("=" * 60)
    
    # Company name
    company_name = info.get('longName', 'Malayan Banking Berhad')
    print(f"Company:       {company_name}")
    
    # Current price and previous close
    current_price = info.get('currentPrice')
    prev_close = info.get('previousClose')
    
    print(f"Current Price: {format_currency(current_price)}")
    print(f"Prev Close:    {format_currency(prev_close)}")
    
    # Calculate daily change
    if current_price and prev_close and prev_close != 0:
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100
        change_symbol = "+" if change >= 0 else ""
        print(f"Daily Change:  {change_symbol}{format_currency(change)} ({change_symbol}{change_pct:+.2f}%)")
    else:
        print(f"Daily Change:  N/A")
    
    # Day's range
    if not hist.empty:
        day_high = hist['High'].iloc[0] if 'High' in hist.columns else info.get('dayHigh')
        day_low = hist['Low'].iloc[0] if 'Low' in hist.columns else info.get('dayLow')
        print(f"Day's Range:   {format_currency(day_low)} - {format_currency(day_high)}")
    else:
        day_high = info.get('dayHigh')
        day_low = info.get('dayLow')
        print(f"Day's Range:   {format_currency(day_low)} - {format_currency(day_high)}")
    
    # 52-week range
    fifty_two_week_high = info.get('fiftyTwoWeekHigh')
    fifty_two_week_low = info.get('fiftyTwoWeekLow')
    print(f"52-Week Range: {format_currency(fifty_two_week_low)} - {format_currency(fifty_two_week_high)}")
    
    # Volume
    volume = info.get('volume', hist['Volume'].iloc[0] if not hist.empty and 'Volume' in hist.columns else None)
    print(f"Volume:        {format_number(volume)} shares")
    
    # Market cap
    market_cap = info.get('marketCap')
    if market_cap:
        if market_cap >= 1_000_000_000_000:
            market_cap_formatted = f"RM {market_cap/1_000_000_000_000:.2f} trillion"
        elif market_cap >= 1_000_000_000:
            market_cap_formatted = f"RM {market_cap/1_000_000_000:.2f} billion"
        elif market_cap >= 1_000_000:
            market_cap_formatted = f"RM {market_cap/1_000_000:.2f} million"
        else:
            market_cap_formatted = f"RM {market_cap:,.0f}"
    else:
        market_cap_formatted = "N/A"
    
    print(f"Market Cap:    {market_cap_formatted}")
    
    # Currency
    currency = info.get('currency', 'MYR')
    print(f"Currency:      {currency}")
    
    # Additional info if available
    print("\nAdditional Information:")
    print("-" * 30)
    
    # P/E ratio
    pe_ratio = info.get('trailingPE')
    if pe_ratio:
        print(f"P/E Ratio:     {pe_ratio:.2f}")
    
    # Dividend yield
    dividend_yield = info.get('dividendYield')
    if dividend_yield:
        print(f"Dividend Yield: {dividend_yield*100:.2f}%")
    
    # Sector and industry
    sector = info.get('sector')
    industry = info.get('industry')
    if sector:
        print(f"Sector:        {sector}")
    if industry:
        print(f"Industry:      {industry}")
    
    # Market status
    if not hist.empty:
        print(f"Market Status:  Data available")
    else:
        print(f"Market Status:  No data (market may be closed)")
    
    print("\nNote: Malaysian stock data is delayed by ~15 minutes.")
    print("Trading hours: Bursa Malaysia (9:00 AM - 5:00 PM MYT)")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    except Exception as e:
        print(f"\nError fetching Maybank stock data: {e}")
        print("\nPossible issues:")
        print("1. Internet connection problem")
        print("2. Yahoo Finance API issue")
        print("3. Market may be closed (weekend/holiday)")
        print("4. Rate limiting - try again in a few seconds")
        print("\nFor more information, check the stock API guide at data/raw/stock-api-guide.md")