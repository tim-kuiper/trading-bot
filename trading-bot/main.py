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
    total_asset_file = asset_pair + "_assets.json"
    total_buy_orders_file = asset_pair + "_buy_orders.json"

    # create asset files if they dont exist
    if not Path(asset_bought_file).exists():
      asset_bought_value = []
      asset_bought_value_json = json.dumps(asset_bought_value, indent=4) 
      with open(asset_bought_file, 'w') as f:
          f.write(asset_bought_value_json)
    
    if not Path(total_asset_file).exists():
      total_assets = []
      total_assets_json = json.dumps(total_assets, indent=4)
      with open(total_asset_file, 'w') as f:
          f.write(total_assets_json)
    
    if not Path(total_buy_orders_file).exists():
      total_asset_buy_orders = []
      total_asset_buy_orders_json = json.dumps(total_asset_buy_orders, indent=4)
      with open(total_buy_orders_file, 'w') as f:
          f.write(total_buy_orders_json)

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
    # hourly_rsi = float(rsi[-1])
    hourly_rsi = 38

    # print RSI values
    print("1H RSI", asset_pair, ":", hourly_rsi)

    # function for returning volume of asset_pair to buy according to our strategy
    def get_volumetobuy()
        payload = {'pair': asset_pair}
        request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
        ask_value = request.json()['result'][asset_pair]['a'][0]
        current_ask_value = float(ask_value)
        volume_to_buy = str(rsi37_balance / current_ask_value)
        return volume_to_buy
        
    
    # function for buying asset_pair
    def buy_asset():
        get_volumetobuy()
        print("Buying the following amount of", asset_pair, ":", volume_to_buy)
        resp = kraken_request('/0/private/AddOrder', {
            "nonce": str(int(1000*time.time())),
            "ordertype": "market",
            "type": "buy",
            "volume": volume_to_buy,
            "pair": asset_pair
        }, api_key, api_sec)
        return resp

    # function for writing bought asset to total_asset_file, needs volume_to_buy var from get_volumetobuy()
    def write_to_assets_file()
        file = open(total_assets_file, 'r')
        file_contents = file.read()
        assets_data = json.loads(file_contents)
        assets_data.append(float(volume_to_buy))
        print("Appending", volume_to_buy, "to", total_asset_file)
        assets_json = json.dumps(assets_data, indent=4)
        with open(total_asset_file, 'w') as f:
            f.write(assets_json)
        print("Appended", volume_to_buy, "to", total_asset_file)

    # buy asset
    if 30 <= hourly_rsi <= 37:
      print("Buying", asset_pair, "because RSI is:", hourly_rsi)
      buy_asset()
    if not resp.json()['error']:
      write_to_assets_file()
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
    print("Nothing to do for ETH, printing stats")
    print("Current date/time:", time.asctime())
  # XRP block  
  if 30 <= hourly_rsi_xrp <= 37:
    print("Buying XRP because RSI is:", hourly_rsi_xrp)
    payload = {'pair': asset_pair_xrp}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair_xrp]['a'][0]
    current_xrp_ask_value = float(ask_value)
    xrp_to_buy = str(rsi37_balance / current_xrp_ask_value)
    print("Buying the following amount of XRP:", xrp_to_buy)
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": xrp_to_buy,
        "pair": asset_pair_xrp
    }, api_key, api_sec)
    if not resp.json()['error']:
      print("Succesfully bought", xrp_to_buy, "XRP")
      assets_file = open('xrp_assets.json', 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      assets_data.append(float(xrp_to_buy))
      print("Current XRP assets_data:", assets_data)
      assets_json = json.dumps(assets_data, indent=4)
      print("XRP assets_json:", assets_json)
      with open('xrp_assets.json', 'w') as f:
          f.write(assets_json)
      print("Added", xrp_to_buy, "to XRP asset list")
      print("Adding USDT value of XRP", current_xrp_ask_value, "to xrp_bought.json")
      xrp_value_file = open('xrp_bought.json', 'r')
      xrp_value_contents = xrp_value_file.read()
      xrp_value_data = json.loads(xrp_value_contents)
      xrp_value_data.append(current_xrp_ask_value)
      xrp_value_json = json.dumps(xrp_value_data, indent=4)
      with open('xrp_bought.json', 'w') as f:
          f.write(xrp_value_json)
      print("Added USDT value of XRP", current_xrp_ask_value, "to xrp_bought.json")
    else:
      print('The following error occured when trying to place a XRP buy order:', resp.json()['error'])
  elif 25 <= hourly_rsi_xrp <= 30:
    print("Buying XRP because RSI is:", hourly_rsi_xrp)
    payload = {'pair': asset_pair_xrp}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair_xrp]['a'][0]
    current_xrp_ask_value = float(ask_value)
    xrp_to_buy = str(rsi30_balance / current_xrp_ask_value)
    print("Buying the following amount of XRP:", xrp_to_buy)
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": xrp_to_buy,
        "pair": asset_pair_xrp
    }, api_key, api_sec)
    if not resp.json()['error']:
      print("Succesfully bought", xrp_to_buy, "XRP")
      assets_file = open('xrp_assets.json', 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      assets_data.append(float(xrp_to_buy))
      print("Current XRP assets_data:", assets_data)
      assets_json = json.dumps(assets_data, indent=4)
      print("XRP assets_json:", assets_json)
      with open('xrp_assets.json', 'w') as f:
          f.write(assets_json)
      print("Added", xrp_to_buy, "to XRP asset list")
      print("Adding USDT value of XRP", current_xrp_ask_value, "to xrp_bought.json")
      xrp_value_file = open('xrp_bought.json', 'r')
      xrp_value_contents = xrp_value_file.read()
      xrp_value_data = json.loads(xrp_value_contents)
      xrp_value_data.append(current_xrp_ask_value)
      xrp_value_json = json.dumps(xrp_value_data, indent=4)
      with open('xrp_bought.json', 'w') as f:
          f.write(xrp_value_json)
      print("Added USDT value of XRP", current_xrp_ask_value, "to xrp_bought.json")
    else:
      print('The following error occured when trying to place a XRP buy order:', resp.json()['error'])
  elif hourly_rsi_xrp < 25:
    print("Buying XRP because RSI is:", hourly_rsi_xrp)
    payload = {'pair': asset_pair_xrp}
    request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    ask_value = request.json()['result'][asset_pair_xrp]['a'][0]
    current_xrp_ask_value = int(float(ask_value))
    xrp_to_buy = str(rsi25_balance / current_xrp_ask_value)
    print("Buying the following amount of XRP:", xrp_to_buy)
    resp = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": xrp_to_buy,
        "pair": asset_pair_xrp
    }, api_key, api_sec)
    if not resp.json()['error']:
      print("Succesfully bought", xrp_to_buy, "XRP")
      assets_file = open('xrp_assets.json', 'r')
      assets_contents = assets_file.read()
      assets_data = json.loads(assets_contents)
      assets_data.append(float(xrp_to_buy))
      print("Current XRP assets_data:", assets_data)
      assets_json = json.dumps(assets_data, indent=4)
      print("XRP assets_json:", assets_json)
      with open('xrp_assets.json', 'w') as f:
          f.write(assets_json)
      print("Added", xrp_to_buy, "to XRP asset list")
      print("Adding USDT value of XRP", current_xrp_ask_value, "to xrp_bought.json")
      xrp_value_file = open('xrp_bought.json', 'r')
      xrp_value_contents = xrp_value_file.read()
      xrp_value_data = json.loads(xrp_value_contents)
      xrp_value_data.append(current_xrp_ask_value)
      xrp_value_json = json.dumps(xrp_value_data, indent=4)
      with open('xrp_bought.json', 'w') as f:
          f.write(xrp_value_json)
      print("Added USDT value of XRP", current_xrp_ask_value, "to xrp_bought.json")
    else:
      print('The following error occured when trying to place a XRP buy order:', resp.json()['error'])
  elif 70 <= hourly_rsi_xrp <= 77: # sell 33% of XRP assets if RSI is between 70 and 77
    assets_file = open('xrp_assets.json', 'r')
    assets_contents = assets_file.read()
    assets_data = json.loads(assets_contents)
    if assets_data: # sell if we have any XRP assets
      print("Selling XRP because RSI is:", hourly_rsi_xrp)
      payload = {'pair': asset_pair_xrp}
      request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
      bid_value = request.json()['result'][asset_pair_xrp]['b'][0]
      current_xrp_bid_value = int(float(bid_value))
      print("Current XRP assets_data:", assets_data)
      xrp_to_sell = str(sum(assets_data) * 0.33)
      print("Selling", xrp_to_sell, "of XRP")
      resp = kraken_request('/0/private/AddOrder', {
          "nonce": str(int(1000*time.time())),
          "ordertype": "market",
          "type": "sell",
          "volume": xrp_to_sell,
          "pair": asset_pair_xrp
      }, api_key, api_sec)
      if not resp.json()['error']:
        print("Sold", xrp_to_sell, "of XRP" )
        print("Substracting", xrp_to_sell, "xrp_assets.json")
        remaining_assets = [(float(sum(assets_data)) - float(xrp_to_sell))]
        remaining_assets_json = json.dumps(remaining_assets, indent=4)
        with open('xrp_assets.json', 'w') as f:
            f.write(remaining_assets_json)
        print("Substraction done")
    else:
      print("No XRP assets to sell")
  elif hourly_rsi_xrp > 77: # sell all XRP assets
    assets_file = open('xrp_assets.json', 'r')
    assets_contents = assets_file.read()
    assets_data = json.loads(assets_contents)
    if assets_data:
      print("Selling all XRP assets because RSI is:", hourly_rsi_xrp)
      payload = {'pair': asset_pair_xrp}
      request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
      bid_value = request.json()['result'][asset_pair_xrp]['b'][0]
      current_xrp_bid_value = int(float(bid_value))
      print("Current XRP assets_data:", assets_data)
      xrp_to_sell = str(sum(assets_data))
      print("Selling", xrp_to_sell, "of XRP")
      resp = kraken_request('/0/private/AddOrder', {
          "nonce": str(int(1000*time.time())),
          "ordertype": "market",
          "type": "sell",
          "volume": xrp_to_sell,
          "pair": asset_pair_xrp
      }, api_key, api_sec)
      if not resp.json()['error']:
        print("Clearing assets list xrp_assets.json")
        clear_assets = assets_data.clear()
        clear_assets_json = json.dumps(clear_assets, indent=4)
        with open('xrp_assets.json', 'w') as f:
            f.write(clear_assets_json)
        print("Asset list xrp_assets.json cleared")
        print("Clearing bought XRP list xrp_bought.json")
        xrp_value_file = open('xrp_bought.json', 'r')
        xrp_value_contents = xrp_value_file.read()
        xrp_value_data = json.loads(xrp_value_contents)
        xrp_value_clear = xrp_value_data.clear()
        xrp_value_json = json.dumps(xrp_value_clear, indent=4)
        with open('xrp_bought.json', 'w') as f:
            f.write(xrp_value_json)
        print("Cleared xrp_bought.json list")
    else:
      print("No XRP assets to sell")
  else:
    print("Nothing to do for XRP, printing stats")
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
  # print XRP stats
  assets_file_xrp = open('xrp_assets.json', 'r')
  assets_contents_xrp = assets_file_xrp.read()
  assets_data_xrp = json.loads(assets_contents_xrp)
  print("assets_data_xrp:", assets_data_xrp)
  print("Total XRP bought so far:", sum(assets_data_xrp))
  xrp_value_file = open('xrp_bought.json', 'r')
  xrp_value_contents = xrp_value_file.read()
  xrp_value_data = json.loads(xrp_value_contents)
  if xrp_value_data:
    print("Average price of XRP bought:", statistics.mean(xrp_value_data))
  print("Checking back again in an hour")
  time.sleep(3600)
