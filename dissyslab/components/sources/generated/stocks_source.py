import time
import yfinance as yf

class StocksSource:
    def __init__(self, ticker='AAPL', poll_interval=300):
        self.ticker = ticker
        self.poll_interval = poll_interval

    def run(self):
        while True:
            print(f"[Stocks] Fetching {self.ticker}...")
            try:
                stock = yf.Ticker(self.ticker)
                info = stock.fast_info
                
                current_price = info.get('lastPrice', 0)
                previous_close = info.get('previousClose', 0)
                market_cap = info.get('marketCap', 0)
                
                change = current_price - previous_close
                change_percent = (change / previous_close * 100) if previous_close != 0 else 0
                
                text = f"Current Price: ${current_price:.2f}\n"
                text += f"Previous Close: ${previous_close:.2f}\n"
                text += f"Change: ${change:+.2f} ({change_percent:+.2f}%)\n"
                text += f"Market Cap: ${market_cap:,.0f}"
                
                yield {
                    "source": "stocks",
                    "title": f"{self.ticker} Stock Update",
                    "text": text,
                    "url": f"https://finance.yahoo.com/quote/{self.ticker}",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            except Exception as e:
                print(f"[Stocks] Error: {e}")
            
            if self.poll_interval:
                print(f"[Stocks] Sleeping {self.poll_interval}s...")
                time.sleep(self.poll_interval)
            else:
                break

def stocks(ticker='AAPL', poll_interval=300):
    return StocksSource(ticker=ticker, poll_interval=poll_interval)