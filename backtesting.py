import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime, timedelta
import asyncio
import matplotlib.pyplot as plt
import csv

class ImprovedBacktester:
    def __init__(self, start_date: datetime, end_date: datetime, initial_balance: float = 10000):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.trades = []
        self.exchange_instances = {}
        self.fee = 0.001  # 0.1% fee per trade
        self.tokens_and_exchanges = self.load_tokens_from_csv()

    def load_tokens_from_csv(self):
        tokens_and_exchanges = {}
        with open('arbitrage_report.csv', 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                opportunities = eval(row['top_opportunities'])
                for opp in opportunities:
                    symbol = opp['symbol']
                    buy_exchange = opp['buy_exchange'].lower()
                    sell_exchange = opp['sell_exchange'].lower()
                    if symbol not in tokens_and_exchanges:
                        tokens_and_exchanges[symbol] = set()
                    tokens_and_exchanges[symbol].add(buy_exchange)
                    tokens_and_exchanges[symbol].add(sell_exchange)
        return tokens_and_exchanges

    async def _initialize_exchanges(self):
        all_exchanges = set()
        for exchanges in self.tokens_and_exchanges.values():
            all_exchanges.update(exchanges)
        
        for exchange in all_exchanges:
            if exchange not in self.exchange_instances:
                exchange_class = getattr(ccxt, exchange)
                self.exchange_instances[exchange] = exchange_class({
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot'
                    }
                })

    async def fetch_historical_data(self, symbol: str, timeframe: str = '1h'):
        all_data = {}
        for exchange_name in self.tokens_and_exchanges[symbol]:
            exchange = self.exchange_instances[exchange_name]
            try:
                data = await self.fetch_ohlcv_with_pagination(exchange, symbol, timeframe)
                if data:
                    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    all_data[exchange_name] = df
            except Exception as e:
                print(f"Error fetching data for {symbol} on {exchange_name}: {e}")
        return all_data

    async def fetch_ohlcv_with_pagination(self, exchange, symbol: str, timeframe: str):
        all_ohlcv = []
        since = int(self.start_date.timestamp() * 1000)
        end = int(self.end_date.timestamp() * 1000)
        limit = 1000  # Adjust based on exchange limits

        while since < end:
            try:
                ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, since, limit)
                if not ohlcv:
                    break
                all_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + 1
                await asyncio.sleep(exchange.rateLimit / 1000)  # Respect rate limits
            except ccxt.NetworkError as e:
                print(f"Network error, retrying: {e}")
                await asyncio.sleep(5)
            except ccxt.ExchangeError as e:
                print(f"Exchange error for {symbol}: {e}")
                break

        return all_ohlcv

    async def run_backtest(self):
        await self._initialize_exchanges()
        current_date = self.start_date
        while current_date <= self.end_date:
            print(f"Backtesting for date: {current_date}")
            
            for symbol, exchanges in self.tokens_and_exchanges.items():
                historical_data = await self.fetch_historical_data(symbol)
                if historical_data:
                    opportunity = self.analyze_opportunity(symbol, historical_data, current_date, exchanges)
                    if opportunity:
                        self.execute_trade(opportunity, current_date)
            
            current_date += timedelta(hours=1)

        self.print_results()

    def analyze_opportunity(self, symbol: str, data: Dict[str, pd.DataFrame], current_date: datetime, exchanges: set):
        current_prices = {}
        for exchange, df in data.items():
            if exchange in exchanges and not df.empty and current_date in df.index:
                current_prices[exchange] = df.loc[current_date, 'close']
        
        if len(current_prices) < 2:
            return None

        buy_exchange = min(current_prices, key=current_prices.get)
        sell_exchange = max(current_prices, key=current_prices.get)
        
        if buy_exchange != sell_exchange:
            spread_percent = (current_prices[sell_exchange] - current_prices[buy_exchange]) / current_prices[buy_exchange] * 100
            if 0.5 <= spread_percent <= 75:
                return {
                    'symbol': symbol,
                    'buy_exchange': buy_exchange,
                    'sell_exchange': sell_exchange,
                    'buy_price': current_prices[buy_exchange],
                    'sell_price': current_prices[sell_exchange],
                    'volume': 150 / current_prices[buy_exchange]  # Используем фиксированную сумму в 150 USDT
                }
        return None

    def execute_trade(self, opportunity, date):
        buy_price = opportunity['buy_price']
        sell_price = opportunity['sell_price']
        volume = opportunity['volume']
        
        cost = volume * buy_price * (1 + self.fee)
        revenue = volume * sell_price * (1 - self.fee)
        
        profit = revenue - cost
        self.current_balance += profit
        
        self.trades.append({
            'date': date,
            'symbol': opportunity['symbol'],
            'buy_exchange': opportunity['buy_exchange'],
            'sell_exchange': opportunity['sell_exchange'],
            'volume': volume,
            'cost': cost,
            'revenue': revenue,
            'profit': profit,
            'balance': self.current_balance
        })

    def print_results(self):
        print(f"Initial balance: {self.initial_balance}")
        print(f"Final balance: {self.current_balance}")
        print(f"Total profit: {self.current_balance - self.initial_balance}")
        print(f"Number of trades: {len(self.trades)}")
        
        df = pd.DataFrame(self.trades)
        if not df.empty:
            print(df.describe())
            self.plot_results(df)
        else:
            print("No trades were executed during the backtest period.")

    def plot_results(self, df):
        plt.figure(figsize=(12, 6))
        plt.plot(df['date'], df['balance'], label='Account Balance')
        plt.title('Account Balance Over Time')
        plt.xlabel('Date')
        plt.ylabel('Balance')
        plt.legend()
        plt.grid(True)
        plt.savefig('backtest_results.png')
        plt.close()

        plt.figure(figsize=(12, 6))
        plt.hist(df['profit'], bins=50)
        plt.title('Distribution of Trade Profits')
        plt.xlabel('Profit')
        plt.ylabel('Frequency')
        plt.savefig('profit_distribution.png')
        plt.close()

    def calculate_metrics(self):
        df = pd.DataFrame(self.trades)
        if df.empty:
            return {
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'profit_factor': 0
            }
        
        total_return = (self.current_balance - self.initial_balance) / self.initial_balance
        sharpe_ratio = np.sqrt(252) * df['profit'].mean() / df['profit'].std() if len(df) > 1 else 0
        max_drawdown = (df['balance'].cummax() - df['balance']) / df['balance'].cummax()
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown.max() if not max_drawdown.empty else 0,
            'win_rate': (df['profit'] > 0).mean() if not df.empty else 0,
            'profit_factor': df[df['profit'] > 0]['profit'].sum() / abs(df[df['profit'] < 0]['profit'].sum()) if not df.empty and (df['profit'] < 0).any() else 0
        }

async def main():
    start_date = datetime(2024, 8, 1)
    end_date = datetime(2024, 8, 2)
    backtester = ImprovedBacktester(start_date, end_date)
    await backtester.run_backtest()
    metrics = backtester.calculate_metrics()
    print("Backtest Metrics:")
    for key, value in metrics.items():
        print(f"{key}: {value}")

    # Закрыть все биржевые соединения
    for exchange in backtester.exchange_instances.values():
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())