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

TODO:
v0.7:
- Trade based on top 5 crypto assets, not BTC only
  - Therefore we need to generalize the code
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
  
  # construct  request to get balance
  resp = kraken_request('/0/private/Balance', {"nonce": str(int(1000*time.time()))}, api_key, api_sec)

  # extract balance and do some calculcations according to the trade strategy
  balance_data = resp.json()
  balance_float = float(balance_data['result']['USDT'])
  balance = int(balance_float)
  dca_balance = int(balance) * 0.75
  rsi37_balance = float(dca_balance) * 0.02
  rsi30_balance = float(dca_balance) * 0.05
  rsi25_balance = float(dca_balance) * 0.07

  print("Total balance: ", balance)
  print("DCA balance: ", dca_balance)
  print("RSI < 37 balance: ", rsi37_balance)
  print("RSI < 30 balance: ", rsi30_balance)
  print("RSI < 25 balance: ", rsi25_balance)
  
  # set asset pairs and start looping over them
  
  asset_pairs = ['XBTUSDT', 'ETHUSDT', 'XRPUSDT', 'ADAUSDT', 'SOLUSDT']

  for asset_pair in asset_pairs:
    # define asset file names
    asset_bought_value_file = asset_pair + "_bought_value.json"
    total_assets_file = asset_pair + "_assets.json"
    total_buy_orders_file = asset_pair + "_buy_orders.json"

    # create asset files if they dont exist
    if not Path(asset_bought_value_file).exists():
      asset_bought_value = []
      asset_bought_value_json = json.dumps(asset_bought_value, indent=4) 
      with open(asset_bought_value_file, 'w') as f:
          f.write(asset_bought_value_json)
    
    if not Path(total_assets_file).exists():
      total_assets = []
      total_assets_json = json.dumps(total_assets, indent=4)
      with open(total_assets_file, 'w') as f:
          f.write(total_assets_json)
    
    if not Path(total_buy_orders_file).exists():
      total_asset_buy_orders = []
      total_asset_buy_orders_json = json.dumps(total_asset_buy_orders, indent=4)
      with open(total_buy_orders_file, 'w') as f:
          f.write(total_asset_buy_orders_json)

    # function for obtaining OHLC data and getting the close value
    def get_ohlcdata():
        payload = {'pair': asset_pair, 'interval': 60}
        ohlc_data_raw = requests.get('https://api.kraken.com/0/public/OHLC', params=payload)
        # construct a dataframe and assign columns using BTC ohlc data
        df = pd.DataFrame(ohlc_data_raw.json()['result'][asset_pair])
        df.columns = ['unixtimestap', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
        # we are only interested in the BTC close data, so create var for close data columns and set var type as float
        close_data = df['close'].astype(float) # set close data to float
        return close_data

    # define function to display RSI (tradingview calculcation)
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
        request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
        return request
    
    # function for buying asset_pair
    def buy_asset():
        print("Buying the following amount of", asset_pair, ":", volume_to_buy)
        resp = kraken_request('/0/private/AddOrder', {
            "nonce": str(int(1000*time.time())),
            "ordertype": "market",
            "type": "buy",
            "volume": volume_to_buy,
            "pair": asset_pair
        }, api_key, api_sec)
        return resp

    def sell_asset():
        print("Selling the following amount of", asset_pair, ":", volume_to_sell)
        resp = kraken_request('/0/private/AddOrder', {
            "nonce": str(int(1000*time.time())),
            "ordertype": "market",
            "type": "sell",
            "volume": volume_to_sell,
            "pair": asset_pair
        }, api_key, api_sec)
        return resp

    # function for writing bought asset to total_asset_file, needs volume_to_buy var from buy_asset()
    def write_to_assets_file():
        file = open(total_assets_file, 'r')
        file_contents = file.read()
        assets_data = json.loads(file_contents)
        assets_data.append(float(volume_to_buy))
        print("Appending", volume_to_buy, "to", total_assets_file)
        assets_json = json.dumps(assets_data, indent=4)
        with open(total_assets_file, 'w') as f:
            f.write(assets_json)
        print("Appended", volume_to_buy, "to", total_assets_file)

    # function for writing bought asset value to file (in USDT), so we can calculate the avg price for which we bought an asset
    def write_to_asset_bought_file():
        print("Adding USDT value of", asset_pair, "with the amount of", current_ask_value, "to", asset_bought_value_file)
        file = open(asset_bought_value_file, 'r')
        file_contents = file.read()
        value_data = json.loads(file_contents)
        value_data.append(current_ask_value)
        value_json = json.dumps(value_data, indent=4)
        with open(asset_bought_value_file, 'w') as f:
            f.write(value_json)
        print("Added USDT value of", current_ask_value, asset_pair, "to", asset_bought_value_file)

    # buy asset
    if 30 <= hourly_rsi <= 37:
      print("Buying", asset_pair, "because RSI is:", hourly_rsi)
      ask_value = get_asset().json()['result'][asset_pair]['a'][0]
      current_ask_value = float(ask_value)
      volume_to_buy = str(rsi37_balance / current_ask_value)
      buy_asset()
      if not get_asset().json()['error']:
        write_to_assets_file()
        write_to_asset_bought_file()
      else:
        print("The following error occured when trying to place a", asset_pair, "buy order:", resp.json()['error'])
    elif 25 <= hourly_rsi <= 30:
      print("Buying", asset_pair, "because RSI is:", hourly_rsi)
      ask_value = get_asset().json()['result'][asset_pair]['a'][0]
      current_ask_value = float(ask_value)
      volume_to_buy = str(rsi30_balance / current_ask_value)
      buy_asset()
      if not get_asset().json()['error']:
        write_to_assets_file()
        write_to_asset_bought_file()
      else:
        print("The following error occured when trying to place a", asset_pair, "buy order:", resp.json()['error'])
    elif hourly_rsi < 25:
      print("Buying", asset_pair, "because RSI is:", hourly_rsi)
      ask_value = get_asset().json()['result'][asset_pair]['a'][0]
      current_ask_value = float(ask_value)
      volume_to_buy = str(rsi25_balance / current_ask_value)
      buy_asset()
      if not get_asset().json()['error']:
        write_to_assets_file()
        write_to_asset_bought_file()
      else:
        print("The following error occured when trying to place a", asset_pair, "buy order:", resp.json()['error'])
    # sell 33% of asset
    elif 70 <= hourly_rsi <= 77: # sell 33% of assets if RSI is between 70 and 77
      assets_file = open(total_assets_file, 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      if assets_data: # sell if we have any assets to sell
        print("Selling 33% of", asset_pair, "because RSI is:", hourly_rsi)
        bid_value = get_asset().json()['result'][asset_pair]['b'][0]
        current_bid_value = int(float(bid_value))
        volume_to_sell = str(sum(assets_data) * 0.33)
        sell_asset()
        if not get_asset().json()['error']:
          print("Sold", volume_to_sell, "of", asset_pair)
          print("Substracting", volume_to_sell, asset_pair, "from", total_assets_file)
          remaining_assets = [(float(sum(assets_data)) - float(volume_to_sell))]
          remaining_assets_json = json.dumps(remaining_assets, indent=4)
          with open(total_assets_file, 'w') as f:
              f.write(remaining_assets_json)
          print("Substracted", volume_to_sell, asset_pair, "from", total_assets_file)
      else:
        print("No", asset_pair, "to sell")
    # sell all holdings of asset
    elif hourly_rsi > 77: # sell all assets
      assets_file = open(total_assets_file, 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      if assets_data:
        print("Selling all of", asset_pair, "because RSI is:", hourly_rsi)
        bid_value = get_asset().json()['result'][asset_pair]['b'][0]
        current_bid_value = int(float(bid_value))
        volume_to_sell = str(sum(assets_data) * 0.33)
        sell_asset()
        if not get_asset().json()['error']:
          print("Sold", volume_to_sell, "of", asset_pair)
          print("Clearing assets list", total_assets_file)
          assets_data.clear()
          clear_assets_json = json.dumps(assets_data, indent=4)
          with open(total_assets_file, 'w') as f:
              f.write(clear_assets_json)
        print("Asset list", total_assets_file, "cleared")
        print("Clearing bought assets list", asset_bought_value_file)
        asset_value_file = open(asset_bought_value_file, 'r')
        asset_value_contents = asset_value_file.read()
        asset_value_data = json.loads(asset_value_contents)
        asset_value_data.clear()
        asset_value_json = json.dumps(asset_value_data, indent=4)
        with open(asset_bought_value_file, 'w') as f:
            f.write(asset_value_json)
        print("Cleared", asset_bought_value_file)
      else:
        print("No", asset_pair, "to sell")
    else:
      print("Nothing to do, printing stats")
      print("Current date/time:", time.asctime())
    # print asset stats
    assets_file = open(total_assets_file, 'r')
    assets_contents = assets_file.read()
    assets_data = json.loads(assets_contents)
    print("Current", asset_pair, "assets:", assets_data)
    if assets_data:
      print("Total", asset_pair,  "bought so far:", sum(assets_data))
    asset_value_file = open(asset_bought_value_file, 'r')
    asset_value_contents = asset_value_file.read()
    asset_value_data = json.loads(asset_value_contents)
    if asset_value_data:
      print("Average price of", asset_pair, "bought:", statistics.mean(asset_value_data))
    print("Checking back again in an hour")
  time.sleep(3600)
