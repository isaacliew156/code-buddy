# Stock API Guide: Fetching Malaysian Stock Data

> Source: `data/raw/stock-api-guide.md`  
> Last updated: April 8, 2026  
> Script created: April 8, 2026

## Overview

We have implemented a Python script using the yfinance library to fetch Malaysian stock data from Yahoo Finance. The system is capable of retrieving current prices, historical data, and key financial metrics for Malaysian stocks.

## Key Script

### `scripts/get_maybank_price.py`
This script fetches current Maybank (1155.KL) stock price and displays:
- Current price and daily change
- Day's high/low
- 52-week high/low  
- Market capitalization
- Trading volume
- Daily change percentage

**Usage:**
```bash
cd scripts && python get_maybank_price.py
```

**Example output (April 8, 2026):**
```
Maybank (1155.KL) Stock Price:
- Current Price: RM 11.28
- Previous Close: RM 11.16  
- Daily Change: +RM 0.12 (+1.08%)
- Day's Range: RM 11.28 - RM 11.42
- 52-Week Range: RM 9.32 - RM 12.42
- Market Cap: RM 136.44 billion
- Volume: 10,823,900 shares
```

## Malaysian Stock Ticker Format

Malaysian stocks on Yahoo Finance use the format: **`{stock_code}.KL`**

| Company | Stock Code | yfinance Ticker |
|---|---|---|
| Maybank | 1155 | `1155.KL` |
| CIMB Group | 1023 | `1023.KL` |
| Public Bank | 1295 | `1295.KL` |
| Tenaga Nasional | 5347 | `5347.KL` |
| Petronas Chemicals | 5183 | `5183.KL` |
| KLCI Index | — | `^KLSE` |

## Installation Requirements

```bash
uv pip install yfinance
```

Or with pip:
```bash
pip install yfinance
```

## API Usage Patterns

### Basic Single Stock Fetch
```python
import yfinance as yf
import time

ticker = yf.Ticker("1155.KL")
time.sleep(1.5)  # Rate limit protection
info = ticker.info

current_price = info.get('currentPrice')
prev_close = info.get('previousClose')
```

### Historical Data
```python
# Last 1 month of daily data
hist = ticker.history(period="1mo")

# Custom date range  
hist = ticker.history(start="2025-01-01", end="2026-01-01")
```

### Multiple Stocks (Batch)
```python
import yfinance as yf

tickers = ["1155.KL", "1023.KL", "1295.KL", "5347.KL"]
data = yf.download(tickers, period="5d")
print(data['Close'])
```

## Rate Limiting Best Practices

yfinance has no official rate limits but practical guidelines:
- **Delay between calls:** 1–3 seconds (use `time.sleep(1.5)`)
- **Batch when possible:** Use `yf.download()` for multiple stocks
- **Daily limit estimate:** ~2,000 calls/day
- **Error handling:** Catch exceptions and retry with backoff

## Data Limitations

1. **Delayed data:** Malaysian stock data is delayed ~15 minutes
2. **Market hours:** Only available during Bursa Malaysia trading hours (9:00 AM - 5:00 PM MYT)
3. **Field availability:** Not all Yahoo Finance fields are populated for KLSE stocks
4. **Weekends/holidays:** No data available outside trading days

## Extending for Other Stocks

To fetch other Malaysian stocks, modify the script by changing the ticker:

```python
# For CIMB Group
ticker = yf.Ticker("1023.KL")

# For Public Bank  
ticker = yf.Ticker("1295.KL")

# For KLCI Index
ticker = yf.Ticker("^KLSE")
```

## Common Malaysian Stock Codes

| Sector | Company | Ticker |
|---|---|---|
| Banking | Maybank | 1155.KL |
| Banking | CIMB Group | 1023.KL |
| Banking | Public Bank | 1295.KL |
| Banking | Hong Leong Bank | 5819.KL |
| Energy | Tenaga Nasional | 5347.KL |
| Energy | Petronas Gas | 6033.KL |
| Healthcare | IHH Healthcare | 5225.KL |
| Healthcare | KPJ Healthcare | 5878.KL |
| Plantations | Sime Darby Plantation | 5285.KL |
| Plantations | Kuala Lumpur Kepong | 2445.KL |
| Telecommunications | Axiata Group | 6888.KL |
| Telecommunications | Maxis | 6012.KL |
| REITs | KLCC Property | 5235SS.KL |
| REITs | IGB REIT | 5227.KL |

## Troubleshooting

**Error: "No data found"**
- Check if market is open (Bursa Malaysia: 9:00 AM - 5:00 PM MYT)
- Verify ticker format is correct (must end with `.KL`)
- Check internet connection

**Error: Rate limiting**
- Increase delay between calls (`time.sleep(2.0)`)
- Use batch download instead of individual calls
- Implement exponential backoff

**Error: Missing fields**
- Use `.get()` method with default values: `info.get('currentPrice', 'N/A')`
- Some fields may not be available for all KLSE stocks

## References
- Source guide: `data/raw/stock-api-guide.md`
- yfinance documentation: [GitHub](https://github.com/ranaroussi/yfinance)
- Bursa Malaysia: [Website](https://www.bursamalaysia.com)