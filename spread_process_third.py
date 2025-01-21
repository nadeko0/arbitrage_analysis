import asyncio
import logging
from decimal import Decimal
from datetime import datetime
import time
import argparse
import sys
import platform

from spread_process_second import main_second
from collect_orderbooks import collect_orderbooks
from risk_manager import AdvancedRiskManager
from get_trade_url import get_spot_trade_url

import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("arbitrage_analysis.log"),
    ]
)
logger = logging.getLogger("arbitrage_analysis")

class ArbitrageAnalyzer:
    def __init__(self, min_profit_percentage: float, max_trade_volume: float, target_volume: float):
        self.maker_fee = Decimal('0.001')
        self.taker_fee = Decimal('0.002')
        self.min_profit_percentage = Decimal(str(min_profit_percentage))
        self.max_trade_volume = Decimal(str(max_trade_volume))
        self.target_volume = Decimal(str(target_volume))
        self.risk_manager = AdvancedRiskManager(
            max_position_size=self.max_trade_volume,
            max_loss_percentage=Decimal('0.02'),
            max_daily_loss=Decimal('0.05'),
            max_drawdown=Decimal('0.1'),
        )
        self.account_balance = Decimal('10000')

    async def analyze_arbitrage_opportunities(self, main_second_results: list[dict], collect_orderbooks_func, max_results=100):
        opportunities = []
        
        async def process_opportunity(result):
            try:
                opportunity = await asyncio.wait_for(
                    self.analyze_single_opportunity_wrapper(result, collect_orderbooks_func),
                    timeout=30
                )
                if opportunity and opportunity['profit_percentage'] > self.min_profit_percentage:
                    entry_price = Decimal(str(opportunity['buy_price']))
                    position_size = Decimal(str(opportunity['volume']))
                    stop_loss = self.risk_manager.calculate_optimal_stop_loss(
                        entry_price, 
                        Decimal(str(opportunity['volatility']))
                    )
                    
                    if self.risk_manager.validate_trade(
                        entry_price=entry_price,
                        position_size=position_size,
                        stop_loss=stop_loss,
                        account_balance=self.account_balance
                    ):
                        adjusted_size = self.risk_manager.adjust_position_size_based_on_performance(position_size)
                        opportunity['volume'] = float(adjusted_size)
                        opportunity['stop_loss'] = float(stop_loss)
                        opportunity['risk_reward_ratio'] = self.calculate_risk_reward_ratio(opportunity)
                        return opportunity
                    else:
                        logger.warning(f"Trade for {opportunity['symbol']} rejected by risk manager")
            except asyncio.TimeoutError:
                logger.warning(f"Analysis for {result['symbol']} timed out and was skipped")
            except Exception as e:
                logger.error(f"Error analyzing opportunity for {result['symbol']}: {str(e)}")
            return None

        tasks = [process_opportunity(result) for result in main_second_results[:max_results]]
        opportunities = [opp for opp in await asyncio.gather(*tasks) if opp]
        
        opportunities.sort(key=lambda x: x['profit_percentage'] * x['risk_reward_ratio'], reverse=True)
        
        return opportunities

    def analyze_single_opportunity(self, symbol: str, buy_exchange: str, sell_exchange: str, buy_orderbook: dict, sell_orderbook: dict, buy_volatility: float, sell_volatility: float):
        try:
            buy_orders = self.get_orderbook_data(buy_orderbook, is_buy=True)
            sell_orders = self.get_orderbook_data(sell_orderbook, is_buy=False)
        except ValueError as e:
            logger.error(f"Error getting orderbook data for {symbol}: {str(e)}")
            return None

        if not buy_orders or not sell_orders:
            logger.warning(f"Empty orderbook for {symbol}")
            return None

        buy_result = self.calculate_split_orders(buy_orders, self.target_volume, is_buy=True)
        if not buy_result:
            logger.warning(f"Insufficient liquidity for buying {symbol}")
            return None

        coins_bought, cost = buy_result['total_volume'], buy_result['total_cost']
        sell_result = self.calculate_split_orders(sell_orders, coins_bought, is_buy=False)
        if not sell_result:
            logger.warning(f"Insufficient liquidity for selling {symbol}")
            return None

        coins_sold, revenue = sell_result['total_volume'], sell_result['total_cost']

        buy_price = cost / coins_bought
        sell_price = revenue / coins_sold

        cost_with_fee = cost * (Decimal('1') + self.taker_fee)
        revenue_with_fee = revenue * (Decimal('1') - self.maker_fee)

        market_depth = self.calculate_market_depth(buy_orderbook, sell_orderbook)
        
        profit = revenue_with_fee - cost_with_fee
        profit_percentage = (profit / cost_with_fee) * Decimal('100')
        
        # Use the average of buy and sell volatilities
        avg_volatility = (buy_volatility + sell_volatility) / 2
        
        return {
            "symbol": symbol,
            "buy_exchange": buy_exchange,
            "sell_exchange": sell_exchange,
            "buy_price": float(buy_price),
            "sell_price": float(sell_price),
            "volume": float(coins_bought),
            "cost": float(cost_with_fee),
            "revenue": float(revenue_with_fee),
            "profit": float(profit),
            "profit_percentage": float(profit_percentage),
            "market_depth": float(market_depth),
            "volatility": float(avg_volatility),
            "timestamp": datetime.now().isoformat(),
        }

    async def analyze_single_opportunity_wrapper(self, result, collect_orderbooks_func):
        symbol = result['symbol']
        buy_exchange = result['buy_exchange']
        sell_exchange = result['sell_exchange']
        buy_volatility = result['buy_exchange_volatility']
        sell_volatility = result['sell_exchange_volatility']
        
        try:
            orderbooks = await asyncio.wait_for(
                collect_orderbooks_func(symbol, [buy_exchange, sell_exchange]),
                timeout=20
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout when fetching orderbooks for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error fetching orderbooks for {symbol}: {str(e)}")
            return None

        if buy_exchange not in orderbooks or sell_exchange not in orderbooks:
            logger.warning(f"Failed to get orderbooks for {symbol} on {buy_exchange} and/or {sell_exchange}")
            return None
        
        buy_orderbook = orderbooks[buy_exchange]
        sell_orderbook = orderbooks[sell_exchange]
        
        return self.analyze_single_opportunity(symbol, buy_exchange, sell_exchange, buy_orderbook, sell_orderbook, buy_volatility, sell_volatility)

    def get_orderbook_data(self, orderbook: dict, is_buy: bool) -> list[list[Decimal]]:
        if 'asks' in orderbook and 'bids' in orderbook:
            data = orderbook['asks'] if is_buy else orderbook['bids']
        elif 'ask_volumes' in orderbook and 'bid_volumes' in orderbook:
            key = 'ask_volumes' if is_buy else 'bid_volumes'
            data = [[price, volume] for price, volume in orderbook[key].items()]
        else:
            raise ValueError("Unsupported orderbook format")
        
        return [[Decimal(str(price)), Decimal(str(volume))] for price, volume in data]

    def calculate_split_orders(self, orderbook: list[list[Decimal]], target_volume: Decimal, is_buy: bool) -> dict:
        orders = []
        total_volume = Decimal('0')
        total_cost = Decimal('0')

        for price, volume in orderbook:
            if is_buy:
                available_volume = min(volume, (target_volume - total_cost) / price)
            else:
                available_volume = min(volume, target_volume - total_volume)

            if available_volume > Decimal('0'):
                orders.append({"price": float(price), "volume": float(available_volume)})
                total_volume += available_volume
                total_cost += available_volume * price

            if (is_buy and total_cost >= target_volume) or (not is_buy and total_volume >= target_volume):
                break

        if (is_buy and total_cost < target_volume) or (not is_buy and total_volume < target_volume):
            return None

        return {
            "orders": orders,
            "total_volume": total_volume,
            "total_cost": total_cost
        }

    def calculate_market_depth(self, buy_orderbook: dict, sell_orderbook: dict, depth_percentage: Decimal = Decimal('0.01')) -> Decimal:
        try:
            buy_orders = self.get_orderbook_data(buy_orderbook, is_buy=True)
            sell_orders = self.get_orderbook_data(sell_orderbook, is_buy=False)
        except ValueError:
            return Decimal('0')

        if not buy_orders or not sell_orders:
            return Decimal('0')

        best_ask = min(price for price, _ in buy_orders)
        best_bid = max(price for price, _ in sell_orders)
        
        buy_depth = sum(volume for price, volume in buy_orders if price <= best_ask * (Decimal('1') + depth_percentage))
        sell_depth = sum(volume for price, volume in sell_orders if price >= best_bid * (Decimal('1') - depth_percentage))
        return min(buy_depth, sell_depth)

    def calculate_risk_reward_ratio(self, opportunity: dict) -> float:
        entry_price = Decimal(str(opportunity['buy_price']))
        stop_loss = Decimal(str(opportunity['stop_loss']))
        take_profit = Decimal(str(opportunity['sell_price']))
        
        risk = (entry_price - stop_loss) / entry_price
        reward = (take_profit - entry_price) / entry_price
        
        if risk == Decimal('0'):
            return float('inf')
        
        return float(reward / risk)

    def print_arbitrage_opportunities(self, opportunities: list[dict]):
        if not opportunities:
            print("No arbitrage opportunities found.")
            return

        print("\n=== Arbitrage Opportunities ===")
        print(f"{'#':<3} {'Symbol':<10} {'Buy':<10} {'Sell':<10} {'Volume':<15} {'Cost (USDT)':<20} {'Revenue (USDT)':<20} {'Profit (USDT)':<15} {'Profit %':<10} {'R/R Ratio':<10} {'Market Depth':<15}")
        print("-" * 160)

        for i, opp in enumerate(opportunities, 1):
            print(f"{i:<3} {opp['symbol']:<10} {opp['buy_exchange']:<10} {opp['sell_exchange']:<10} "
                  f"{opp['volume']:<15.8f} {opp['cost']:<20.8f} {opp['revenue']:<20.8f} "
                  f"{opp['profit']:<15.8f} {opp['profit_percentage']:<10.2f}% {opp['risk_reward_ratio']:<10.2f} {opp['market_depth']:<15.2f}")

async def main(args):
    start_time = time.time()
    analyzer = ArbitrageAnalyzer(
        min_profit_percentage=args.min_profit,
        max_trade_volume=args.max_volume,
        target_volume=args.target_volume
    )

    while True:
        try:
            print(f"\n--- Analysis start: {datetime.now()} ---")
            print("Starting main_second execution")
            main_second_results = await main_second()
            print(f"main_second completed. Received {len(main_second_results)} results")
            
            print("Starting arbitrage opportunities analysis")
            opportunities = await analyzer.analyze_arbitrage_opportunities(main_second_results, collect_orderbooks)
            
            print(f"Analysis completed. Found {len(opportunities)} opportunities")
            analyzer.print_arbitrage_opportunities(opportunities)
            
        except Exception as e:
            logger.error(f"An error occurred: {e}", exc_info=True)
        
        if not args.loop:
            break
        
        print(f"\nWaiting {args.interval} seconds until next update...")
        await asyncio.sleep(args.interval)

    end_time = time.time()
    print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    parser = argparse.ArgumentParser(description="Arbitrage Opportunity Analyzer")
    parser.add_argument("--min-profit", type=float, default=config.MIN_PROFIT_PERCENTAGE,
                        help="Minimum profit percentage to consider an opportunity")
    parser.add_argument("--max-volume", type=float, default=config.MAX_TRADE_VOLUME,
                        help="Maximum trade volume in USDT")
    parser.add_argument("--target-volume", type=float, default=config.TARGET_VOLUME,
                        help="Target trade volume in USDT")
    parser.add_argument("--interval", type=int, default=config.UPDATE_INTERVAL,
                        help="Update interval in seconds")
    parser.add_argument("--loop", action="store_true",
                        help="Run in continuous loop mode")
    parser.add_argument("--log-level", type=str, default=config.LOG_LEVEL,
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Logging level")
    parser.add_argument("--log-file", type=str, default=config.LOG_FILE,
                        help="Log file path")

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(args.log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        print(f"A critical error occurred. Check the log file for details: {args.log_file}")