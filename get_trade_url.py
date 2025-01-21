import logging
from typing import Optional

import logging_config, config

# Get the logger
logger = logging.getLogger("get_trade_url")

quote_currencies = [
    "USDT", "USD", "EUR", "USDC", "BTC", "ETH", "BUSD", "DAI", "GBP", "AUD", 
    "JPY", "KRW", "RUB", "TRY", "CNY", "SGD", "HKD", "CAD", "CHF", "NZD"
]

def get_spot_trade_url(exchange: str, symbol: str) -> Optional[str]:
    # logger.debug(f"Attempting to get URL for exchange: {exchange}, symbol: {symbol}")

    quote_symbol = next((quote for quote in quote_currencies if symbol.endswith(quote)), None)
    if not quote_symbol:
        logger.error(f"Could not find corresponding currency for symbol {symbol}.")
        return None

    base_symbol = symbol[: -len(quote_symbol)]

    if exchange not in config.TRADE_URLS:
        logger.error(f"Exchange {exchange} is not supported.")
        return None

    url_formats = {
        "Binance": f"{config.TRADE_URLS[exchange]}/{base_symbol}_{quote_symbol}?type=spot",
        "Bitget": f"{config.TRADE_URLS[exchange]}/{base_symbol}{quote_symbol}?type=spot",
        "HTX": f"{config.TRADE_URLS[exchange]}/{base_symbol.casefold()}_{quote_symbol.casefold()}?type=spot",
        "OKX": f"{config.TRADE_URLS[exchange]}/{base_symbol.casefold()}-{quote_symbol.casefold()}",
        "KuCoin": f"{config.TRADE_URLS[exchange]}/{base_symbol}-{quote_symbol}",
        "Bybit": f"{config.TRADE_URLS[exchange]}/{base_symbol}/{quote_symbol}",
        "MEXC": f"{config.TRADE_URLS[exchange]}/{base_symbol}_{quote_symbol}",
        "GateIo": f"{config.TRADE_URLS[exchange]}/{base_symbol}_{quote_symbol}", 
    }

    url = url_formats.get(exchange)
    if url:
        # logger.info(f"Successfully got URL for exchange: {exchange}, symbol: {symbol}")
        return url
    else:
        logger.error(f"Unexpected error occurred while generating URL for {exchange}.")
        return None
