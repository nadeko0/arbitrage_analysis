import aiohttp
import asyncio
import time
import logging
from typing import Dict, List, Any, Optional

# Import logging configuration
import logging_config

# Get the logger
logger = logging.getLogger("collect_ordersbooks")
time_logger = logging.getLogger("time_analysis")

async def fetch_orderbook(session, url, headers=None):
    headers = headers or {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    start_time = time.time()
    try:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            try:
                data = await response.json()
                duration = time.time() - start_time
                logger.info(f"Fetched data from URL: {url} in {duration:.2f} seconds")
                logger.debug(f"Response status: {response.status}, Content-Type: {response.headers.get('Content-Type')}")
                return data
            except aiohttp.ContentTypeError:
                logger.error(f"Invalid JSON format from URL {url}")
                logger.debug(f"Response content: {await response.text()}")
                return None
    except aiohttp.ClientError as e:
        logger.error(f"Client error fetching orderbook from URL {url}: {e}")
        return None
    except asyncio.TimeoutError:
        logger.error(f"Timeout error fetching orderbook from URL {url}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching orderbook from URL {url}: {e}")
        return None

async def fetch_orderbook_binance(session, symbol):
    url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=200"
    return await fetch_orderbook(session, url)

async def fetch_orderbook_bitget(session, symbol):
    url = f"https://api.bitget.com/api/v2/spot/market/orderbook?symbol={symbol}&limit=200"
    return await fetch_orderbook(session, url)

async def fetch_orderbook_htx(session, symbol):
    url = f"https://api.huobi.pro/market/depth?symbol={symbol}&type=step0&limit=200"
    return await fetch_orderbook(session, url)

async def fetch_orderbook_okx(session, symbol):
    url = f"https://www.okx.com/api/v5/market/books?instId={symbol}&limit=200"
    return await fetch_orderbook(session, url)

async def fetch_orderbook_kucoin(session, symbol):
    url = f"https://api.kucoin.com/api/v1/market/orderbook/level2_20?symbol={symbol}&limit=200"
    return await fetch_orderbook(session, url)

async def fetch_orderbook_bybit(session, symbol):
    url = f"https://api.bybit.com/v5/market/orderbook?category=spot&symbol={symbol}&limit=200"
    return await fetch_orderbook(session, url)

async def fetch_orderbook_mexc(session, symbol):
    url = f"https://api.mexc.com/api/v3/depth?symbol={symbol}&limit=200"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    return await fetch_orderbook(session, url, headers=headers)

async def fetch_orderbook_gateio(session, symbol):
    url = f"https://api.gateio.ws/api/v4/spot/order_book?currency_pair={symbol}&limit=1000"
    return await fetch_orderbook(session, url)

def analyze_orderbook_depth(symbol, bids, asks):
    logger.info(f"Analyzing orderbook depth for symbol: {symbol}")
    
    bid_counts = {price: bids.count((price, qty)) for price, qty in bids}
    ask_counts = {price: asks.count((price, qty)) for price, qty in asks}

    bid_volumes = {
        price: sum(qty for p, qty in bids if p == price) for price in bid_counts
    }
    ask_volumes = {
        price: sum(qty for p, qty in asks if p == price) for price in ask_counts
    }

    logger.debug(f"Bid price levels: {len(bid_counts)}, Ask price levels: {len(ask_counts)}")
    logger.debug(f"Total bid volume: {sum(bid_volumes.values()):.2f}, Total ask volume: {sum(ask_volumes.values()):.2f}")

    return {
        "symbol": symbol,
        "bid_counts": bid_counts,
        "ask_counts": ask_counts,
        "bid_volumes": bid_volumes,
        "ask_volumes": ask_volumes,
    }

def parse_binance_orderbook(orderbook):
    bids = [(float(price), float(qty)) for price, qty in orderbook.get("bids", [])]
    asks = [(float(price), float(qty)) for price, qty in orderbook.get("asks", [])]
    return bids, asks

def parse_bitget_orderbook(orderbook):
    bids = [
        (float(price), float(qty))
        for price, qty in orderbook.get("data", {}).get("bids", [])
    ]
    asks = [
        (float(price), float(qty))
        for price, qty in orderbook.get("data", {}).get("asks", [])
    ]
    return bids, asks


def parse_htx_orderbook(orderbook):
    bids = [
        (float(price), float(qty))
        for price, qty in orderbook.get("tick", {}).get("bids", [])
    ]
    asks = [
        (float(price), float(qty))
        for price, qty in orderbook.get("tick", {}).get("asks", [])
    ]
    return bids, asks

def parse_okx_orderbook(orderbook):
    bids = [
        (float(price), float(qty))
        for price, qty, *_ in orderbook.get("data", [{}])[0].get("bids", [])
    ]
    asks = [
        (float(price), float(qty))
        for price, qty, *_ in orderbook.get("data", [{}])[0].get("asks", [])
    ]
    return bids, asks

def parse_kucoin_orderbook(orderbook):
    data = orderbook.get("data", {})
    bids = [(float(price), float(qty)) for price, qty in data.get("bids", [])]
    asks = [(float(price), float(qty)) for price, qty in data.get("asks", [])]
    return bids, asks

def parse_bybit_orderbook(orderbook):
    result = orderbook.get("result", {})
    bids = [
        (float(price), float(qty))
        for price, qty in result.get("b", [])
    ]
    asks = [
        (float(price), float(qty))
        for price, qty in result.get("a", [])
    ]
    return bids, asks

def parse_mexc_orderbook(orderbook):
    if orderbook is None:
        logger.warning("MEXC orderbook is None, returning empty lists")
        return [], []
    
    bids = [
        (float(price), float(qty))
        for price, qty in orderbook.get("bids", [])
    ]
    asks = [
        (float(price), float(qty))
        for price, qty in orderbook.get("asks", [])
    ]
    return bids, asks

def parse_gateio_orderbook(orderbook):
    bids = [
        (float(price), float(qty))
        for price, qty in orderbook.get("bids", [])
    ]
    asks = [
        (float(price), float(qty))
        for price, qty in orderbook.get("asks", [])
    ]
    return bids, asks


def convert_symbol_for_exchange(exchange, symbol):
    quote_currencies = [
        "USDT", "USD", "EUR", "USDC", "BTC", "ETH", "BUSD", "DAI", "GBP",
        "AUD", "JPY", "KRW", "TRY", "CNY", "SGD", "HKD", "CAD", "CHF", "NZD",
    ]

    if exchange in ["OKX", "KuCoin"]:
        for quote in quote_currencies:
            if symbol.endswith(quote):
                return symbol.replace(quote, f"-{quote}")
    if exchange == "GateIo":
        for quote in quote_currencies:
            if symbol.endswith(quote):
                return symbol.replace(quote, f"_{quote}")
    conversions = {
        "Binance": symbol,
        "Bitget": symbol,
        "HTX": symbol.lower(),
        "OKX": symbol,
        "KuCoin": symbol,
        "Bybit": symbol,
        "MEXC": symbol,
        "GateIo": symbol,
    }
    return conversions[exchange]

async def collect_orderbooks(symbol: str, exchanges: Optional[List[str]] = None) -> Dict[str, Any]:
    start_time = time.time()
    logger.info(f"Starting to collect orderbooks for symbol: {symbol}")
    if exchanges is None:
        exchanges = [
            "Binance", "Bitget", "HTX", "OKX", "KuCoin", "Bybit", "MEXC", "GateIo"
        ]
    logger.info(f"Exchanges to query: {', '.join(exchanges)}")
    
    if symbol.endswith("USD"):
        symbol = symbol.replace("USD", "USDT")
        logger.info(f"Symbol adjusted to: {symbol}")

    exchange_functions = {
        "Binance": (fetch_orderbook_binance, parse_binance_orderbook),
        "Bitget": (fetch_orderbook_bitget, parse_bitget_orderbook),
        "HTX": (fetch_orderbook_htx, parse_htx_orderbook),
        "OKX": (fetch_orderbook_okx, parse_okx_orderbook),
        "KuCoin": (fetch_orderbook_kucoin, parse_kucoin_orderbook),
        "Bybit": (fetch_orderbook_bybit, parse_bybit_orderbook),
        "MEXC": (fetch_orderbook_mexc, parse_mexc_orderbook),
        "GateIo": (fetch_orderbook_gateio, parse_gateio_orderbook),
    }

    orderbooks = {}
    semaphore = asyncio.Semaphore(5)
    logger.info(f"Using semaphore with limit of 5 concurrent requests")

    async with aiohttp.ClientSession() as session:
        tasks = []
        for exchange in exchanges:
            fetch_func, _ = exchange_functions[exchange]
            exchange_symbol = convert_symbol_for_exchange(exchange, symbol)
            logger.info(f"Preparing to fetch orderbook for {exchange} symbol {exchange_symbol}")

            async def fetch_with_semaphore(fetch_func, session, exchange_symbol, exchange_name):
                url = ""  # Initialize url variable for logging
                try:
                    logger.debug(f"Acquiring semaphore for {exchange_name}")
                    async with semaphore:
                        logger.debug(f"Semaphore acquired for {exchange_name}, preparing to fetch orderbook")

                        # Here we derive the URL by fetching orderbook and logging the URL
                        if exchange_name == "Binance":
                            url = f"https://api.binance.com/api/v3/depth?symbol={exchange_symbol}&limit=200"
                        elif exchange_name == "Bitget":
                            url = f"https://api.bitget.com/api/v2/spot/market/orderbook?symbol={exchange_symbol}&limit=200"
                        elif exchange_name == "HTX":
                            url = f"https://api.huobi.pro/market/depth?symbol={exchange_symbol}&type=step0&limit=200"
                        elif exchange_name == "OKX":
                            url = f"https://www.okx.com/api/v5/market/books?instId={exchange_symbol}&limit=200"
                        elif exchange_name == "KuCoin":
                            url = f"https://api.kucoin.com/api/v1/market/orderbook/level2_20?symbol={exchange_symbol}&limit=200"
                        elif exchange_name == "Bybit":
                            url = f"https://api.bybit.com/v5/market/orderbook?category=spot&symbol={exchange_symbol}&limit=200"
                        elif exchange_name == "MEXC":
                            url = f"https://api.mexc.com/api/v3/depth?symbol={exchange_symbol}&limit=200"
                        elif exchange_name == "GateIo":
                            url = f"https://api.gateio.ws/api/v4/spot/order_book?currency_pair={exchange_symbol}&limit=1000"

                        # Log the URL
                        logger.info(f"Fetching orderbook from {exchange_name} with URL: {url}")
                        result = await fetch_func(session, exchange_symbol)
                        logger.debug(f"Fetch completed for {exchange_name}")
                        return result
                except Exception as e:
                    logger.error(f"Error fetching data from {exchange_name} (URL: {url}): {e}")
                    return None
                
            tasks.append(
                asyncio.create_task(
                    fetch_with_semaphore(fetch_func, session, exchange_symbol, exchange)
                )
            )
        
        logger.info(f"Created {len(tasks)} tasks for fetching orderbooks")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All fetch tasks completed")

        for exchange, result in zip(exchanges, results):
            try:
                if isinstance(result, Exception):
                    logger.error(f"Failed to fetch orderbook from {exchange}: {result}")
                    continue
                
                logger.info(f"Processing orderbook for {exchange}")
                _, parse_func = exchange_functions[exchange]
                bids, asks = parse_func(result)
                logger.debug(f"{exchange}: Parsed {len(bids)} bids and {len(asks)} asks")
                
                orderbooks[exchange] = analyze_orderbook_depth(symbol, bids, asks)
                logger.info(f"Completed processing orderbook for {exchange}")
            except Exception as e:
                logger.error(f"Error processing {exchange}: {e}", exc_info=True)

    total_duration = time.time() - start_time
    logger.critical(f"Finished collecting orderbooks for {symbol}")
    logger.critical(f"Total exchanges processed: {len(orderbooks)}/{len(exchanges)}")
    time_logger.info(f"Total duration for collect_orderbooks: {total_duration:.2f} seconds")
    
    return orderbooks

# To use the asynchronous functions, you need to run them within an event loop
# if __name__ == "__main__":
#     start_time = time.time()
#     symbol = "SLNUSDT"
#     logger.info(f"Starting collection of orderbooks for symbol {symbol}")
#     orderbooks = asyncio.run(collect_orderbooks(symbol))
#     end_time = time.time()
#     logger.info(f"Execution time: {end_time - start_time:.2f} seconds")
#     logger.info(f"Orderbooks collected: {orderbooks}")
