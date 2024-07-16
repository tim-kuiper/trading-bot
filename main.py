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


'''
Based on https://www.tradingview.com/script/zR9yW6nn-MACD-Crossover-Backtest

Program flow for each asset:
- When MACD hist crosses 0 upwards (-1, 1):
  - Close short position if any (market order)
    - Check if we have any positions (get positions)
      - If we have positions, check if we have a short position (get short position type)
        - If we have a short position, close it with market order type (close short pos)
  - Open long position
    - Open long position using market order type
- When MACD hist crosses 0 downwards (1, -1):
  - Close long position if any (market order)
    - Check if we have any positions (get positions)
      - If we have positions, check if we have a long position (get long position type)
        - If we have a long position, close it with market order type (close long pos)
  - Open short position 
    - Open short pos using market order type


Pyramiding: Adding long/short order in delayed fashion after macd crossover, so we need ordered long/short lists per asset. 
Flow when using pyramiding:
- When MACD hist crosses 0 upwards (-1, 1):
  - 
'''



# set vars
## general vars
asset_dict = {}
asset_pairs = ['XXBTZUSD', 'SOLUSD', 'XETHZUSD']
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_url = "https://api.kraken.com"
tg_token = os.environ['telegram_token']
list_24h = []
start_list_24h = [] # use this list in combination with the regular 24h list in order to execute the 24h block without waiting 24 hours
loop_time_seconds = 86400 # 1d - iteration time for main loop

# functions
def get_asset_vars():
    ## asset pair specific vars
    if asset_pair == "XXBTZUSD":
      asset_code = "XXBT"
      leverage = "5:1"
      api_sec = os.environ['api_sec_env_btc']
      api_key = os.environ['api_key_env_btc']
    if asset_pair == "SOLUSD":
      asset_code = "SOL"
      leverage = "4:1"
      api_sec = os.environ['api_sec_env_sol']
      api_key = os.environ['api_key_env_sol']
    if asset_pair == "XETHZUSD":
      asset_code = "XETH"
      leverage = "5:1"
      api_sec = os.environ['api_sec_env_eth']
      api_key = os.environ['api_key_env_eth']
    return [asset_code, api_sec, api_key, leverage]
    
def send_telegram_message():
    token = tg_token
    chat_id = "481520678"
    message = tg_message
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    requests.get(url) # send message

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

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def get_holdings():
    holdings = kraken_request('/0/private/Balance', {"nonce": str(int(1000*time.time()))}, api_key, api_sec)
    return holdings

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def min_order_size():
    time.sleep(2)
    resp = requests.get('https://api.kraken.com/0/public/AssetPairs')
    minimum_order_size = float(resp.json()['result'][asset_pair]['ordermin'])
    return minimum_order_size

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def get_asset_close():
    time.sleep(2)
    payload = {'pair': asset_pair}
    resp = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    close_value = resp.json()['result'][asset_pair]['c'][0]
    return close_value

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def get_ohlcdata():
    time.sleep(2)
    payload = {'pair': asset_pair, 'interval': interval_time_minutes}
    ohlc_data_raw = requests.get('https://api.kraken.com/0/public/OHLC', params=payload)
    # construct a dataframe and assign columns using asset ohlc data
    df = pd.DataFrame(ohlc_data_raw.json()['result'][asset_pair])
    df.columns = ['unixtimestap', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
    # we are only interested in asset close data, so create var for close data columns and set var type as float
    close_data = df['close'].astype(float) # set close data to float
    return close_data

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
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

#@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
#def get_orderinfo():
#    time.sleep(2)
#    resp = kraken_request('/0/private/QueryOrders', {
#        "nonce": str(int(1000*time.time())),
#        "txid": transaction_id,
#        "trades": True
#    }, api_key, api_sec)
#    return resp

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
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

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
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

def rsi_tradingview(period: int = 14, round_rsi: bool = True):
    # RSI tradingview calculation
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

def get_macd():
    close = get_ohlcdata_macd()
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd_dict = macd.to_dict()
    macd_values = list(macd_dict.values())
    return macd_values[-1]

def get_macdsignal():
    close = get_ohlcdata_macd()
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd_dict = macdsignal.to_dict()
    macd_signal_values = list(macd_dict.values())
    return macd_signal_values[-1]

def get_macdhist():
    close = get_ohlcdata_macd()
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd_dict = macdhist.to_dict()
    macd_hist_values = list(macd_dict.values())
    return macd_hist_values[-1]

# returns last 2 macd hist values for given assetpair/interval as list [x, y]
def get_macdhist_start():
    close = get_ohlcdata_macd()
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd_dict = macdhist.to_dict()
    macd_hist_values = list(macd_dict.values())
    return [macd_hist_values[-2], macd_hist_values[-1]]

def check_create_asset_file():
    global asset_dict
    asset_dict.clear()
    asset_file_exists = os.path.exists(asset_file_path)
    # create file if it doesnt exist, add dictionary per asset to it
    if not asset_file_exists:
      print(f"Asset dict before: {asset_dict}")
      print(f"Asset file {asset_file} doesnt exist , creating one")
      print(f"Asset dict after: {asset_dict}")
      asset_dict.update({asset_pair: {"macd_hist": []}})
      write_to_asset_file()
    else:
      print(f"Asset file {asset_file} exists, reading")
      asset_dict = json.loads(read_asset_file())
      if asset_pair not in asset_dict.keys():
        print(f"Asset dict before: {asset_dict}")
        print(f"Asset pair {asset_pair} not present in asset file {asset_file}, updating file")
        asset_dict.update({asset_pair: {"macd_hist": []}})
        print(f"Asset dict after: {asset_dict}")
        write_to_asset_file()
        print(f"Appended {asset_pair} to {asset_file}")

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def write_to_asset_file():
    f = open(asset_file, "w")
    f.write(json.dumps(asset_dict))
    f.close()

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def read_asset_file():
    f = open(asset_file, "r")
    asset_json = f.read()
    f.close()
    return asset_json

def open_asset_pair_long_position():
    time.sleep(2)
    response = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "reduce_only": False,
        "volume": volume_to_buy,
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
        "volume": volume_to_sell,
        "leverage": leverage,
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

# main loop
while True:
 # start_list_24h.append(24)
 # list_24h.append(24)
 # if len(list_24h) == 24 or len(start_list_24h) == 1:
  timeframe = "1d"
  file_extension = '.json'
  asset_file = timeframe + file_extension 
  asset_file_path = './' + asset_file
  interval_time_minutes = 1440
  interval_time_simple = '1d'
  order_size = 1000
  for asset_pair in asset_pairs:
    api_key = get_asset_vars()[2]
    api_sec = get_asset_vars()[1]
    leverage = get_asset_vars()[3]
    check_create_asset_file()
    print(f"Opening asset file {asset_file}")
    asset_dict = json.loads(read_asset_file())
    macd_hist_list = asset_dict[asset_pair]["macd_hist"] 
    # when macd list is empty
    if len(macd_hist_list) == 0:
      print(f"{interval_time_simple} {asset_pair}: MACD hist list length: {len(asset_dict[asset_pair]['macd_hist'])}, appending 2 MACD hist values")
      macd_hist_tmp = get_macdhist_start()
      macd_hist_list.append(macd_hist_tmp[-2])
      macd_hist_list.append(macd_hist_tmp[-1])
      asset_dict[asset_pair]["macd_hist"] = macd_hist_list
      write_to_asset_file()
      time.sleep(1)
      print(f"{interval_time_simple} {asset_pair}: Appended MACD hist: {macd_hist_list}")
      tg_message = f"{interval_time_simple} {asset_pair}: Appended MACD hist: {macd_hist_list}"
      send_telegram_message()
    if len(macd_hist_list) == 1:
      print(f"{interval_time_simple} {asset_pair}: {macd_hist_list}, appending 1 MACD hist value")
      print(f"{interval_time_simple} {asset_pair}: MACD hist list length: {len(asset_dict[asset_pair]['macd_hist'])}, appending 1 MACD hist value")
      macd_hist_list.append(get_macdhist())
      asset_dict[asset_pair]["macd_hist"] = macd_hist_list
      write_to_asset_file()
      time.sleep(1)
      print(f"{interval_time_simple} {asset_pair}: Appended MACD hist: {macd_hist_list}")
      tg_message = f"{interval_time_simple} {asset_pair}: Appended MACD hist: {macd_hist_list}"
      send_telegram_message()

    # reread asset json
    asset_dict = json.loads(read_asset_file())
    macd_hist_list = asset_dict[asset_pair]["macd_hist"] 

    print(f"{interval_time_simple} {asset_pair} MACD hist list: {macd_hist_list}")
    if macd_hist_list[-2] < 0:
      print(f"{interval_time_simple} {asset_pair}: Watching to buy asset when MACD hist crosses 0")
      if macd_hist_list[-1] < 0:
        print(f"{interval_time_simple} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing")
        macd_hist_list.pop(0)
        asset_dict[asset_pair]["macd_hist"] = macd_hist_list
        write_to_asset_file()
        tg_message = f"{interval_time_simple} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing"
        send_telegram_message()
      elif macd_hist_list[-1] > 0:
        print(f"{interval_time_simple} {asset_pair}: MACD hist crossed 0, closing short position if any and opening long")
        tg_message = f"{interval_time_simple} {asset_pair}: MACD hist crossed 0, closing short position if any and opening long"
        send_telegram_message()
        close_asset_pair_short_positions() # closes all short positions
        asset_close = float(get_asset_close())
        usd_order_size = order_size
        volume_to_buy = str(float(usd_order_size / asset_close))
        order_output = open_asset_pair_long_position() # executes long order
        if not order_output.json()['error']:
          print(f"{interval_time_simple} {asset_pair}: Bought {volume_to_buy}")
          tg_message = order_output.json()['result']
          send_telegram_message()        
          macd_hist_list.pop(0)
          asset_dict[asset_pair]["macd_hist"] = macd_hist_list
          write_to_asset_file()
        else:
          print(f"{interval_time_simple} {asset_pair}: An error occured when trying to place a long order: {order_output.json()['error']}")
          tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to place a long order: {order_output.json()['error']}"
          send_telegram_message()
    elif macd_hist_list[-2] > 0:
      print(f"{interval_time_simple} {asset_pair}: Watching to close long position(sell) when MACD hist crosses 0 and opening a short position")
      if macd_hist_list[-1] > 0:
        print(f"{interval_time_simple} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing")
        macd_hist_list.pop(0)
        asset_dict[asset_pair]["macd_hist"] = macd_hist_list
        write_to_asset_file()
        tg_message = f"{interval_time_simple} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing"
        send_telegram_message()
      elif macd_hist_list[-1] < 0:
        print(f"{interval_time_simple} {asset_pair}: MACD hist crossed 0, closing long position and opening a short one")
        tg_message = f"{interval_time_simple} {asset_pair}: MACD crossed 0 downwards, closing long position and opening a short one"
        send_telegram_message()
        close_asset_pair_long_positions()
        asset_close = float(get_asset_close())
        usd_order_size = order_size
        volume_to_sell = str(float(usd_order_size / asset_close))
        order_output = open_asset_pair_short_position()
        if not order_output.json()['error']:
          macd_hist_list.pop(0)
          asset_dict[asset_pair]["macd_hist"] = macd_hist_list
          write_to_asset_file()
          print(f"{interval_time_simple} {asset_pair}: Closes long position {order_output.json()['result']}")
          tg_message = order_output.json()['result']
          send_telegram_message()        
        else:
          print(f"{interval_time_simple} {asset_pair}: An error occured when trying to place a sell order: {order_output.json()['error']}")
          tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to place a sell order: {order_output.json()['error']}"
          send_telegram_message()
    time.sleep(3) # sleep 3 seconds between asset pair
  #list_24h.clear()
  time.sleep(loop_time_seconds)