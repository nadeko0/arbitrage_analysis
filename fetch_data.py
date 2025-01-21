import aiohttp
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any

import config, logging_config
from cache import cached
from error_handling import handle_api_errors

logger = logging.getLogger("fetch_data")
time_logger = logging.getLogger("time_analysis")

@cached
@handle_api_errors
async def fetch_data(session: aiohttp.ClientSession, url: str) -> Optional[Dict[str, Any]]:
    start_time = time.time()
    try:
        async with session.get(url, timeout=15) as response:
            response.raise_for_status()
            data = await response.json()
            logger.debug(f"Data fetched from URL: {url} - Response size: {len(str(data))} bytes")
            time_logger.debug(f"Data fetch from {url} took {time.time() - start_time:.2f} seconds")
            return data
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(f"Error fetching data from {url}: {e}")
        return None

def safe_float(value: Optional[str], default: float = 0.0) -> float:
    """ Convert value to float, return default if conversion fails or value is empty. """
    try:
        return float(value) if value else default
    except ValueError:
        return default

def extract_fields(exchange: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    start_time = time.time()
    logger.debug(f"Starting field extraction for exchange: {exchange}")
    try:
        exchange_parsers = {
            "Binance": lambda data: [
                {
                    "symbol": item["symbol"], 
                    "bid_price": safe_float(item["bidPrice"]), 
                    "ask_price": safe_float(item["askPrice"])
                } 
                for item in data
            ],
            "Bitget": lambda data: [
                {
                    "symbol": item["symbol"], 
                    "bid_price": safe_float(item["buyOne"]), 
                    "ask_price": safe_float(item["sellOne"])
                } 
                for item in data["data"]
            ],
            "HTX": lambda data: [
                {
                    "symbol": item["symbol"].upper(), 
                    "bid_price": safe_float(item["bid"]), 
                    "ask_price": safe_float(item["ask"])
                } 
                for item in data["data"]
            ],
            "OKX": lambda data: [
                {
                    "symbol": item["instId"].replace("-", ""), 
                    "bid_price": safe_float(item["bidPx"]), 
                    "ask_price": safe_float(item["askPx"])
                } 
                for item in data["data"]
            ],
            "KuCoin": lambda data: [
                {
                    "symbol": item["symbol"].replace("-", ""), 
                    "bid_price": safe_float(item["buy"]), 
                    "ask_price": safe_float(item["sell"])
                } 
                for item in data["data"]["ticker"]
            ],
            "Bybit": lambda data: [
                {
                    "symbol": item["symbol"], 
                    "bid_price": safe_float(item["bid1Price"]), 
                    "ask_price": safe_float(item["ask1Price"])
                } 
                for item in data["result"]["list"]
            ],
            "MEXC": lambda data: [
                {
                    "symbol": item["symbol"], 
                    "bid_price": safe_float(item["bidPrice"]), 
                    "ask_price": safe_float(item["askPrice"])
                } 
                for item in data
            ],
            "GateIo": lambda data: [
                {
                    "symbol": item["currency_pair"].replace("_", ""), 
                    "bid_price": safe_float(item["highest_bid"]), 
                    "ask_price": safe_float(item["lowest_ask"])
                } 
                for item in data
            ],
        }
        result = exchange_parsers.get(exchange, lambda _: [])(data)
    except KeyError as e:
        logger.error(f"Error extracting fields for {exchange}: {e}")
        result = []
    time_logger.debug(f"Field extraction for {exchange} took {time.time() - start_time:.2f} seconds")
    return result

async def fetching() -> Dict[str, List[Dict[str, Any]]]:
    import platform
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    start_time = time.time()
    exchanges_data = {}
    semaphore = asyncio.Semaphore(10)

    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_with_semaphore(session, semaphore, exchange, url)
            for exchange, url in config.TICKERS_URLS.items()
        ]
        results = await asyncio.gather(*tasks)

        for exchange, data in results:
            if data is not None:
                exchanges_data[exchange] = extract_fields(exchange, data)
                logger.info(f"Data successfully fetched and extracted for {exchange}")
            else:
                logger.warning(f"{exchange}: No data received")

    logger.critical("-" * 50)
    time_logger.debug(f"Fetching completed - duration: {time.time() - start_time:.2f} seconds")
    return exchanges_data

async def fetch_with_semaphore(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, exchange: str, url: str):
    async with semaphore:
        logger.debug(f"Fetching data for {exchange} from {url}")
        return exchange, await fetch_data(session, url)

if __name__ == "__main__":
    asyncio.run(fetching())
