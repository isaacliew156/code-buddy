#!/usr/bin/env python3
"""Fetch current stock price for any ticker using yfinance API.
Usage: python scripts/get_stock_price.py TICKER
Example: python scripts/get_stock_price.py 1023.KL (CIMB)
         python scripts/get_stock_price.py 1155.KL (Maybank)
         python scripts/get_stock_price.py 1295.KL (Public Bank)
"""

import yfinance as yf
import time
import datetime
import sys

def get_stock_price(ticker_symbol):
    """Fetch and display current stock price for given ticker."""
    
    print(f"Fetching stock price for {ticker_symbol}...")
    print("-" * 50)
    
    try:
        # Get the ticker object
        ticker = yf.Ticker(ticker_symbol)
        
        # Fetch info with a small delay to be polite
        time.sleep(1.5)
        info = ticker.info
        
        # Extract key information
        name = info.get('longName', ticker_symbol)
        current_price = info.get('currentPrice')
        prev_close = info.get('previousClose')
        day_high = info.get('dayHigh')
        day_low = info.get('dayLow')
        year_high = info.get('fiftyTwoWeekHigh')
        year_low = info.get('fiftyTwoWeekLow')
        market_cap = info.get('marketCap')
        currency = info.get('currency', 'Unknown')
        
        # Display results
        print(f"Company:        {name}")
        print(f"Ticker:         {ticker_symbol}")
        print(f"Currency:       {currency}")
        print("-" * 50)
        
        if current_price is not None:
            # Format price based on currency
            currency_symbol = "RM" if currency == "MYR" else "$" if currency == "USD" else currency
            print(f"Current Price:  {currency_symbol} {current_price:.2f}")
        else:
            print("Current Price:  Not available (market may be closed)")
            
        if prev_close is not None:
            currency_symbol = "RM" if currency == "MYR" else "$" if currency == "USD" else currency
            print(f"Previous Close: {currency_symbol} {prev_close:.2f}")
            
        # Calculate daily change if we have both current and previous close
        if current_price is not None and prev_close is not None and prev_close != 0:
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100
            currency_symbol = "RM" if currency == "MYR" else "$" if currency == "USD" else currency
            print(f"Daily Change:   {currency_symbol} {change:+.2f} ({change_pct:+.2f}%)")
        
        if day_high is not None:
            currency_symbol = "RM" if currency == "MYR" else "$" if currency == "USD" else currency
            print(f"Day's High:     {currency_symbol} {day_high:.2f}")
            
        if day_low is not None:
            currency_symbol = "RM" if currency == "MYR" else "$" if currency == "USD" else currency
            print(f"Day's Low:      {currency_symbol} {day_low:.2f}")
            
        if year_high is not None:
            currency_symbol = "RM" if currency == "MYR" else "$" if currency == "USD" else currency
            print(f"52-Week High:   {currency_symbol} {year_high:.2f}")
            
        if year_low is not None:
            currency_symbol = "RM" if currency == "MYR" else "$" if currency == "USD" else currency
            print(f"52-Week Low:    {currency_symbol} {year_low:.2f}")
            
        if market_cap is not None:
            # Format market cap in billions
            market_cap_bil = market_cap / 1_000_000_000
            currency_symbol = "RM" if currency == "MYR" else "$" if currency == "USD" else currency
            print(f"Market Cap:     {currency_symbol} {market_cap_bil:.2f}B")
            
        print("-" * 50)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Data fetched at: {current_time}")
        
        # Add note about Malaysian stocks specifically
        if ticker_symbol.endswith('.KL'):
            print("Note: Malaysian stock data is delayed ~15 minutes")
        
        # Also try to get today's trading data
        print("\nFetching today's trading data...")
        try:
            hist = ticker.history(period="1d")
            if not hist.empty:
                currency_symbol = "RM" if currency == "MYR" else "$" if currency == "USD" else currency
                print(f"Open:           {currency_symbol} {hist['Open'].iloc[-1]:.2f}")
                print(f"Close:          {currency_symbol} {hist['Close'].iloc[-1]:.2f}")
                if 'Volume' in hist.columns:
                    volume = hist['Volume'].iloc[-1]
                    print(f"Volume:         {volume:,.0f} shares")
        except Exception as e:
            print(f"Could not fetch historical data: {e}")
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        print("Please check your internet connection and try again.")

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nError: Please provide a ticker symbol.")
        print("Example: python scripts/get_stock_price.py 1023.KL")
        return 1
    
    ticker_symbol = sys.argv[1].upper()
    
    # Validate the ticker format
    if not ticker_symbol:
        print("Error: Ticker symbol cannot be empty.")
        return 1
    
    get_stock_price(ticker_symbol)
    return 0

if __name__ == "__main__":
    sys.exit(main())