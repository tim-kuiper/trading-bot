import argparse

parser = argparse.ArgumentParser()

parser.add_argument("timeframe", choices=["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"], type=str)
parser.add_argument("order_size", type=int)
parser.add_argument("strategy", choices=["dca-macd-rsi", "dca-flat", "macd-crossover", "rsi", "macd-rsi"], type=str)

args = parser.parse_args()

timeframe = args.timeframe
order_size = args.order_size
strategy = args.strategy