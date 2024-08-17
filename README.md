[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)

# Trading bot written in Python utilizing the Kraken API for trading cryptocurrencies

## Strategy
Currently there are 2 strategies:
- Main branch: MACD only, go long/short on MACD crossover, using daily (1D) timeframe. Strategy is backtested using a Tradingview backtester which returned profits for almost all assets.
- v0.8 branch: trades RSI and MACD, a trade is triggered when RSI is below or above a certain value. After that the MACD is analyzed and when MACD is in an upward/downward trend the asset is bought or sold 

## Requirements / dependencies
- Tested on Fedora39/40
- See requirements.txt for Python dependencies
- TA-Lib library: underlying C library needs to be installed. For instructions see https://github.com/ta-lib/ta-lib-python
- Kraken API key with capabilities to trade assets and obtain account information, for more information see https://support.kraken.com/hc/en-us/articles/360000919966-How-to-create-an-API-key
- Telegram key which is used to send information about buy/sell to your telegram bot
- The program expects that your Kraken API key(s) and Telegram key are present in env vars. Export them accordingly. 

## Todo
- Containerize application
- Create Helm chart to be used on k8s
- Update MACD/RSI strategy such that no asset file is used and rename branch
