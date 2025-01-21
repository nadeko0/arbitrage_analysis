# config.py
from typing import Dict
from apis import API_KEYS

# Analysis Parameters
MIN_PROFIT_PERCENTAGE = 0.5  # Minimum profit percentage to consider
MAX_TRADE_VOLUME = 1000  # Maximum trade volume in USDT
TARGET_VOLUME = 150  # Target trade volume in USDT

# Update Settings
UPDATE_INTERVAL = 300  # Data refresh interval in seconds

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FILE = "arbitrage_analyzer.log"

# Supported Exchanges
EXCHANGES = ["Binance", "Bitget", "HTX", "OKX", "KuCoin", "Bybit", "MEXC", "GateIo"]

# Exchange Ticker API Endpoints
TICKERS_URLS: Dict[str, str] = {
    "Binance": "https://api.binance.com/api/v3/ticker/bookTicker",
    "Bitget": "https://api.bitget.com/api/spot/v1/market/tickers",
    "HTX": "https://api.huobi.pro/market/tickers",
    "OKX": "https://www.okx.com/api/v5/market/tickers?instType=SPOT",
    "KuCoin": "https://api.kucoin.com/api/v1/market/allTickers",
    "Bybit": "https://api.bybit.com/v5/market/tickers?category=spot",
    "MEXC": "https://api.mexc.com/api/v3/ticker/bookTicker",
    "GateIo": "https://api.gateio.ws/api/v4/spot/tickers",
}

# Trading Interface URLs
TRADE_URLS: Dict[str, str] = {
    "Binance": "https://www.binance.com/en/trade",
    "Bitget": "https://www.bitget.com/spot",
    "HTX": "https://www.htx.com/trade",
    "OKX": "https://www.okx.com/en/trade-spot",
    "KuCoin": "https://www.kucoin.com/en/trade",
    "Bybit": "https://www.bybit.com/en/trade/spot",
    "MEXC": "https://www.mexc.com/en/exchange",
    "GateIo": "https://www.gate.io/en/trade",
}

# Deposit Interface URLs
DEPOSIT_URLS: Dict[str, str] = {
    "Binance": "https://www.binance.com/en/my/wallet/account/main/deposit/crypto",
    "Bitget": "https://www.bitget.com/asset/recharge",
    "HTX": "https://www.htx.com/en-us/finance/deposit",
    "OKX": "https://www.okx.com/en/balance/recharge",
    "KuCoin": "https://www.kucoin.com/en/assets/coin",
    "Bybit": "https://www.bybit.com/user/assets/deposit",
    "MEXC": "https://www.mexc.com/en/assets/deposit",
    "GateIo": "https://www.gate.io/en/myaccount/deposit",
}

# Withdrawal Interface URLs
WITHDRAW_URLS: Dict[str, str] = {
    "Binance": "https://www.binance.com/en/my/wallet/account/main/withdrawal/crypto",
    "Bitget": "https://www.bitget.com/asset/withdraw",
    "HTX": "https://www.htx.com/en-us/finance/withdraw",
    "OKX": "https://www.okx.com/en/balance/withdrawal",
    "KuCoin": "https://www.kucoin.com/en/assets/withdraw",
    "Bybit": "https://www.bybit.com/user/assets/withdraw",
    "MEXC": "https://www.mexc.com/en/assets/withdraw",
    "GateIo": "https://www.gate.io/en/myaccount/withdraw",
}

# Cache Settings
CACHE_EXPIRATION = 60  # Cache lifetime in seconds

# Async Request Configuration
MAX_CONCURRENT_REQUESTS = 10  # Maximum number of concurrent requests
REQUEST_TIMEOUT = 15  # Request timeout in seconds

# Error Handling Settings
MAX_RETRIES = 3  # Maximum number of retry attempts on request failure
RETRY_DELAY = 1  # Delay between retry attempts in seconds

# Testing Configuration
TEST_SYMBOL = "BTCUSDT"  # Symbol to use in tests