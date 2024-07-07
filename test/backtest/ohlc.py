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
import itertools
# set vars
## general vars

asset_dict = {}
# asset_pairs = ['XXBTZUSD', 'XXRPZUSD', 'XETHZUSD', 'ADAUSD', 'SOLUSD']
asset_pairs = ['XXBTZUSD']
pd.options.display.max_rows = 999 
pd.options.display.max_columns = 8 
api_url = "https://api.kraken.com"
loop_time_seconds = 14400
rsi_lower_boundary = 25
rsi_upper_boundary = 75
interval_time_minutes = 240 # 4h timeframe
# interval_time_minutes = 1440 # 1d timeframe
# interval_time_minutes = 10080 # 1w timeframe
# interval_time_minutes = 60 # 1h timeframe
#interval_time_minutes = 15 # 15m timeframe
data_dict = {}
balance_usd = 5000
order_size = 400 

# functions
def get_asset_vars():
    ## asset pair specific vars
    if asset_pair == "XXBTZUSD":
      asset_code = "XXBT"
      api_sec = os.environ['api_sec_env_btc']
      api_key = os.environ['api_key_env_btc']
    return [asset_code, api_sec, api_key]

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

def get_ohlc():
    date_time = datetime.datetime(2021, 7, 26, 21, 20)
    unix = int(time.mktime(date_time.timetuple()))
    time.sleep(2)
    payload = {'pair': asset_pair, 'interval': interval_time_minutes, 'since': unix}
    ohlc_data_raw = requests.get('https://api.kraken.com/0/public/OHLC', params=payload)
    # construct a dataframe and assign columns using asset ohlc data
    df = pd.DataFrame(ohlc_data_raw.json()['result'][asset_pair])
    df.columns = ['unixtimestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
    # we are only interested in asset close data, so create var for close data columns and set var type as float
    # close_data = df['close']
    # return close_data
    return df

for asset_pair in asset_pairs:
  ohlc = get_ohlc()
  print(ohlc)
