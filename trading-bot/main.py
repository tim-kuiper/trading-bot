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
btc_bought_file = Path("btc_bought.json")
btc_assets_file = Path("btc_assets.json")
total_btc_buy_orders_file = Path("btc_buy_orders.json")
eth_bought_file = Path("eth_bought.json")
eth_assets_file = Path("eth_assets.json")
total_eth_buy_orders_file = Path("eth_buy_orders.json")
xrp_bought_file = Path("xrp_bought.json")
xrp_assets_file = Path("xrp_assets.json")
total_xrp_buy_orders_file = Path("xrp_buy_orders.json")
ada_bought_file = Path("ada_bought.json")
ada_assets_file = Path("ada_assets.json")
total_ada_buy_orders_file = Path("ada_buy_orders.json")
sol_bought_file = Path("sol_bought.json")
sol_assets_file = Path("sol_assets.json")
total_sol_buy_orders_file = Path("sol_buy_orders.json")



# create json files to store our data in
# creates the files if they dont exist

# files related to BTC
if not btc_bought_file.exists():
  btc_bought_value = []
  btc_bought_value_json = json.dumps(btc_bought_value, indent=4) 
  with open('btc_bought.json', 'w') as f:
      f.write(btc_bought_value_json)

if not btc_assets_file.exists():
  btc_assets = []
  btc_assets_json = json.dumps(btc_assets, indent=4)
  with open('btc_assets.json', 'w') as f:
      f.write(btc_assets_json)

if not total_btc_buy_orders_file.exists():
  total_btc_buy_orders = []
  total_btc_buy_orders_json = json.dumps(total_btc_buy_orders, indent=4)
  with open('btc_buy_orders.json', 'w') as f:
      f.write(total_btc_buy_orders_json)

# files related to ETH
if not eth_bought_file.exists():
  eth_bought_value = []
  eth_bought_value_json = json.dumps(eth_bought_value, indent=4) 
  with open('eth_bought.json', 'w') as f:
      f.write(eth_bought_value_json)

if not eth_assets_file.exists():
  eth_assets = []
  eth_assets_json = json.dumps(eth_assets, indent=4)
  with open('eth_assets.json', 'w') as f:
      f.write(eth_assets_json)

if not total_eth_buy_orders_file.exists():
  total_eth_buy_orders = []
  total_eth_buy_orders_json = json.dumps(total_eth_buy_orders, indent=4)
  with open('eth_buy_orders.json', 'w') as f:
      f.write(total_eth_buy_orders_json)

# files related to XRP
# files related to ADA
# files related to SOL

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
  print(balance_data)
  balance_float = float(balance_data['result']['USDT'])
  balance = int(balance_float)
  dca_balance = int(balance) * 0.75
  # rsi37_balance = float(dca_balance) * 0.02
  rsi37_balance = float(dca_balance) * 0.01 # for testing purposes
  rsi30_balance = float(dca_balance) * 0.05
  rsi25_balance = float(dca_balance) * 0.07

  print("Total balance: ", balance)
  print("DCA balance: ", dca_balance)
  print("RSI < 37 balance: ", rsi37_balance)
  print("RSI < 30 balance: ", rsi30_balance)
  print("RSI < 25 balance: ", rsi25_balance)
  
  # set asset pairs
  asset_pair_btc = 'XBTUSDT'
  asset_pair_sol = 'SOLUSDT'
  asset_pair_ada = 'ADAUSDT'
  asset_pair_eth = 'ETHUSDT'
  asset_pair_xrp = 'XRPUSDT'
  
  # get 1H BTC OHLC data
  payload = {'pair': asset_pair_btc, 'interval': 60}
  ohlc_data_raw_btc = requests.get('https://api.kraken.com/0/public/OHLC', params=payload)

  # get 1H ETH OHLC data
  payload = {'pair': asset_pair_eth, 'interval': 60}
  ohlc_data_raw_eth = requests.get('https://api.kraken.com/0/public/OHLC', params=payload)
  
  # construct a dataframe and assign columns using BTC ohlc data
  df_btc = pd.DataFrame(ohlc_data_raw_btc.json()['result'][asset_pair_btc])
  df_btc.columns = ['unixtimestap', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']

  # construct a dataframe and assign columns using ETH ohlc data
  df_eth = pd.DataFrame(ohlc_data_raw_eth.json()['result'][asset_pair_eth])
  df_eth.columns = ['unixtimestap', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
  
  # we are only interested in the BTC close data, so create var for close data columns and set var type as float
  close_data_btc = df_btc['close'].astype(float) # set close data to float

  # we are only interested in the ETH close data, so create var for close data columns and set var type as float
  close_data_eth = df_eth['close'].astype(float) # set close data to float
  
  # define function to display BTC RSI (tradingview calculcation)
  def rsi_tradingview_btc(period: int = 14, round_rsi: bool = True):
      delta = close_data_btc.diff()
      up = delta.copy()
      up[up < 0] = 0
      up = pd.Series.ewm(up, alpha=1/period).mean()
      down = delta.copy()
      down[down > 0] = 0
      down *= -1
      down = pd.Series.ewm(down, alpha=1/period).mean()
      rsi = np.where(up == 0, 0, np.where(down == 0, 100, 100 - (100 / (1 + up / down))))
      return np.round(rsi, 2) if round_rsi else rsi

  # define function to display ETH RSI (tradingview calculcation)
  def rsi_tradingview_eth(period: int = 14, round_rsi: bool = True):
      delta = close_data_eth.diff()
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
  rsi_btc = rsi_tradingview_btc()
  # hourly_rsi_btc = float(rsi_btc[-1])
  hourly_rsi_btc = 36

  # set variable for hourly ETH RSI
  rsi_eth = rsi_tradingview_eth()
  # hourly_rsi_eth = float(rsi_eth[-1])
  hourly_rsi_eth = 36 
  
  print("1H RSI BTC:", hourly_rsi_btc)
  print("1H RSI ETH:", hourly_rsi_eth)

  # BTC block  
  if 30 <= hourly_rsi_btc <= 37:
    print("Buying BTC because RSI is:", hourly_rsi_btc)
    payload = {'pair': asset_pair_btc}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair_btc]['a'][0]
    current_btc_ask_value = float(ask_value)
    btc_to_buy = str(rsi37_balance / current_btc_ask_value)
    print("Buying the following amount of BTC:", btc_to_buy)
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": btc_to_buy,
        "pair": asset_pair_btc
    }, api_key, api_sec)
    if not resp.json()['error']:
      print("Succesfully bought", btc_to_buy, "BTC")
      assets_file = open('btc_assets.json', 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      assets_data.append(float(btc_to_buy))
      print("Current BTC assets_data:", assets_data)
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
      print('The following error occured when trying to place a BTC buy order:', resp.json()['error'])
  elif 25 <= hourly_rsi_btc <= 30:
    print("Buying BTC because RSI is:", hourly_rsi_btc)
    payload = {'pair': asset_pair_btc}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair_btc]['a'][0]
    current_btc_ask_value = float(ask_value)
    btc_to_buy = str(rsi30_balance / current_btc_ask_value)
    print("Buying the following amount of BTC:", btc_to_buy)
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": btc_to_buy,
        "pair": asset_pair_btc
    }, api_key, api_sec)
    if not resp.json()['error']:
      print("Succesfully bought", btc_to_buy, "BTC")
      assets_file = open('btc_assets.json', 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      assets_data.append(float(btc_to_buy))
      print("Current BTC assets_data:", assets_data)
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
      print('The following error occured when trying to place a BTC buy order:', resp.json()['error'])
  elif hourly_rsi_btc < 25:
    print("Buying BTC because RSI is:", hourly_rsi_btc)
    payload = {'pair': asset_pair_btc}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair_btc]['a'][0]
    current_btc_ask_value = int(float(ask_value))
    btc_to_buy = str(rsi25_balance / current_btc_ask_value)
    print("Buying the following amount of BTC:", btc_to_buy)
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": btc_to_buy,
        "pair": asset_pair_btc
    }, api_key, api_sec)
    if not resp.json()['error']:
      print("Succesfully bought", btc_to_buy, "BTC")
      assets_file = open('btc_assets.json', 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      assets_data.append(float(btc_to_buy))
      print("Current BTC assets_data:", assets_data)
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
      print('The following error occured when trying to place a BTC buy order:', resp.json()['error'])
  elif 70 <= hourly_rsi_btc <= 77: # sell 33% of btc assets if RSI is between 70 and 77
    assets_file = open('btc_assets.json', 'r')
    assets_contents = assets_file.read()
    assets_data = json.loads(assets_contents)
    if assets_data: # sell if we have any BTC assets
      print("Selling BTC because RSI is:", hourly_rsi_btc)
      payload = {'pair': asset_pair_btc}
      request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
      bid_value = request.json()['result'][asset_pair_btc]['b'][0]
      current_btc_bid_value = int(float(bid_value))
      print("Current BTC assets_data:", assets_data)
      btc_to_sell = str(sum(assets_data) * 0.33)
      print("Selling", btc_to_sell, "of BTC")
      resp = kraken_request('/0/private/AddOrder', {
          "nonce": str(int(1000*time.time())),
          "ordertype": "market",
          "type": "sell",
          "volume": btc_to_sell,
          "pair": asset_pair_btc
      }, api_key, api_sec)
      if not resp.json()['error']:
        print("Sold", btc_to_sell, "of BTC" )
        print("Substracting", btc_to_sell, "btc_assets.json")
        remaining_assets = [(float(sum(assets_data)) - float(btc_to_sell))]
        remaining_assets_json = json.dumps(remaining_assets, indent=4)
        with open('btc_assets.json', 'w') as f:
            f.write(remaining_assets_json)
        print("Substraction done")
    else:
      print("No BTC assets to sell")
  elif hourly_rsi_btc > 77: # sell all btc assets
    assets_file = open('btc_assets.json', 'r')
    assets_contents = assets_file.read()
    assets_data = json.loads(assets_contents)
    if assets_data:
      print("Selling all BTC assets because RSI is:", hourly_rsi_btc)
      payload = {'pair': asset_pair_btc}
      request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
      bid_value = request.json()['result'][asset_pair_btc]['b'][0]
      current_btc_bid_value = int(float(bid_value))
      print("Current BTC assets_data:", assets_data)
      btc_to_sell = str(sum(assets_data))
      print("Selling", btc_to_sell, "of BTC")
      resp = kraken_request('/0/private/AddOrder', {
          "nonce": str(int(1000*time.time())),
          "ordertype": "market",
          "type": "sell",
          "volume": btc_to_sell,
          "pair": asset_pair_btc
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
    print("Nothing to do for BTC, printing stats")
    print("Current date/time:", time.asctime())

  # ETH block
  if 30 <= hourly_rsi_eth <= 37:
    print("Buying ETH because RSI is:", hourly_rsi_eth)
    payload = {'pair': asset_pair_eth}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair_eth]['a'][0]
    current_eth_ask_value = float(ask_value)
    eth_to_buy = str(rsi37_balance / current_eth_ask_value)
    print("Buying the following amount of ETH:", eth_to_buy)
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": eth_to_buy,
        "pair": asset_pair_eth
    }, api_key, api_sec)
    if not resp.json()['error']:
      print("Succesfully bought", eth_to_buy, "ETH")
      assets_file = open('eth_assets.json', 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      assets_data.append(float(eth_to_buy))
      print("Current ETH assets_data:", assets_data)
      assets_json = json.dumps(assets_data, indent=4)
      print("assets_json:", assets_json)
      with open('eth_assets.json', 'w') as f:
          f.write(assets_json)
      print("Added", eth_to_buy, "to asset list")
      print("Adding USDT value of ETH", current_eth_ask_value, "to eth_bought.json")
      eth_value_file = open('eth_bought.json', 'r')
      eth_value_contents = eth_value_file.read()
      eth_value_data = json.loads(eth_value_contents)
      eth_value_data.append(current_eth_ask_value)
      eth_value_json = json.dumps(eth_value_data, indent=4)
      with open('eth_bought.json', 'w') as f:
          f.write(eth_value_json)
      print("Added USDT value of ETH", current_eth_ask_value, "to eth_bought.json")
    else:
      print('The following error occured when trying to place a ETH buy order:', resp.json()['error'])
  elif 25 <= hourly_rsi_eth <= 30:
    print("Buying ETH because RSI is:", hourly_rsi_eth)
    payload = {'pair': asset_pair_eth}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair_eth]['a'][0]
    current_eth_ask_value = float(ask_value)
    eth_to_buy = str(rsi30_balance / current_eth_ask_value)
    print("Buying the following amount of ETH:", eth_to_buy)
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": eth_to_buy,
        "pair": asset_pair_eth
    }, api_key, api_sec)
    if not resp.json()['error']:
      print("Succesfully bought", eth_to_buy, "ETH")
      assets_file = open('eth_assets.json', 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      assets_data.append(float(eth_to_buy))
      print("Current ETH assets_data:", assets_data)
      assets_json = json.dumps(assets_data, indent=4)
      print("assets_json:", assets_json)
      with open('eth_assets.json', 'w') as f:
          f.write(assets_json)
      print("Added", eth_to_buy, "to asset list")
      print("Adding USDT value of ETH", current_eth_ask_value, "to eth_bought.json")
      eth_value_file = open('eth_bought.json', 'r')
      eth_value_contents = eth_value_file.read()
      eth_value_data = json.loads(eth_value_contents)
      eth_value_data.append(current_eth_ask_value)
      eth_value_json = json.dumps(eth_value_data, indent=4)
      with open('eth_bought.json', 'w') as f:
          f.write(eth_value_json)
      print("Added USDT value of ETH", current_eth_ask_value, "to eth_bought.json")
    else:
      print('The following error occured when trying to place a ETH buy order:', resp.json()['error'])
  elif hourly_rsi_eth < 25:
    print("Buying ETH because RSI is:", hourly_rsi_eth)
    payload = {'pair': asset_pair_eth}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair_eth]['a'][0]
    current_eth_ask_value = int(float(ask_value))
    eth_to_buy = str(rsi25_balance / current_eth_ask_value)
    print("Buying the following amount of ETH:", eth_to_buy)
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": eth_to_buy,
        "pair": asset_pair_eth
    }, api_key, api_sec)
    if not resp.json()['error']:
      print("Succesfully bought", eth_to_buy, "ETH")
      assets_file = open('eth_assets.json', 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      assets_data.append(float(eth_to_buy))
      print("Current ETH assets_data:", assets_data)
      assets_json = json.dumps(assets_data, indent=4)
      print("assets_json:", assets_json)
      with open('eth_assets.json', 'w') as f:
          f.write(assets_json)
      print("Added", eth_to_buy, "to asset list")
      print("Adding USDT value of ETH", current_eth_ask_value, "to eth_bought.json")
      eth_value_file = open('eth_bought.json', 'r')
      eth_value_contents = eth_value_file.read()
      eth_value_data = json.loads(eth_value_contents)
      eth_value_data.append(current_eth_ask_value)
      eth_value_json = json.dumps(eth_value_data, indent=4)
      with open('eth_bought.json', 'w') as f:
          f.write(eth_value_json)
      print("Added USDT value of ETH", current_eth_ask_value, "to eth_bought.json")
    else:
      print('The following error occured when trying to place a ETH buy order:', resp.json()['error'])
  elif 70 <= hourly_rsi_eth <= 77: # sell 33% of eth assets if RSI is between 70 and 77
    assets_file = open('eth_assets.json', 'r')
    assets_contents = assets_file.read()
    assets_data = json.loads(assets_contents)
    if assets_data: # sell if we have any ETH assets
      print("Selling ETH because RSI is:", hourly_rsi_eth)
      payload = {'pair': asset_pair_eth}
      request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
      bid_value = request.json()['result'][asset_pair_eth]['b'][0]
      current_eth_bid_value = int(float(bid_value))
      print("Current ETH assets_data:", assets_data)
      eth_to_sell = str(sum(assets_data) * 0.33)
      print("Selling", eth_to_sell, "of ETH")
      resp = kraken_request('/0/private/AddOrder', {
          "nonce": str(int(1000*time.time())),
          "ordertype": "market",
          "type": "sell",
          "volume": eth_to_sell,
          "pair": asset_pair_eth
      }, api_key, api_sec)
      if not resp.json()['error']:
        print("Sold", eth_to_sell, "of ETH" )
        print("Substracting", eth_to_sell, "eth_assets.json")
        remaining_assets = [(float(sum(assets_data)) - float(eth_to_sell))]
        remaining_assets_json = json.dumps(remaining_assets, indent=4)
        with open('eth_assets.json', 'w') as f:
            f.write(remaining_assets_json)
        print("Substraction done")
    else:
      print("No ETH assets to sell")
  elif hourly_rsi_eth > 77: # sell all ETH assets
    assets_file = open('eth_assets.json', 'r')
    assets_contents = assets_file.read()
    assets_data = json.loads(assets_contents)
    if assets_data:
      print("Selling all ETH assets because RSI is:", hourly_rsi_eth)
      payload = {'pair': asset_pair_eth}
      request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
      bid_value = request.json()['result'][asset_pair_eth]['b'][0]
      current_eth_bid_value = int(float(bid_value))
      print("Current ETH assets_data:", assets_data)
      eth_to_sell = str(sum(assets_data))
      print("Selling", eth_to_sell, "of ETH")
      resp = kraken_request('/0/private/AddOrder', {
          "nonce": str(int(1000*time.time())),
          "ordertype": "market",
          "type": "sell",
          "volume": eth_to_sell,
          "pair": asset_pair_eth
      }, api_key, api_sec)
      if not resp.json()['error']:
        print("Clearing assets list eth_assets.json")
        clear_assets = assets_data.clear()
        clear_assets_json = json.dumps(clear_assets, indent=4)
        with open('eth_assets.json', 'w') as f:
            f.write(clear_assets_json)
        print("Asset list eth_assets.json cleared")
        print("Clearing bought eth list btc_bought.json")
        eth_value_file = open('eth_bought.json', 'r')
        eth_value_contents = eth_value_file.read()
        eth_value_data = json.loads(eth_value_contents)
        eth_value_clear = eth_value_data.clear()
        eth_value_json = json.dumps(eth_value_clear, indent=4)
        with open('eth_bought.json', 'w') as f:
            f.write(eth_value_json)
        print("Cleared eth_bought.json list")
    else:
      print("No ETH assets to sell")
  else:
    print("Nothing to do for BTC and ETH, printing stats")
    print("Current date/time:", time.asctime())
  # print BTC stats
  assets_file_btc = open('btc_assets.json', 'r')
  assets_contents_btc = assets_file_btc.read()
  assets_data_btc = json.loads(assets_contents_btc)
  print("assets_data_btc:", assets_data_btc)
  print("Total BTC bought so far:", sum(assets_data_btc))
  btc_value_file = open('btc_bought.json', 'r')
  btc_value_contents = btc_value_file.read()
  btc_value_data = json.loads(btc_value_contents)
  if btc_value_data:
    print("Average price of BTC bought:", statistics.mean(btc_value_data))
  # print ETH stats
  assets_file_eth = open('eth_assets.json', 'r')
  assets_contents_eth = assets_file_eth.read()
  assets_data_eth = json.loads(assets_contents_eth)
  print("assets_data_eth:", assets_data_eth)
  print("Total ETH bought so far:", sum(assets_data_eth))
  eth_value_file = open('eth_bought.json', 'r')
  eth_value_contents = eth_value_file.read()
  eth_value_data = json.loads(eth_value_contents)
  if eth_value_data:
    print("Average price of ETH bought:", statistics.mean(eth_value_data))
  print("Checking back again in an hour")
  time.sleep(3600)
