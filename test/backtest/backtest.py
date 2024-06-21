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
interval_time_minutes = 240 # 4h timeframe
data_dict = {}
balance_usd = 5000

# functions
def get_asset_vars():
    ## asset pair specific vars
    if asset_pair == "XXBTZUSD":
      asset_code = "XXBT"
      api_sec = os.environ['api_sec_env_btc']
      api_key = os.environ['api_key_env_btc']
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
    time.sleep(2)
    payload = {'pair': asset_pair, 'interval': interval_time_minutes}
    ohlc_data_raw = requests.get('https://api.kraken.com/0/public/OHLC', params=payload)
    # construct a dataframe and assign columns using asset ohlc data
    df = pd.DataFrame(ohlc_data_raw.json()['result'][asset_pair])
    df.columns = ['unixtimestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
    # we are only interested in asset close data, so create var for close data columns and set var type as float
    # close_data = df['close']
    # return close_data
    return df

def get_close():
    time.sleep(2)
    ohlc_data = get_ohlc()
    close_data = ohlc_data['close'].astype(float)
    return close_data

def get_time():
    time.sleep(2)
    ohlc_data = get_ohlc()
    time_data_dict = ohlc_data['unixtimestamp'].to_dict()
    time_data_list = list(time_data_dict.values())
    time_data_list_datetime = []
    for i in time_data_list:
      normal_time_unformatted = datetime.datetime.utcfromtimestamp(i)
      normal_time = normal_time_unformatted.strftime('%Y-%m-%d %H:%M:%S')
      time_data_list_datetime.append(normal_time)
    return time_data_list_datetime

def get_macd():
    # close = get_ohlcdata_macd()
    close = get_close()
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd_dict = macd.to_dict()
    macd_values = list(macd_dict.values())
    # return macd_values[-1]
    return macd_values

def get_rsi(period: int = 14, round_rsi: bool = True):
    # RSI tradingview calculation
    close_data = get_close()
    # delta = get_ohlc().diff()
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

def get_asset_amount():
    buy_amount_usd = 200
    asset_amount_list = []
    close_list = get_close().tolist()
    for i in close_list:
      asset_amount_list.append(float(buy_amount_usd)/float(i))
    return asset_amount_list

for asset_pair in asset_pairs:
  holdings = []
  api_key = get_asset_vars()[2]
  api_sec = get_asset_vars()[1]
  # data_dict = dict({"Time": get_time(), "MACD": get_macd(), "RSI": get_rsi()})
  time_list = get_time()
  macd_list = get_macd()
  rsi_list = get_rsi().tolist()
  close_list = get_close().tolist()
  amount_list = get_asset_amount()
  rsi_list_temp = []
  macd_list_temp = []
  amount_list_temp = []
  holdings_list = []
  price_bought_list = []
  for (time, macd, rsi, close, amount) in zip(time_list, macd_list, rsi_list, close_list, amount_list):
    #print(f"{time}, {macd}, {rsi}, {close}, {amount}")
    # print(f"Balance USD: {balance_usd}")
    is_macd_float = isinstance(macd,float)
    if 0 < rsi < 100 and is_macd_float:
      print(f"rsi {rsi} and macd {macd}")
      if len(rsi_list_temp) == 1:
        if rsi_list_temp[0] < rsi_lower_boundary:
          rsi = rsi_list_temp[0]
        elif rsi_list_temp[0] > rsi_upper_boundary:
          rsi = rsi_list_temp[0]
        else:
          rsi_list_temp.clear()
          rsi_list_temp.append(rsi)
      elif len(rsi_list_temp) == 0:
        rsi_list_temp.append(rsi)
      if rsi < rsi_lower_boundary and len(macd_list_temp) < 3:
        macd_list_temp.append(macd)
      if rsi < rsi_lower_boundary and len(macd_list_temp) >= 3:
        if macd_list_temp[-3] < macd_list_temp[-2] < macd_list_temp[-1]:
          print(f"Buy asset")
          holdings_list.append(amount)
          print(f"Holdings list: {holdings_list}")
          price_bought_list.append(close)
          macd_list_temp.clear()
          rsi_list_temp.clear()
        else:
          macd_list_temp.append(macd)
      elif rsi > rsi_upper_boundary and len(macd_list_temp) < 3:
        macd_list_temp.append(macd)
      elif rsi > rsi_upper_boundary and len(macd_list_temp) >= 3:
        if macd_list_temp[-3] > macd_list_temp[-2] > macd_list_temp[-1]:
          if float(sum(holdings_list)) > 0:
            price_bought_avg = sum(price_bought_list) / len(price_bought_list)
            if close > price_bought_avg:
              usd_sold = sum(holdings_list) * close
              balance_usd = balance_usd + usd_sold
              print(f"Balance USD: {balance_usd}")
              macd_list_temp.clear()
              rsi_list_temp.clear()
              price_bought_list.clear()
            else:
              print(f"Avg too low")
              macd_list_temp.clear()
              rsi_list_temp.clear()
        else:
          macd_list_temp.clear()
          rsi_list_temp.clear()
      else:
        macd_list_temp.clear()
        rsi_list_temp.clear()
    else:
      print(f"Incorrect test for macd {macd} and rsi {rsi}") 
