# yfinance API Guide for Malaysian (KLSE) Stocks

> Last verified: April 2026 | yfinance v1.2.1

## 1. Status: Is yfinance Free & Working?

**Yes.** yfinance is free, open-source (Apache 2.0), and actively maintained — v1.2.1 was released April 7, 2026. It wraps Yahoo Finance's public (unofficial) API. No API key needed.

**Caveats:**
- Not officially affiliated with Yahoo — it can break if Yahoo changes endpoints
- Yahoo has tightened rate limits since 2025; aggressive usage triggers `429 Too Many Requests`
- Intended for **personal/educational use only** per Yahoo's terms
- Malaysian stock data is **delayed** (~15 min), not real-time

## 2. Malaysian Stock Ticker Format

Malaysian stocks on Yahoo Finance use the format: **`{stock_code}.KL`**

| Company | Stock Code | yfinance Ticker |
|---|---|---|
| Maybank | 1155 | `1155.KL` |
| CIMB Group | 1023 | `1023.KL` |
| Public Bank | 1295 | `1295.KL` |
| Tenaga Nasional | 5347 | `5347.KL` |
| Petronas Chemicals | 5183 | `5183.KL` |
| Top Glove | 7113 | `7113.KL` |
| IHH Healthcare | 5225 | `5225.KL` |
| Sime Darby | 4197 | `4197.KL` |
| Bursa Malaysia | 1818 | `1818.KL` |
| KLCI Index | — | `^KLSE` |

> **How to find codes:** Search on finance.yahoo.com or check Bursa Malaysia's website for the 4-digit stock code, then append `.KL`.

## 3. Installation

```bash
pip install yfinance
```

## 4. Basic Usage

### Get Current Price & Daily Change

```python
import yfinance as yf

ticker = yf.Ticker("1155.KL")  # Maybank
info = ticker.info

print(f"Name:           {info.get('longName')}")
print(f"Current Price:  RM {info.get('currentPrice')}")
print(f"Previous Close: RM {info.get('previousClose')}")
print(f"Day High:       RM {info.get('dayHigh')}")
print(f"Day Low:        RM {info.get('dayLow')}")
print(f"52-Week High:   RM {info.get('fiftyTwoWeekHigh')}")
print(f"52-Week Low:    RM {info.get('fiftyTwoWeekLow')}")
print(f"Market Cap:     RM {info.get('marketCap')}")
print(f"Currency:       {info.get('currency')}")

# Daily change
current = info.get('currentPrice', 0)
prev = info.get('previousClose', 0)
if prev:
    change = current - prev
    change_pct = (change / prev) * 100
    print(f"Change:         RM {change:+.2f} ({change_pct:+.2f}%)")
```

### Get Historical Data

```python
# Last 1 month of daily data
hist = ticker.history(period="1mo")
print(hist[['Open', 'High', 'Low', 'Close', 'Volume']])

# Custom date range
hist = ticker.history(start="2025-01-01", end="2026-01-01")

# Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
# Valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
```

### Batch Download (Multiple Stocks)

```python
import yfinance as yf

tickers = ["1155.KL", "1023.KL", "1295.KL", "5347.KL"]
data = yf.download(tickers, period="5d")
print(data['Close'])
```

### Get Key Financial Info

```python
ticker = yf.Ticker("1155.KL")

# These may not all be available for KLSE stocks
print(ticker.info.get('trailingPE'))       # P/E ratio
print(ticker.info.get('dividendYield'))    # Dividend yield
print(ticker.info.get('sector'))           # Sector
print(ticker.info.get('industry'))         # Industry
```

## 5. Rate Limits & Best Practices

There are **no officially documented rate limits**, but practical guidelines:

| Guideline | Recommendation |
|---|---|
| Approx daily limit | ~2,000 calls/day (community estimate) |
| Delay between calls | 1–3 seconds (use `time.sleep`) |
| Batch when possible | Use `yf.download(["A","B","C"])` instead of individual calls |
| Cache results | Save to CSV/DB, don't re-fetch unchanged data |
| Error handling | Catch `YFRateLimitError` and retry with exponential backoff |

### Rate-Limit-Safe Pattern

```python
import yfinance as yf
import time
import random

tickers = ["1155.KL", "1023.KL", "1295.KL", "5347.KL", "5183.KL"]
results = {}

for t in tickers:
    try:
        stock = yf.Ticker(t)
        info = stock.info
        results[t] = {
            "name": info.get("longName"),
            "price": info.get("currentPrice"),
            "52wHigh": info.get("fiftyTwoWeekHigh"),
            "52wLow": info.get("fiftyTwoWeekLow"),
        }
    except Exception as e:
        print(f"Error fetching {t}: {e}")
    
    time.sleep(random.uniform(1.0, 3.0))  # polite delay

for t, data in results.items():
    print(f"{data['name']}: RM{data['price']} (52w: {data['52wLow']}-{data['52wHigh']})")
```

## 6. Common Pitfalls

1. **`.info` can be slow** — it fetches a lot of data. If you only need price history, use `.history()` instead.
2. **Some fields return `None`** — not all Yahoo Finance fields are populated for KLSE stocks. Always use `.get()`.
3. **VPN/proxy users** may get blocked more aggressively.
4. **Intraday data** (1m, 5m intervals) is only available for the last 7–60 days depending on interval.
5. **Stock splits/dividends** — `history()` returns adjusted prices by default. Pass `auto_adjust=False` for raw prices.

## 7. Quick Reference for AI Agents

```
TASK: Get Malaysian stock price
STEPS:
  1. pip install yfinance
  2. Ticker format: {4-digit-code}.KL  (e.g. 1155.KL for Maybank)
  3. Index ticker: ^KLSE
  4. Use yf.Ticker("XXXX.KL").info for current snapshot
  5. Use yf.Ticker("XXXX.KL").history(period="1d") for OHLCV
  6. Use yf.download(["A.KL","B.KL"], period="5d") for batch
  7. Add 1-3s delay between individual .info calls
  8. All prices are in MYR, delayed ~15 min
```
