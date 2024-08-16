# Trading bot written in Python utilizing the Kraken API for trading cryptocurrencies

## Strategy
Currently there are 2 stratege

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
