import time
import asyncio
import logging
from spread_process_first import first_spread_main
from volatility import volatility
import logging_config

logger = logging.getLogger("spread_process_second")
time_logger = logging.getLogger("time_analysis")

METRIC_THRESHOLDS = {
    "volatility": (-1.2, 1.2),
    "adr": (-5, 5),
    "mean_deviation": (-0.75, 0.75),
    "roc": (-0.4, 0.4),
    "max_drawdown": (-0.6, 0.6),
    "sharpe_ratio": (-2, 2),
    "var": (-0.05, 0.05),
    "cvar": (-0.07, 0.07),
    "calmar_ratio": (-5, 5),
    "sortino_ratio": (-4, 4),
    "momentum": (-50, 50),
    "cumulative_return": (-0.5, 0.5),
    "omega_ratio": (-2, 2),
}

def is_within_range(value, range_or_threshold):
    if isinstance(range_or_threshold, tuple):
        return range_or_threshold[0] <= value <= range_or_threshold[1]
    return value <= range_or_threshold

async def process_coin(coin):
    try:
        metrics = await volatility(coin)
        if metrics is None:
            logger.warning(f"Metrics info is None for coin: {coin['symbol']}")
            return None

        valid_combinations = []

        for buy_exchange in coin["bid_exchanges_in_range"]:
            for sell_exchange in coin["ask_exchanges_in_range"]:
                min_bid_metrics = metrics.get(buy_exchange, {})
                max_ask_metrics = metrics.get(sell_exchange, {})

                if not min_bid_metrics or not max_ask_metrics:
                    logger.warning(f"Metrics missing for exchanges {buy_exchange} or {sell_exchange} for coin: {coin['symbol']}")
                    continue

                # Verify all metrics are within acceptable thresholds
                all_within_thresholds = all(
                    is_within_range(min_bid_metrics.get(metric), threshold) and 
                    is_within_range(max_ask_metrics.get(metric), threshold)
                    for metric, threshold in METRIC_THRESHOLDS.items()
                )

                # Check volatility for both buy and sell exchanges
                buy_volatility = min_bid_metrics.get("volatility")
                sell_volatility = max_ask_metrics.get("volatility")

                if buy_volatility is not None and sell_volatility is not None:
                    if all_within_thresholds and \
                            is_within_range(buy_volatility, METRIC_THRESHOLDS["volatility"]) and \
                            is_within_range(sell_volatility, METRIC_THRESHOLDS["volatility"]):
                        logger.info(f"Valid combination found for {coin['symbol']}: Buy from {buy_exchange} (Volatility: {buy_volatility}), Sell on {sell_exchange} (Volatility: {sell_volatility})")
                        valid_combinations.append({
                            "symbol": coin["symbol"],
                            "buy_exchange": buy_exchange,
                            "sell_exchange": sell_exchange,
                            "buy_exchange_volatility": buy_volatility,
                            "sell_exchange_volatility": sell_volatility,
                        })
        
        return valid_combinations if valid_combinations else None

    except Exception as e:
        logger.error(f"Error processing coin {coin['symbol']}: {e}", exc_info=True)
        return None


async def second_spread(coins_with_spreads):
    tasks = [process_coin(coin) for coin in coins_with_spreads]
    results = await asyncio.gather(*tasks)
    
    filtered_coins = [combination for result in results if result for combination in result]
    return filtered_coins


async def main_second():
    import platform
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    start_time = time.time()
    try:
        # Get list of coins with potential spreads from first stage
        coins_with_spreads = await first_spread_main()
        filtered_coins = await second_spread(coins_with_spreads)
        return filtered_coins

    except Exception as e:
        print(f"Error in main_second execution: {e}")
        return []
    
def print_info_coins(filtered_coins):
    if not filtered_coins:
        print("No valid coin combinations found.")
        return

    print(f"Found {len(filtered_coins)} valid coin combinations:")
    print("-" * 50)
    for i, combination in enumerate(filtered_coins, start=1):
        print(f"Combination {i}:")
        print(f"  Symbol: {combination['symbol']}")
        print(f"  Buy Exchange: {combination['buy_exchange']}")
        print(f"  Sell Exchange: {combination['sell_exchange']}")
        print(f"  Buy Exchange Volatility: {combination['buy_exchange_volatility']:.4f}")
        print(f"  Sell Exchange Volatility: {combination['sell_exchange_volatility']:.4f}")
        print("-" * 50)

if __name__ == "__main__":
    filtered_coins = asyncio.run(main_second())
    print_info_coins(filtered_coins)


