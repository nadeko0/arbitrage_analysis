import logging
import asyncio
from collections import defaultdict
from typing import List, Dict, Any
from fetch_data import fetching
import logging_config

logger = logging.getLogger("find_common_coins")

def common_coins(exchanges_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    logger.debug("Starting the process of finding common coins.")

    symbol_exchange_data = defaultdict(lambda: defaultdict(dict))
    
    # Process symbols and collect exchange data
    for exchange, data in exchanges_data.items():
        for item in data:
            symbol = item["symbol"]
            symbol_exchange_data[symbol][exchange] = {
                "bid_price": item["bid_price"],
                "ask_price": item["ask_price"],
            }
    
    # Find symbols available on multiple exchanges (2 or more)
    common_coins = [
        {"symbol": symbol, **exchanges}
        for symbol, exchanges in symbol_exchange_data.items()
        if len(exchanges) >= 2
    ]

    logger.debug(f"Common symbols found: {len(common_coins)} symbols.")
    logger.info(f"Total common coins found: {len(common_coins)}")
    return common_coins

async def main() -> List[Dict[str, Any]]:
    import platform
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        logger.info("Starting the main process.")
        exchanges_data = await fetching()
        logger.info("Data fetching process completed.")
        common_coins_result = common_coins(exchanges_data)
        logger.info("Common coins finding process completed.")
        logger.critical("-" * 50)
        return common_coins_result
    except Exception as e:
        logger.critical("-" * 50)
        logger.error(f"Error during execution: {e}", exc_info=True)
        return []

if __name__ == "__main__":
    print(asyncio.run(main()))
