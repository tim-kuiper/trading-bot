import urllib.parse
import hashlib
import hmac
import base64
import time
import os
import requests
import json
import io
import pandas as pd
import numpy as np
import statistics
from pathlib import Path

'''
Trading script utilizing the Kraken API to buy/sell BTCUSDT/ETHUSDT/XRPUSDT/ADAUSDT/SOLUSDT on RSI for DCA
Notes:
- Using Kraken API key 
- Traded assets: BTC/ETH/XRP/ADA/SOL
- Based on 1H OHLC charts, executing a potential buy with the following properties:
  - If a trade is executed (currency is bought) then the value of the currency in USDT during execution is stored in a list
- List values should be stored and each hour the avg of this list should be printed, indicating the avg price that BTC was bought for
'''

# set vars
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_sec = os.environ['api_sec_env']
api_key = os.environ['api_key_env']
api_url = "https://api.kraken.com"

while True:
  def get_kraken_signature(urlpath, data, secret):
      postdata = urllib.parse.urlencode(data)
      encoded = (str(data['nonce']) + postdata).encode()
      message = urlpath.encode() + hashlib.sha256(encoded).digest()
      mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
      sigdigest = base64.b64encode(mac.digest())
      return sigdigest.decode()
  
  def kraken_request(uri_path, data, api_key, api_sec):
      headers = {}
      headers['API-Key'] = api_key
      headers['API-Sign'] = get_kraken_signature(uri_path, data, api_sec)             
      req = requests.post((api_url + uri_path), headers=headers, data=data)
      return req

  # returns our holdings
  def get_holdings():
      holdings = kraken_request('/0/private/Balance', {"nonce": str(int(1000*time.time()))}, api_key, api_sec)
      return holdings
      
  # extract balance and do some calculcations according to the trade strategy
  balance = float(get_holdings().json()['result']['ZUSD']) 
  rsi35_balance = balance * 0.015
  rsi30_balance = balance * 0.02
  rsi25_balance = balance * 0.035

  print("USD balance: ", balance)
  print("RSI < 35 balance: ", rsi35_balance)
  print("RSI < 30 balance: ", rsi30_balance)
  print("RSI < 25 balance: ", rsi25_balance)
  
  # set asset pairs and start looping over them
  
  asset_pairs = ['XXBTZUSD', 'XETHZUSD', 'XXRPZUSD', 'ADAUSD', 'SOLUSD', 'MATICUSD', 'AVAXUSD', 'DOTUSD']

  for asset_pair in asset_pairs:

    # set asset code since Kraken asset codes are not consistent
    if asset_pair == "XXBTZUSD":
      asset_code = "XXBT"
    elif asset_pair == "XETHZUSD":
      asset_code = "XETH"
    elif asset_pair == "XXRPZUSD":
      asset_code = "XXRP"
    elif asset_pair == "ADAUSD":
      asset_code = "ADA"
    elif asset_pair == "SOLUSD":
      asset_code = "SOL"
    elif asset_pair == "MATICUSD":
      asset_code = "MATIC"
    elif asset_pair == "AVAXUSD":
      asset_code = "AVAX"
    elif asset_pair == "DOTUSD":
      asset_code = "DOT"

    # function for obtaining OHLC data and getting the close value
    def get_ohlcdata():
        payload = {'pair': asset_pair, 'interval': 60}
        ohlc_data_raw = requests.get('https://api.kraken.com/0/public/OHLC', params=payload)
        # construct a dataframe and assign columns using asset ohlc data
        df = pd.DataFrame(ohlc_data_raw.json()['result'][asset_pair])
        df.columns = ['unixtimestap', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
        # we are only interested in asset close data, so create var for close data columns and set var type as float
        close_data = df['close'].astype(float) # set close data to float
        return close_data

    # function to display RSI (tradingview calculcation)
    def rsi_tradingview(period: int = 14, round_rsi: bool = True):
        delta = get_ohlcdata().diff()
        up = delta.copy()
        up[up < 0] = 0
        up = pd.Series.ewm(up, alpha=1/period).mean()
        down = delta.copy()
        down[down > 0] = 0
        down *= -1
        down = pd.Series.ewm(down, alpha=1/period).mean()
        rsi = np.where(up == 0, 0, np.where(down == 0, 100, 100 - (100 / (1 + up / down))))
        return np.round(rsi, 2) if round_rsi else rsi

    # set variable for hourly BTC RSI
    rsi  = rsi_tradingview()
    hourly_rsi = float(rsi[-1])
    # hourly_rsi = 88

    # print RSI values
    print("1H RSI", asset_pair, ":", hourly_rsi)

    # function for obtaining asset info
    def get_asset():
        payload = {'pair': asset_pair}
        asset = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
        return asset
    
    # function for buying asset_pair
    def buy_asset():
        print("Buying the following amount of", asset_pair, ":", volume_to_buy)
        buy_order = kraken_request('/0/private/AddOrder', {
            "nonce": str(int(1000*time.time())),
            "ordertype": "market",
            "type": "buy",
            "volume": volume_to_buy,
            "pair": asset_pair
        }, api_key, api_sec)
        return buy_order

    def sell_asset():
        print("Selling the following amount of", asset_pair, ":", volume_to_sell)
        sell_order = kraken_request('/0/private/AddOrder', {
            "nonce": str(int(1000*time.time())),
            "ordertype": "market",
            "type": "sell",
            "volume": volume_to_sell,
            "pair": asset_pair
        }, api_key, api_sec)
        return sell_order

    # buy asset
    if 30 <= hourly_rsi <= 35:
      print("Buying", asset_pair, "because RSI is:", hourly_rsi)
      ask_value = get_asset().json()['result'][asset_pair]['a'][0]
      current_ask_value = float(ask_value)
      volume_to_buy = str(rsi35_balance / current_ask_value)
      if not buy_asset().json()['error']:
        print("Bought", volume_to_buy, "of", asset_pair)
      else:
        print("An error occured when trying to place a", asset_pair, "buy order")
    elif 25 <= hourly_rsi <= 30:
      print("Buying", asset_pair, "because RSI is:", hourly_rsi)
      ask_value = get_asset().json()['result'][asset_pair]['a'][0]
      current_ask_value = float(ask_value)
      volume_to_buy = str(rsi30_balance / current_ask_value)
      if not buy_asset().json()['error']:
        print("Bought", volume_to_buy, "of", asset_pair)
      else:
        print("An error occured when trying to place a", asset_pair, "buy order")
    elif hourly_rsi < 25:
      print("Buying", asset_pair, "because RSI is:", hourly_rsi)
      ask_value = get_asset().json()['result'][asset_pair]['a'][0]
      current_ask_value = float(ask_value)
      volume_to_buy = str(rsi25_balance / current_ask_value)
      if not buy_asset().json()['error']:
        print("Bought", volume_to_buy, "of", asset_pair)
      else:
        print("An error occured when trying to place a", asset_pair, "buy order")
    # sell 33% of asset
    elif 68 <= hourly_rsi <= 75: # sell 33% of assets if RSI is between 70 and 77
      if asset_code in get_holdings().json()['result']: # check whether asset is present in our holdings
        if float(get_holdings().json()['result'][asset_code]) > 0: # check whether we actually have more than 0
          print("Selling 33% of", asset_pair, "because RSI is:", hourly_rsi)
          volume_to_sell = str(float(get_holdings().json()['result'][asset_code]) * 0.33)
          if not sell_asset().json()['error']:
            print("Sold", volume_to_sell, "of", asset_pair)
          else:
            print("An error occured when trying to place a", asset_pair, "sell order:")
        else:
          print("No", asset_pair, "to sell because we own 0 of it")
      else:
        print("No", asset_pair, "to sell because we don't have it in our holdings")
    # sell all holdings of asset
    elif hourly_rsi > 75: # sell all assets
      if asset_code in get_holdings().json()['result']: # check whether asset is present in our holdings
        if float(get_holdings().json()['result'][asset_code]) > 0: # check whether we actually have more than 0
          print("Selling all of our", asset_pair, "because RSI is:", hourly_rsi)
          volume_to_sell = str(float(get_holdings().json()['result'][asset_code]))
          if not sell_asset().json()['error']:
            print("Sold", volume_to_sell, "of", asset_pair)
          else:
            print("An error occured when trying to place a", asset_pair, "sell order:")
        else:
          print("No", asset_pair, "to sell because we own 0 of it")
      else:
        print("No", asset_pair, "to sell because we don't have it in our holdings")
    else:
      print("Nothing to do, printing stats")
  print("Current date/time:", time.asctime())
  # print asset stats
  print("Current asset holdings:", get_holdings().json()['result'])
  print("Checking back again in an hour")
  time.sleep(3600)
