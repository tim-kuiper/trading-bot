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
Trading script utilizing the Kraken API to buy/sell BTCUSDT on RSI for DCA
Notes:
- Using Kraken API key 
- Based on 1H BTCUSDT chart, executing a potential buy with the following properties:
  - If a trade is executed (BTC is bought) then the value of BTC in USDT during execution is stored in a list
- List values should be stored and each hour the avg of this list should be printed, indicating the avg price that BTC was bought for
'''

# set vars
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_sec = os.environ['api_sec_env']
api_key = os.environ['api_key_env']
api_url = "https://api.kraken.com"
btc_bought_file = Path("btc_bought.json")
btc_assets_file = Path("btc_assets.json")
total_buy_orders_file = Path("btc_buy_orders.json")



# create json files to store our data in
# creates the files if they dont exist

if btc_bought_file.exists():
  btc_bought_value = []
  btc_bought_value_json = json.dumps(btc_bought_value, indent=4) 
  with open('btc_bought.json', 'w') as f:
      f.write(btc_bought_value_json)

if btc_assets_file.exists():
  btc_assets = []
  btc_assets_json = json.dumps(btc_assets, indent=4)
  with open('btc_assets.json', 'w') as f:
      f.write(btc_assets_json)

if total_buy_orders_file.exists():
  total_buy_orders = []
  total_buy_orders_json = json.dumps(total_buy_orders, indent=4)
  with open('btc_buy_orders.json', 'w') as f:
      f.write(total_buy_orders_json)


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
  
  # set asset pair
  asset_pair = 'XBTUSDT'
  
  print("Total balance: ", balance)
  print("DCA balance: ", dca_balance)
  print("RSI < 37 balance: ", rsi37_balance)
  print("RSI < 30 balance: ", rsi30_balance)
  print("RSI < 25 balance: ", rsi25_balance)
  
  # get ohcl (open/high/close/low) data from kraken using the hourly (1H) interval
  ohlc_data_raw = requests.get('https://api.kraken.com/0/public/OHLC?pair=XBTUSDT&interval=60')
  
  # construct a dataframe and assign columns using ohlc data
  df = pd.DataFrame(ohlc_data_raw.json()['result']['XBTUSDT'])
  df.columns = ['unixtimestap', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
  
  # we are only interested in the close data, so create var for close data columns and set var type as float
  close_data = df['close'].astype(float) # set close data to float
  
  # define function to display RSI (tradingview calculcation)
  def rsi_tradingview(period: int = 14, round_rsi: bool = True):
      delta = close_data.diff()
      up = delta.copy()
      up[up < 0] = 0
      up = pd.Series.ewm(up, alpha=1/period).mean()
      down = delta.copy()
      down[down > 0] = 0
      down *= -1
      down = pd.Series.ewm(down, alpha=1/period).mean()
      rsi = np.where(up == 0, 0, np.where(down == 0, 100, 100 - (100 / (1 + up / down))))
      return np.round(rsi, 2) if round_rsi else rsi
  
  # set variable for hourly rsi
  rsi = rsi_tradingview()
  hourly_rsi = float(rsi[-1])
  # hourly_rsi = 29.54
  
  print("1H RSI:", hourly_rsi)
  
  if 30 <= hourly_rsi <= 37:
    print("Buying BTC because RSI is:", hourly_rsi)
    payload = {'pair': asset_pair}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair]['a'][0]
    current_btc_ask_value = float(ask_value)
    btc_to_buy = str(rsi37_balance / current_btc_ask_value)
    print("Buying the following amount of BTC:", btc_to_buy)
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": btc_to_buy,
        "pair": asset_pair
    }, api_key, api_sec)
    if not resp.json()['error']:
      print("Succesfully bought", btc_to_buy, "BTC")
      assets_file = open('btc_assets.json', 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      assets_data.append(float(btc_to_buy))
      print("assets_data:", assets_data)
      assets_json = json.dumps(assets_data, indent=4)
      print("assets_json:", assets_json)
      with open('btc_assets.json', 'w') as f:
          f.write(assets_json)
      print("Added", btc_to_buy, "to asset list")
      print("Adding USDT value of BTC", current_btc_ask_value, "to btc_bought.json")
      btc_value_file = open('btc_bought.json', 'r')
      btc_value_contents = btc_value_file.read()
      btc_value_data = json.loads(btc_value_contents)
      btc_value_data.append(current_btc_ask_value)
      btc_value_json = json.dumps(btc_value_data, indent=4)
      with open('btc_bought.json', 'w') as f:
          f.write(btc_value_json)
      print("Added USDT value of BTC", current_btc_ask_value, "to btc_bought.json")
    else:
      print('The following error occured when trying to place a buy order:', resp.json()['error'])
  elif 25 <= hourly_rsi <= 30:
    print("Buying BTC because RSI is:", hourly_rsi)
    payload = {'pair': asset_pair}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair]['a'][0]
    # current_btc_ask_value = int(float(ask_value))
    current_btc_ask_value = float(ask_value)
    btc_to_buy = str(rsi30_balance / current_btc_ask_value)
    print("Buying the following amount of BTC:", btc_to_buy)
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": btc_to_buy,
        "pair": asset_pair
    }, api_key, api_sec)
    if not resp.json()['error']:
      print("Succesfully bought", btc_to_buy, "BTC")
      assets_file = open('btc_assets.json', 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      assets_data.append(float(btc_to_buy))
      print("assets_data:", assets_data)
      assets_json = json.dumps(assets_data, indent=4)
      print("assets_json:", assets_json)
      with open('btc_assets.json', 'w') as f:
          f.write(assets_json)
      print("Added", btc_to_buy, "to asset list")
      print("Adding USDT value of BTC", current_btc_ask_value, "to btc_bought.json")
      btc_value_file = open('btc_bought.json', 'r')
      btc_value_contents = btc_value_file.read()
      btc_value_data = json.loads(btc_value_contents)
      btc_value_data.append(current_btc_ask_value)
      btc_value_json = json.dumps(btc_value_data, indent=4)
      with open('btc_bought.json', 'w') as f:
          f.write(btc_value_json)
      print("Added USDT value of BTC", current_btc_ask_value, "to btc_bought.json")
    else:
      print('The following error occured when trying to place a buy order:', resp.json()['error'])
  elif hourly_rsi < 25:
    print("Buying BTC because RSI is:", hourly_rsi)
    payload = {'pair': asset_pair}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair]['a'][0]
    current_btc_ask_value = int(float(ask_value))
    btc_to_buy = str(rsi25_balance / current_btc_ask_value)
    print("Buying the following amount of BTC:", btc_to_buy)
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": btc_to_buy,
        "pair": asset_pair
    }, api_key, api_sec)
    if not resp.json()['error']:
      print("Succesfully bought", btc_to_buy, "BTC")
      assets_file = open('btc_assets.json', 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      assets_data.append(float(btc_to_buy))
      print("assets_data:", assets_data)
      assets_json = json.dumps(assets_data, indent=4)
      print("assets_json:", assets_json)
      with open('btc_assets.json', 'w') as f:
          f.write(assets_json)
      print("Added", btc_to_buy, "to asset list")
      print("Adding USDT value of BTC", current_btc_ask_value, "to btc_bought.json")
      btc_value_file = open('btc_bought.json', 'r')
      btc_value_contents = btc_value_file.read()
      btc_value_data = json.loads(btc_value_contents)
      btc_value_data.append(current_btc_ask_value)
      btc_value_json = json.dumps(btc_value_data, indent=4)
      with open('btc_bought.json', 'w') as f:
          f.write(btc_value_json)
      print("Added USDT value of BTC", current_btc_ask_value, "to btc_bought.json")
    else:
      print('The following error occured when trying to place a buy order:', resp.json()['error'])
  elif 70 <= hourly_rsi <= 77: # sell 33% of btc assets if RSI is between 70 and 77
    assets_file = open('btc_assets.json', 'r')
    assets_contents = assets_file.read()
    assets_data = json.loads(assets_contents)
    if assets_data: # sell if we have any BTC assets
      print("Selling BTC because RSI is:", hourly_rsi)
      payload = {'pair': asset_pair}
      request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
      bid_value = request.json()['result'][asset_pair]['b'][0]
      current_btc_bid_value = int(float(bid_value))
      print("assets_data:", assets_data)
      btc_to_sell = str(sum(assets_data) * 0.33)
      resp = kraken_request('/0/private/AddOrder', {
          "nonce": str(int(1000*time.time())),
          "ordertype": "market",
          "type": "sell",
          "volume": btc_to_sell,
          "pair": asset_pair
      }, api_key, api_sec)
      if not resp.json()['error']:
        print("Sold", btc_to_sell, "of BTC" )
        print("Substracting", btc_to_sell, "btc_assets.json")
        remaining_assets = (float(sum(assets_data)) - float(btc_to_sell))
        remaining_assets_json = json.dumps(remaining_assets, indent=4)
        with open('btc_assets.json', 'w') as f:
            f.write(remaining_assets_json)
        print("Substraction done")
    else:
      print("No BTC assets to sell")
  elif hourly_rsi > 77: # sell all btc assets
    assets_file = open('btc_assets.json', 'r')
    assets_contents = assets_file.read()
    assets_data = json.loads(assets_contents)
    if assets_data:
      print("Selling all BTC assets because RSI is:", hourly_rsi)
      payload = {'pair': asset_pair}
      request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
      bid_value = request.json()['result'][asset_pair]['b'][0]
      current_btc_bid_value = int(float(bid_value))
      print("assets_data:", assets_data)
      btc_to_sell = str(sum(assets_data))
      resp = kraken_request('/0/private/AddOrder', {
          "nonce": str(int(1000*time.time())),
          "ordertype": "market",
          "type": "sell",
          "volume": btc_to_sell,
          "pair": asset_pair
      }, api_key, api_sec)
      if not resp.json()['error']:
        print("Clearing assets list btc_assets.json")
        clear_assets = assets_data.clear()
        clear_assets_json = json.dumps(clear_assets, indent=4)
        with open('btc_assets.json', 'w') as f:
            f.write(clear_assets_json)
        print("Asset list btc_assets.json cleared")
        print("Clearing bought btc list btc_bought.json")
        btc_value_file = open('btc_bought.json', 'r')
        btc_value_contents = btc_value_file.read()
        btc_value_data = json.loads(btc_value_contents)
        btc_value_clear = btc_value_data.clear()
        btc_value_json = json.dumps(btc_value_clear, indent=4)
        with open('btc_bought.json', 'w') as f:
            f.write(btc_value_json)
        print("Cleared btc_bought.json list")
    else:
      print("No BTC assets to sell")
  else:
    print("Nothing to do, printing stats")
    print("Current date/time:", time.asctime())
  assets_file = open('btc_assets.json', 'r')
  assets_contents = assets_file.read()
  assets_data = json.loads(assets_contents)
  print("assets_data:", assets_data)
  print("Total BTC bought so far:", sum(assets_data))
  btc_value_file = open('btc_bought.json', 'r')
  btc_value_contents = btc_value_file.read()
  btc_value_data = json.loads(btc_value_contents)
  if btc_value_data:
    print("Average price of BTC bought:", statistics.mean(btc_value_data))
  print("Total buy orders so far:", len(assets_data))
  print("Checking back again in an hour")
  time.sleep(3600)
