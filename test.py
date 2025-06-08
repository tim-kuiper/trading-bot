import argparse

parser = argparse.ArgumentParser(
    prog="test",
    description="this is a testprogram",
    epilog="thank you"
)

parser.add_argument("timeframe")
parser.add_argument("strategy")

args = parser.parse_args()

