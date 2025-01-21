import asyncio
import logging
import time
from typing import List, Dict, Optional, Tuple, Union

from find_common_coins import main

# Loggers for process information and execution time tracking
logger = logging.getLogger("spread_process_first")
time_logger = logging.getLogger("time_analysis")

def compute_spread_percent(coin_data: Dict[str, Dict[str, float]]) -> Tuple[Optional[float], Optional[float], List[str], List[str]]:
    try:
        bid_prices = {
            exchange: data["bid_price"]
            for exchange, data in coin_data.items()
            if isinstance(data, dict) and "bid_price" in data and data["bid_price"] > 0
        }
        ask_prices = {
            exchange: data["ask_price"]
            for exchange, data in coin_data.items()
            if isinstance(data, dict) and "ask_price" in data and data["ask_price"] > 0
        }
    except (TypeError, KeyError) as e:
        logger.error(f"Error processing coin_data: {coin_data}. Exception: {e}")
        return None, None, [], []

    if not bid_prices or not ask_prices:
        logger.warning(f"Missing bid or ask prices for coin_data: {coin_data.get('symbol', 'unknown')} Data: {coin_data}")
        return None, None, [], []

    # Find minimum bid price and maximum ask price
    min_bid = min(bid_prices.values())
    max_ask = max(ask_prices.values())

    # Define bid price range: [min_bid, min_bid * 1]
    bid_range = (min_bid, min_bid * 1)

    # Define ask price range: [max_ask * 1, max_ask]
    ask_range = (max_ask * 1, max_ask)

    # Find all exchanges where bid price is within range
    bid_exchanges_in_range = [
        exchange for exchange, price in bid_prices.items() if bid_range[0] <= price <= bid_range[1]
    ]

    # Find all exchanges where ask price is within range
    ask_exchanges_in_range = [
        exchange for exchange, price in ask_prices.items() if ask_range[0] <= price <= ask_range[1]
    ]

    # Check if arbitrage opportunity exists (min_bid < max_ask)
    if min_bid >= max_ask:
        logger.warning(f"Invalid bid-ask pair: Min Bid ({min_bid}) >= Max Ask ({max_ask})")
        return None, None, [], []

    # Calculate spread percentage
    spread_percent = ((max_ask - min_bid) / min_bid) * 100
    return spread_percent, min_bid, bid_exchanges_in_range, ask_exchanges_in_range

async def spread_first(common_coins: List[Dict[str, Union[str, Dict[str, float]]]]) -> List[Dict[str, Union[str, float, List[str]]]]:
    coins_with_spreads = []

    for coin in common_coins:
        spread_percent, min_bid, bid_exchanges_in_range, ask_exchanges_in_range = compute_spread_percent(coin)
        if spread_percent is not None and 4 <= spread_percent <= 75:
            if any(exchange in ask_exchanges_in_range for exchange in bid_exchanges_in_range):
                logger.info(f"Skipping coin: {coin.get('symbol', 'unknown')} as min and max exchanges overlap in range.")
                continue
            coins_with_spreads.append({
                "symbol": coin.get("symbol", "unknown"),
                "bid_exchanges_in_range": bid_exchanges_in_range,
                "ask_exchanges_in_range": ask_exchanges_in_range,
                "spread_percent": spread_percent,
                "min_bid": min_bid,
                "max_ask": max(ask_exchanges_in_range),
            })
    logger.info(f"Found {len(coins_with_spreads)} coins with spreads.")
    return coins_with_spreads

async def first_spread_main() -> List[Dict[str, Union[str, float]]]:
    import platform
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logger.info("Starting first_spread function.")
    try:
        start_time = time.time()
        # main() function collects data from exchanges and returns list of common assets
        common_coins = await main()
        if common_coins:
            coins_with_spreads = await spread_first(common_coins)
            for coin in coins_with_spreads:
                logger.info(f"Coin with spread: {coin['symbol']}")
            time_logger.info(f"first_spread_main duration: {time.time() - start_time:.2f} seconds.")
            logger.critical("-" * 50)
            return coins_with_spreads
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        logger.critical("-" * 50)
        return []

if __name__ == "__main__":
    import platform
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    coins = asyncio.run(first_spread_main())
    print(coins)
