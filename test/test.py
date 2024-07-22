import urllib.parse
import hashlib
import hmac
import base64 
import time
import os
import requests
import json
import pandas as pd
import numpy as np
import talib
import datetime 
from tenacity import *
# set vars
## general vars

asset_dict = {}
asset_pairs = ['XXBTZUSD']
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_url = "https://api.kraken.com"
tg_token = os.environ['telegram_token']
list_1h = []
list_4h = []
list_24h = []
start_list_24h = [] # use this list in combination with the regular 24h list in order to execute the 24h block without waiting a full day
loop_time_seconds = 14400
rsi_lower_boundary = 35
rsi_upper_boundary = 65
interval_time_minutes = 60 # ohlc timeframe

# functions
def get_asset_vars():
    ## asset pair specific vars
    if asset_pair == "XXBTZUSD":
      asset_code = "XXBT"
      api_sec = os.environ['api_sec_env_btc']
      api_key = os.environ['api_key_env_btc']
      leverage = "5:1"
    if asset_pair == "XXRPZUSD":
      asset_code = "XXRP"
      api_sec = os.environ['api_sec_env_xrp']
      api_key = os.environ['api_key_env_xrp']
    if asset_pair == "ADAUSD":
      asset_code = "ADA"
      api_sec = os.environ['api_sec_env_ada']
      api_key = os.environ['api_key_env_ada']
    if asset_pair == "SOLUSD":
      asset_code = "SOL"
      api_sec = os.environ['api_sec_env_sol']
      api_key = os.environ['api_key_env_sol']
    if asset_pair == "XETHZUSD":
      asset_code = "XETH"
      api_sec = os.environ['api_sec_env_eth']
      api_key = os.environ['api_key_env_eth']
    return [asset_code, api_sec, api_key, leverage]

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

def get_ohlcdata_macd():
    time.sleep(2)
    payload = {'pair': asset_pair, 'interval': interval_time_minutes}
    ohlc_data_raw = requests.get('https://api.kraken.com/0/public/OHLC', params=payload)
    # construct a dataframe and assign columns using asset ohlc data
    df = pd.DataFrame(ohlc_data_raw.json()['result'][asset_pair])
    df.columns = ['unixtimestap', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
    # we are only interested in asset close data, so create var for close data columns and set var type as float
    close_data = df['close']
    return close_data

def get_macd():
    close = get_ohlcdata_macd()
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd_dict = macd.to_dict()
    macd_values = list(macd_dict.values())
    return [macd_values[-2], macd_values[-1]]

def get_macdsignal():
    close = get_ohlcdata_macd()
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd_dict = macdsignal.to_dict()
    macd_values = list(macd_dict.values())
    return [macd_values[-2], macd_values[-1]]

def get_macdhist():
    close = get_ohlcdata_macd()
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd_dict = macdhist.to_dict()
    macd_values = list(macd_dict.values())
    return macd_values[-1]

asset_pair_positions =  {}

# get open positions for asset pair
def get_asset_pair_positions():
    # get positions for asset pair
    time.sleep(2)
    # first get all positions
    response = kraken_request('/0/private/OpenPositions', {"nonce": str(int(1000*time.time()))}, api_key, api_sec)
    # loop through positions and get positions for asset pair
    open_positions = response.json()['result']
    for k,v in open_positions.items():
      # print(f"key: {k}, value: {v}")
      if v['pair'] == asset_pair:
        asset_pair_positions.update({k:v})
    return asset_pair_positions
    
def open_asset_pair_long_position():
    time.sleep(2)
    response = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "reduce_only": False,
        "volume": "0.0001",
        "leverage": leverage,
        "pair": asset_pair
    }, api_key, api_sec)
    return response

def open_asset_pair_short_position():
    time.sleep(2)
    response = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "sell",
        "reduce_only": False,
        "volume": "0.0001",
        "leverage": leverage,
        "close[ordertype]": "stop-loss-limit",
        "close[price]": "70000",
        "close[price2]": "72000",
        "pair": asset_pair
    }, api_key, api_sec)
    return response

def close_asset_pair_long_positions():
    time.sleep(2)
    response = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "sell",
        "reduce_only": False,
        "volume": "0", # closes all long positions
        "leverage": leverage, # for btc, construct a dict for asset pair and leverage lvls
        "pair": asset_pair
    }, api_key, api_sec)
    return response
    
def close_asset_pair_short_positions():
    time.sleep(2)
    response = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "reduce_only": False,
        "volume": "0", # closes all short pos
        "leverage": leverage,
        "pair": asset_pair
    }, api_key, api_sec)
    return response

def cancel_order():
   response = kraken_request('/0/private/CancelOrder', {
       "nonce": str(int(1000*time.time())), 
       "txid": "OWF53A-HNVC7-TWDTAG"
   }, api_key, api_sec)
   return response

def query_order_txid():
   response = kraken_request('/0/private/QueryOrders', {
       "nonce": str(int(1000*time.time())), 
       "txid": "OSYA6J-JPWFZ-PREAID"
   }, api_key, api_sec)
   return response

def query_open_orders():
   response = kraken_request('/0/private/OpenOrders', {
       "nonce": str(int(1000*time.time()))
   }, api_key, api_sec)
   return response

while True:
  for asset_pair in asset_pairs:
    api_key = get_asset_vars()[2]
    api_sec = get_asset_vars()[1]
    leverage = get_asset_vars()[3]
    # print(f"Open positions: {get_asset_pair_positions()}")
    # print(f"Close all long pos for {asset_pair}: {close_asset_pair_long_positions().json()}")
    # print(f"Close all short pos for {asset_pair}: {close_asset_pair_short_positions().json()}")
    #  print(f"Open 1 short pos for {asset_pair}: {open_asset_pair_short_position().json()}")
    print(f"Cancellng order for {asset_pair}: {cancel_order().json()}")
    # print(f"Open 1 long pos for {asset_pair}: {open_asset_pair_long_position().json()}")
    # print(f"Create long pos for {asset_pair}: {create_asset_pair_long_position().json()}")
    # print(f"Query open orders: {query_open_orders().json()}")
    time.sleep(5)
