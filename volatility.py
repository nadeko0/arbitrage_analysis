import asyncio
import aiohttp
import numpy as np
from datetime import datetime, timedelta
import logging
import time

import calculate_metrics

logger = logging.getLogger("volatility")
time_logger = logging.getLogger("time_analysis")

# Supported quote currencies for trading pairs
QUOTE_CURRENCIES = [
    "USDT", "USD", "EUR", "USDC", "BTC", "ETH", "BUSD", "DAI", "GBP", "AUD",
    "JPY", "KRW", "TRY", "CNY", "SGD", "HKD", "CAD", "CHF", "NZD",
]

def convert_symbol_for_exchange(exchange, symbol):
    if not isinstance(symbol, str):
        logger.error(f"Symbol must be a string, got {type(symbol)} instead.")
        return None

    def generic_conversion(symbol, separator):
        for quote in QUOTE_CURRENCIES:
            if symbol.endswith(quote):
                return symbol.replace(quote, f"{separator}{quote}")
        return symbol

    conversions = {
        "Binance": lambda sym: sym,
        "Bitget": lambda sym: sym,
        "HTX": lambda sym: sym,
        "OKX": lambda sym: generic_conversion(sym, "-"),
        "KuCoin": lambda sym: generic_conversion(sym, "-"),
        "Bybit": lambda sym: generic_conversion(sym, ""),
        "MEXC": lambda sym: generic_conversion(sym, ""),
        "GateIo": lambda sym: generic_conversion(sym, "_"),
    }

    return conversions.get(exchange, lambda x: x)(symbol)


async def fetch_price_data(session, url, data_key=None, data_format=None):
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()

            if data_key:
                for key in data_key.split('.'):
                    data = data.get(key, {})

            if not isinstance(data, list):
                logger.warning(f"Expected list for data_key '{data_key}', but got: {type(data)}")
                return []

            return [data_format(candle) for candle in data] if data_format else [float(candle[4]) for candle in data]
    except Exception as e:
        logger.error(f"Error fetching data from URL {url}: {e}")
        return []


async def get_binance_price_data(session, symbol):
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=10)).timestamp() * 1000)
    url = (
        f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=240"
        f"&startTime={start_time}&endTime={end_time}"
    )
    return await fetch_price_data(session, url)

async def get_bitget_price_data(session, symbol):
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=10)).timestamp() * 1000)
    url = (
        f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity=1h&limit=240"
        f"&startTime={start_time}&endTime={end_time}"
    )
    return await fetch_price_data(session, url, data_key="data")

async def get_htx_price_data(session, symbol):
    try:
        url = f"https://api.huobi.pro/market/history/kline?period=60min&size=240&symbol={symbol.lower()}"
        response = await fetch_price_data(session, url, data_key="data", data_format=lambda x: float(x["close"]))

        if not response:
            logger.warning(f"No valid data returned for HTX {symbol}. Please verify the symbol and API.")
            return []

        return response

    except Exception as e:
        logger.error(f"Exception occurred while fetching data from HTX: {str(e)}")
        return []

async def get_okx_price_data(session, symbol):
    start_time = int((datetime.now() - timedelta(days=10)).timestamp() * 1000)
    url = f"https://www.okx.com/api/v5/market/history-candles?instId={symbol}&bar=1H&before={start_time}&limit=240"
    return await fetch_price_data(session, url, data_key="data", data_format=lambda x: float(x[4]))

async def get_kucoin_price_data(session, symbol):
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=10)).timestamp() * 1000)
    url = f"https://api.kucoin.com/api/v1/market/candles?type=1hour&symbol={symbol}&startAt={start_time // 1000}&endAt={end_time // 1000}&limit=240"
    return await fetch_price_data(session, url, data_key="data", data_format=lambda x: float(x[2]))

async def get_bybit_price_data(session, symbol):
    try:
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=10)).timestamp() * 1000)
        url = (
            f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol}&interval=60"
            f"&start={start_time}&end={end_time}&limit=240"
        )
        response = await fetch_price_data(session, url, data_key="result.list", data_format=lambda x: float(x[4]))

        if not response:
            logger.warning(f"No valid data returned for Bybit {symbol}. Please verify the symbol and API.")
            return []

        return response

    except Exception as e:
        logger.error(f"Exception occurred while fetching data from Bybit: {str(e)}")
        return []

async def get_mexc_price_data(session, symbol):
    try:
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=10)).timestamp() * 1000)
        url = (
            f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=60m&limit=240"
            f"&startTime={start_time}&endTime={end_time}"
        )
        response = await fetch_price_data(session, url, data_format=lambda x: float(x[4]))

        if not response:
            logger.warning(f"No valid data returned for MEXC {symbol}. Please verify the symbol and interval.")
            return []

        return response

    except Exception as e:
        logger.error(f"Exception occurred while fetching data from MEXC: {str(e)}")
        return []

async def get_gateio_price_data(session, symbol):
    try:
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=10)).timestamp())
        url = (
            f"https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={symbol}&interval=1h"
            f"&from={start_time}&to={end_time}&limit=240"
        )
        response = await fetch_price_data(session, url, data_format=lambda x: float(x[2]))

        if not response:
            logger.warning(f"No valid data returned for Gate.io {symbol}. Please verify the symbol and API.")
            return []

        return response

    except Exception as e:
        logger.error(f"Exception occurred while fetching data from Gate.io: {str(e)}")
        return []
    
async def volatility(coin, risk_free_rate=0, target_return=0):
    symbol = coin.get("symbol")
    bid_exchanges = coin.get("bid_exchanges_in_range") or coin.get("buy_exchange")
    ask_exchanges = coin.get("ask_exchanges_in_range") or coin.get("sell_exchange")

    if not symbol or not bid_exchanges or not ask_exchanges:
        logger.error("Symbol, bid_exchanges, or ask_exchanges not specified in coin dictionary.")
        return None

    symbol_dict = {exchange: convert_symbol_for_exchange(exchange, symbol) for exchange in set(bid_exchanges + ask_exchanges)}

    async with aiohttp.ClientSession() as session:
        fetch_functions = {
            exchange: globals().get(f"get_{exchange.lower()}_price_data")
            for exchange in set(bid_exchanges + ask_exchanges)
        }

        fetch_functions = {exchange: fetch_function for exchange, fetch_function in fetch_functions.items() if fetch_function}

        if not fetch_functions:
            logger.error("No valid fetch functions found for the exchanges.")
            return None

        tasks = {
            exchange: fetch_function(session, symbol_dict[exchange]) 
            for exchange, fetch_function in fetch_functions.items()
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        metrics = {}
        for exchange, result in zip(tasks.keys(), results):
            if isinstance(result, Exception) or not result or len(result) <= 1:
                continue

            metrics[exchange] = calculate_metrics.calculate_all_metrics(result, risk_free_rate, target_return)

        return metrics if metrics else None