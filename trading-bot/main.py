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
- Using API built from flask able to receive HTTP(S) POST requests from Tradingview in order to obtain RSI value of asset
- Based on 1H BTCUSDT chart, executing a potential buy with the following properties:
  - RSI between 45-30: 0.005*0.75*balance
  - RSI <30: 0.01*0.75*balance
  - If a trade is executed (BTC is bought) then the value of BTC in USDT during execution is stored in a list
- List values should be stored and each hour the avg of this list should be printed, indicating the avg price that BTC was bought for
- When asset is sold, which is will be done manually for the time being, the list must be stored somewhere and a new list should be made starting the above process again
'''

# set vars
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_sec = os.environ['api_sec_env']
api_key = os.environ['api_key_env']
api_url = "https://api.kraken.com"
btc_bought_value = []
btc_assets = []
total_buy_orders = []

# create json files to store our data in
btc_bought_value_json = json.dumps(btc_bought_value, indent=4) 
with open('btc_bought.json', 'w') as f:
    f.write(btc_bought_value_json)
btc_assets_json = json.dumps(btc_assets, indent=4)
with open('btc_assets.json', 'w') as f:
    f.write(btc_assets_json)
total_buy_orders_json = json.dumps(total_buy_orders, indent=4)
with open('btc_buy_orders.json', 'w') as f:
    f.write(btc_buy_orders_json)


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
  rsi37_balance = int(dca_balance) * 0.02
  rsi30_balance = int(dca_balance) * 0.03
  rsi25_balance = int(dca_balance) * 0.05
  
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
  
  print("1H RSI:", hourly_rsi)
  
  if 30 <= hourly_rsi <= 37:
    print("Buying BTC because RSI is:", hourly_rsi)
    # calculate how much btc we can buy according to the strategy, for this we need to convert an X amount of USDT to BTC value
    payload = {'pair': asset_pair}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair]['a'][0]
    current_btc_value = int(float(ask_value))
    btc_to_buy = str(rsi37_balance / current_btc_value)
    print("Buying the following amount of BTC:", btc_to_buy)
    # construct buy order
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": btc_to_buy,
        "pair": asset_pair
    }, api_key, api_sec)
    if not resp.json()['error']:
      # CONT HERE
      btc_assets.append(float(btc_to_buy))
      btc_bought_value.append(current_btc_value)
    else:
      print('The following error occured when trying to place a buy order:', resp.json()['error'])
  elif 25 <= hourly_rsi <= 30:
    print("Buying BTC because RSI is:", hourly_rsi)
    payload = {'pair': asset_pair}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair]['a'][0]
    current_btc_value = int(float(ask_value))
    btc_to_buy = str(rsi30_balance / current_btc_value)
    print("Buying the following amount of BTC:", btc_to_buy)
    # construct buy order
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": btc_to_buy,
        "pair": asset_pair
    }, api_key, api_sec)
    if not resp.json()['error']:
      btc_assets.append(float(btc_to_buy))
      btc_bought_value.append(current_btc_value)
    else:
      print('The following error occured when trying to place a buy order:', resp.json()['error'])
  elif hourly_rsi < 25:
    print("Buying BTC because RSI is:", hourly_rsi)
    payload = {'pair': asset_pair}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair]['a'][0]
    current_btc_value = int(float(ask_value))
    btc_to_buy = str(rsi25_balance / current_btc_value)
    print("Buying the following amount of BTC:", btc_to_buy)
    # construct buy order
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": btc_to_buy,
        "pair": asset_pair
    }, api_key, api_sec)
    if not resp.json()['error']:
      btc_assets.append(float(btc_to_buy))
      btc_bought_value.append(current_btc_value)
    else:
      print('The following error occured when trying to place a buy order:', resp.json()['error'])
  else:
    print("Nothing to do, printing stats")

  print("Total BTC bought so far:", sum(btc_assets))
  if btc_bought_value: # tests if list is not empty
    print("Average price of BTC bought:", statistics.mean(btc_bought_value))
  print("Total buy orders so far:", len(btc_assets))
  print("Checking back again in an hour")
  time.sleep(3600)
