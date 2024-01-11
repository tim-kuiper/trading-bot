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

'''
Trading script utilizing the Kraken API to buy/sell asset pairs based on RSI for DCA
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

  print("Current USD balance: ", balance)
 
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

    # get min order size for asset_pair
    def min_order_size():
        time.sleep(1)
        resp = requests.get('https://api.kraken.com/0/public/AssetPairs')
        minimum_order_size = float(resp.json()['result'][asset_pair]['ordermin'])
        return minimum_order_size

    # function for obtaining OHLC data and getting the close value
    def get_ohlcdata():
        time.sleep(1)
        payload = {'pair': asset_pair, 'interval': 15}
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

    # set variable for RSI
    rsi  = rsi_tradingview()
    hourly_rsi = float(rsi[-1])
    #hourly_rsi = 69

    print("15M RSI", asset_pair, ":", hourly_rsi)

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
    if 25 <= hourly_rsi <= 30:
      print("Buying", asset_pair, "because RSI is:", hourly_rsi)
      volume_to_buy = str(min_order_size())
      if not buy_asset().json()['error']:
        print("Bought", volume_to_buy, "of", asset_pair)
      else:
        print("An error occured when trying to place a", asset_pair, "buy order")
    elif hourly_rsi < 25:
      print("Buying", asset_pair, "because RSI is:", hourly_rsi)
      volume_to_buy = str(float(min_order_size() *1.25))
      if not buy_asset().json()['error']:
        print("Bought", volume_to_buy, "of", asset_pair)
      else:
        print("An error occured when trying to place a", asset_pair, "buy order")
    # sell asset
    elif 68 <= hourly_rsi <= 73: # sell 50% of assets if RSI is between 68 and 73
      if asset_code in get_holdings().json()['result']: # check whether asset is present in our holdings
        if float(get_holdings().json()['result'][asset_code]) > 0: # check whether we actually have more than 0
          volume_to_sell = str(min_order_size())
          print("Selling", volume_to_sell, "of", asset_pair, "holdings because RSI is:", hourly_rsi)
          if float(get_holdings().json()['result'][asset_code]) / float(volume_to_sell) < 2: # sell all of our asset if we cant sell 2 more times of it
            print("Selling all of", asset_pair, "in order to not violate the minimum order size of", min_order_size())
            volume_to_sell = str(float(get_holdings().json()['result'][asset_code]))
            if not sell_asset().json()['error']:
              print("Sold", volume_to_sell, "of", asset_pair)
            else:
              print("An error occured when trying to place a", asset_pair, "sell order:")
          else:
            print("Selling", volume_to_sell, "of", asset_pair,  "because RSI is:", hourly_rsi)
            if not sell_asset().json()['error']:
              print("Sold", volume_to_sell, "of", asset_pair)
            else:
              print("An error occured when trying to place a", asset_pair, "sell order:", sell_asset().json()['error'])
        else:
          print("No", asset_pair, "to sell because we own 0 of it")
      else:
        print("No", asset_pair, "to sell because we don't have it in our holdings")
    elif 73 <= hourly_rsi <= 80:
      if asset_code in get_holdings().json()['result']: # check whether asset is present in our holdings
        if float(get_holdings().json()['result'][asset_code]) > 0: # check whether we actually have more than 0
          volume_to_sell = str(float(min_order_size() * 1.25))
          if float(get_holdings().json()['result'][asset_code]) / float(volume_to_sell) < 2: # sell all of our asset if we cant sell 2 more times of it
            print("Selling all of", asset_pair, "in order to not exceed the minimum order size of", min_order_size())
            volume_to_sell = str(float(get_holdings().json()['result'][asset_code]))
            if not sell_asset().json()['error']:
              print("Sold all of", asset_pair, "(",volume_to_sell,")")
            else:
              print("An error occured when trying to place a", asset_pair, "sell order:", sell_asset().json()['error'])
          else:
            print("Selling", volume_to_sell, "of", asset_pair,  "because RSI is:", hourly_rsi)
            if not sell_asset().json()['error']:
              print("Sold", volume_to_sell, "of", asset_pair)
            else:
              print("An error occured when trying to place a", asset_pair, "sell order:", sell_asset().json()['error'])
        else:
          print("No", asset_pair, "to sell because we own 0 of it")
      else:
        print("No", asset_pair, "to sell because we don't have it in our holdings")
    elif hourly_rsi > 80:
      if asset_code in get_holdings().json()['result']: # check whether asset is present in our holdings
        if float(get_holdings().json()['result'][asset_code]) > 0: # check whether we actually have more than 0
          volume_to_sell = str(float(get_holdings().json()['result'][asset_code]))
          print("Selling all of asset", asset_pair, "with the amount of", volume_to_sell, "because RSI is:", hourly_rsi)
          if not sell_asset().json()['error']:
            print("Sold", volume_to_sell, "of", asset_pair)
          else:
            print("An error occured when trying to place a", asset_pair, "sell order:", sell_asset().json()['error'])
        else:
          print("No", asset_pair, "to sell because we own 0 of it")
      else:
        print("No", asset_pair, "to sell because we don't have it in our holdings")
    else:
      print("Nothing to do, printing stats")
  print("Current date/time:", time.asctime())
  print("Current asset holdings:", get_holdings().json()['result'])
  print("Checking back again in 5 minutes")
  time.sleep(300)
