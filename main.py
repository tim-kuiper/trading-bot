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
asset_pairs = ['XXBTZUSD', 'SOLUSD', 'XETHZUSD']
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_url = "https://api.kraken.com"
tg_token = os.environ['telegram_token']
list_24h = [] # 1d
#list_168h = [] # 1w
#list_360h = [] # 15d
#start_list_24h = [] # use this list in combination with the regular 24h list in order to execute the 24h block without waiting 24 hours
#start_list_168h = [] # use this list in combination with the regular 168h list in order to execute the 168h block without waiting 168 hours
#start_list_360h = [] # use this list in combination with the regular 360h list in order to execute the 360h block without waiting 360 hours
loop_time_seconds = 86400 # 1d - iteration time for main loop

# functions
def get_asset_vars():
    ## asset pair specific vars
    if asset_pair == "XXBTZUSD":
      asset_code = "XXBT"
      leverage = "5:1"
      api_sec = os.environ['api_sec_env_btc']
      api_key = os.environ['api_key_env_btc']
      asset_pair_short = "XBTUSD"
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
    return [asset_code, api_sec, api_key, leverage, asset_pair_short]
    
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

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def get_orderinfo():
    time.sleep(2)
    resp = kraken_request('/0/private/QueryOrders', {
        "nonce": str(int(1000*time.time())),
        "txid": transaction_id,
        "trades": True
    }, api_key, api_sec)
    return resp

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def buy_asset():
    time.sleep(2)
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
    time.sleep(2)
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

def open_increase_long_pos():
    time.sleep(2)
    response = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "reduce_only": False,
        "volume": order_volume,
        "leverage": leverage,
        "close[ordertype]": "stop-loss-limit",
        "close[price]": sll_trigger, # sll trigger price
        "close[price2]": sll_limit, # sll limit price
        "pair": asset_pair
    }, api_key, api_sec)
    return response

def open_increase_short_pos():
    time.sleep(2)
    response = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "sell",
        "reduce_only": False,
        "volume": order_volume,
        "leverage": leverage,
        "close[ordertype]": "stop-loss-limit",
        "close[price]": sll_trigger, # sll trigger price
        "close[price2]": sll_limit, # sll limit price
        "pair": asset_pair
    }, api_key, api_sec)
    return response

def close_short_pos():
    time.sleep(2)
    response = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "reduce_only": False,
        "volume": "0",
        "leverage": leverage,
        "pair": asset_pair
    }, api_key, api_sec)
    return response

def close_long_pos():
    time.sleep(2)
    response = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "sell",
        "reduce_only": False,
        "volume": "0",
        "leverage": leverage,
        "pair": asset_pair
    }, api_key, api_sec)

def cancel_order():
   time.sleep(2)
   response = kraken_request('/0/private/CancelOrder', {
       "nonce": str(int(1000*time.time())), 
       "txid": order_txid
   }, api_key, api_sec)
   return response

def query_open_orders():
   time.sleep(2)
   response = kraken_request('/0/private/OpenOrders', {
       "nonce": str(int(1000*time.time()))
   }, api_key, api_sec)
   return response

def query_open_pos():
   response = kraken_request('/0/private/OpenPositions', {
       "nonce": str(int(1000*time.time()))
   }, api_key, api_sec)
   return response

# main loop
while True:
  #start_list_168h.append(168)
  #start_list_360h.append(360)
  list_24h.append(24)
  #list_168h.append(168)
  #list_360h.append(360)
  if len(list_24h) == 1:
    timeframe = "1d"
    interval_time_minutes = 1440
    interval_time_simple = '1d'
    # order_size = 1200
    order_size = 10
    sll_short_trigger_pct = 1.09 # trigger pct from current price
    sll_short_limit_pct = 1.10 # limit pct from current price
    sll_long_trigger_pct = 0.91 # trigger pct from current price
    sll_long_limit_pct = 0.90 # limit pct from current price
    for asset_pair in asset_pairs:
      api_key = get_asset_vars()[2]
      api_sec = get_asset_vars()[1]
      leverage = get_asset_vars()[3]
      asset_pair_short = get_asset_vars()[4]
      if len(macd_hist_list) == 0:
        print(f"{interval_time_simple} {asset_pair}: MACD hist list length: {len(asset_dict[asset_pair]['macd_hist'])}, appending 2 MACD hist values")
        macd_hist_tmp = get_macdhist_start()
        macd_hist_list.append(macd_hist_tmp[-2])
        macd_hist_list.append(macd_hist_tmp[-1])
        asset_dict[asset_pair]["macd_hist"] = macd_hist_list
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
      margin_pos_txid_list = asset_dict[asset_pair]["margin_pos_txid"]
      conditional_order_txid_list = asset_dict[asset_pair]["conditional_order_txid"]
      print(f"{interval_time_simple} {asset_pair} MACD hist list: {macd_hist_list}")
      # for testing purposes
      macd_hist_list = [-1, 1] # buy
      # macd_hist_list = [1, -1] # sell
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
          print(f"{interval_time_simple} {asset_pair}: MACD hist crossed 0, closing short pos if any and opening long pos")
          tg_message = f"{interval_time_simple} {asset_pair}: MACD hist crossed 0, closing short pos if any and opening long pos"
          send_telegram_message()
          # check if short txid list and conditional txid list arent empty
          if not margin_pos_txid_list and not conditional_order_txid_list:
            # close or reduce short pos with amount in holdings short list
            order_output = close_short_pos()
            if not order_output.json()['error']:
              margin_pos_txid_list.clear()
              write_to_asset_file()
              print(f"Succesfully closed {asset_pair} short position: {order_output.json()}")
              tg_message = f"Succesfully closed {asset_pair} short position: {order_output.json()}"
              send_telegram_message()
              # cancel corresponding SLL order
              asset_dict = json.loads(read_asset_file())
              macd_hist_list = asset_dict[asset_pair]["macd_hist"] 
              margin_pos_txid_list = asset_dict[asset_pair]["margin_pos_txid"]
              conditional_order_txid_list = asset_dict[asset_pair]["conditional_order_txid"]
              order_txid = conditional_order_txid_list[0]
              order_output = cancel_order()
              if not order_output.json()['error']:
                conditional_order_txid_list.clear() 
                asset_dict[asset_pair]['conditional_order_txid'] = conditional_order_txid_list
                write_to_asset_file()
                print(f"Succesfully cleared {asset_pair} SLL order: {order_output.json()}")
                tg_message = f"Succesfully cleared {asset_pair} SLL order: {order_output.json()}"
                send_telegram_message()
                # Going long on asset
                print(f"Opening long pos for {asset_pair}")
                asset_close = float(get_asset_close())
                usd_order_size = order_size
                order_volume = str(float(usd_order_size / asset_close))
                sll_trigger = str(round(float(asset_close * sll_long_trigger_pct), 1))
                sll_limit = str(round(float(asset_close * sll_long_limit_pct), 1))
                order_output = open_increase_long_pos()
                if not order_output.json()['error']:
                  print(f"{interval_time_simple} {asset_pair}: Opened long pos: {order_output.json()['result']}")
                  tg_message = f"{interval_time_simple} {asset_pair}: Opened long pos: {order_output.json()['result']}"
                  send_telegram_message()
                  transaction_id = order_output.json()['result']['txid'][0]
                  order_info = get_orderinfo()
                  asset_dict = json.loads(read_asset_file())
                  macd_hist_list = asset_dict[asset_pair]["macd_hist"] 
                  margin_pos_txid_list = asset_dict[asset_pair]["margin_pos_txid"]
                  conditional_order_txid_list = asset_dict[asset_pair]["conditional_order_txid"]
                  macd_hist_list.pop(0)
                  asset_dict[asset_pair]["macd_hist"] = macd_hist_list
                  write_to_asset_file()
                else:
                  print(f"{interval_time_simple} {asset_pair}: An error occured when trying to open a long pos: {order_output.json()['error']}")
                  tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to open a long pos: {order_output.json()['error']}"
                  send_telegram_message()
                  macd_hist_list.pop(0)
                  asset_dict[asset_pair]["macd_hist"] = macd_hist_list
                  write_to_asset_file()
              else:
                print(f"{interval_time_simple} {asset_pair}: An error occured when trying to cancel a SLL order: {order_output.json()['error']}")
                tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to cancel a SLL order: {order_output.json()['error']}"
                send_telegram_message()
                macd_hist_list.pop(0)
                asset_dict[asset_pair]["macd_hist"] = macd_hist_list
                write_to_asset_file()
            else:
              print(f"{interval_time_simple} {asset_pair}: An error occured when trying to reduce/close a short position: {order_output.json()['error']}")
              tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to reduce/close a short position: {order_output.json()['error']}"
              send_telegram_message()
              macd_hist_list.pop(0)
              asset_dict[asset_pair]["macd_hist"] = macd_hist_list
              write_to_asset_file()
          else:
            print(f"{interval_time_simple} {asset_pair}: No margin txid or SLL txid present, opening long pos")
            tg_message = f"{interval_time_simple} {asset_pair}: No margin txid or SLL txid present, opening long pos"
            send_telegram_message()
            asset_close = float(get_asset_close())
            usd_order_size = order_size
            order_volume = str(float(usd_order_size / asset_close))
            sll_trigger = str(round(float(asset_close * sll_long_trigger_pct), 1))
            sll_limit = str(round(float(asset_close * sll_long_limit_pct), 1))
            order_output = open_increase_long_pos()
            if not order_output.json()['error']:
              print(f"{interval_time_simple} {asset_pair}: Opened long pos: {order_output.json()['result']}")
              tg_message = f"{interval_time_simple} {asset_pair}: Opened long pos: {order_output.json()['result']}"
              send_telegram_message()
              transaction_id = order_output.json()['result']['txid'][0]
              order_info = get_orderinfo()
              asset_dict = json.loads(read_asset_file())
              macd_hist_list = asset_dict[asset_pair]["macd_hist"] 
              margin_pos_txid_list = asset_dict[asset_pair]["margin_pos_txid"]
              conditional_order_txid_list = asset_dict[asset_pair]["conditional_order_txid"]
              # add margin txid and sll txid to asset dict lists
              margin_txid = order_output.json()['result']['txid'][0]
              open_orders = query_open_orders().json()
              for key, value in open_orders['result']['open'].items():
                print(f"Key: {key}, Value: {value['refid']}")
                if margin_txid == value['refid']:
                  print(f"Found a match")
                  conditional_order_txid = key
              margin_pos_txid_list.append(margin_txid)
              conditional_order_txid_list.append(conditional_order_txid)
              macd_hist_list.pop(0)
              asset_dict[asset_pair]["macd_hist"] = macd_hist_list
              asset_dict[asset_pair]["margin_pos_txid"] = margin_pos_txid_list
              asset_dict[asset_pair]["conditional_order_txid"] = conditional_order_txid_list
              write_to_asset_file()
            else:
              print(f"{interval_time_simple} {asset_pair}: An error occured when trying to open a long pos: {order_output.json()['error']}")
              tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to open a long pos: {order_output.json()['error']}"
              send_telegram_message()
              macd_hist_list.pop(0)
              asset_dict[asset_pair]["macd_hist"] = macd_hist_list
              write_to_asset_file()
      elif macd_hist_list[-2] > 0:
        print(f"{interval_time_simple} {asset_pair}: Watching to sell asset when MACD hist crosses 0 and opening a short position")
        if macd_hist_list[-1] > 0:
          print(f"{interval_time_simple} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing")
          macd_hist_list.pop(0)
          asset_dict[asset_pair]["macd_hist"] = macd_hist_list
          write_to_asset_file()
          tg_message = f"{interval_time_simple} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing"
          send_telegram_message()
        elif macd_hist_list[-1] < 0:
          print(f"{interval_time_simple} {asset_pair}: MACD hist crossed 0, closing long pos if any and opening short pos")
          tg_message = f"{interval_time_simple} {asset_pair}: MACD hist crossed 0, closing long pos if any and opening short pos"
          send_telegram_message()
          if not margin_pos_txid_list and not conditional_order_txid_list:
            order_output = close_long_pos()
            if not order_output.json()['error']:
              margin_pos_txid_list.clear()
              write_to_asset_file()
              print(f"Succesfully closed {asset_pair} long pos: {order_output.json()}")
              tg_message = f"Succesfully closed {asset_pair} long pos: {order_output.json()}"
              send_telegram_message()        
              # cancel corresponding SLL order
              asset_dict = json.loads(read_asset_file())
              macd_hist_list = asset_dict[asset_pair]["macd_hist"] 
              margin_pos_txid_list = asset_dict[asset_pair]["margin_pos_txid"]
              conditional_order_txid_list = asset_dict[asset_pair]["conditional_order_txid"]
              order_txid = conditional_order_txid_list[0]
              order_output = cancel_order()
              if not order_output.json()['error']:
                conditional_order_txid_list.clear() 
                asset_dict[asset_pair]['conditional_order_txid'] = conditional_order_txid_list
                write_to_asset_file()
                print(f"Succesfully cleared {asset_pair} SLL order: {order_output.json()}")
                tg_message = f"Succesfully cleared {asset_pair} SLL order: {order_output.json()}"
                send_telegram_message()
                # create/increase short position
                asset_close = float(get_asset_close())
                usd_order_size = order_size
                order_volume = str(float(usd_order_size / asset_close))
                sll_trigger = str(round(float(asset_close * sll_short_trigger_pct), 1))
                sll_limit = str(round(float(asset_close * sll_short_limit_pct), 1))
                order_output = open_increase_short_pos()
                if not order_output.json()['error']:
                  print(f"{interval_time_simple} {asset_pair}: Sucessfully created created/increased short position with SLL: {order_output.json()}")
                  tg_message = f"{interval_time_simple} {asset_pair}: Sucessfully created created/increased short position with SLL: {order_output.json()}"
                  send_telegram_message()
                  asset_dict = json.loads(read_asset_file())
                  macd_hist_list = asset_dict[asset_pair]["macd_hist"] 
                  margin_pos_txid_list = asset_dict[asset_pair]["margin_pos_txid"]
                  conditional_order_txid_list = asset_dict[asset_pair]["conditional_order_txid"]
                  # add short txid and sll txid to asset dict lists
                  margin_txid = order_output.json()['result']['txid'][0]
                  open_orders = query_open_orders().json()
                  for key, value in open_orders['result']['open'].items():
                    print(f"Key: {key}, Value: {value['refid']}")
                    if margin_txid == value['refid']:
                      print(f"Found a match")
                      conditional_order_txid = key
                  margin_pos_txid_list.append(margin_txid)
                  conditional_order_txid_list.append(conditional_order_txid)
                  macd_hist_list.pop(0)
                  asset_dict[asset_pair]["macd_hist"] = macd_hist_list
                  asset_dict[asset_pair]["margin_pos_txid"] = margin_pos_txid_list
                  asset_dict[asset_pair]["conditional_order_txid"] = conditional_order_txid_list
                  write_to_asset_file()
                else:
                  print(f"{interval_time_simple} {asset_pair}: An error occured when trying to create/increase a short position with SLL: {order_output.json()['error']}")
                  tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to create/increase a short position with SLL: {order_output.json()['error']}"
                  send_telegram_message()
                  macd_hist_list.pop(0)
                  asset_dict[asset_pair]["macd_hist"] = macd_hist_list
                  write_to_asset_file()
              else:
                print(f"{interval_time_simple} {asset_pair}: An error occured when trying to cancel a SLL order: {order_output.json()['error']}")
                tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to cancel a SLL order: {order_output.json()['error']}"
                send_telegram_message()
                macd_hist_list.pop(0)
                asset_dict[asset_pair]["macd_hist"] = macd_hist_list
                write_to_asset_file()
            else:
              print(f"{interval_time_simple} {asset_pair}: An error occured when trying to reduce/close a long pos: {order_output.json()['error']}")
              tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to reduce/close a long pos: {order_output.json()['error']}"
              send_telegram_message()
              macd_hist_list.pop(0)
              asset_dict[asset_pair]["macd_hist"] = macd_hist_list
              write_to_asset_file()
          else:
            print(f"{interval_time_simple} {asset_pair}: Nothing left to sell because we own 0 of it, so just create a short position")
            tg_message = f"{interval_time_simple} {asset_pair}: Nothing left to sell because we own 0 of it, so just create a short position"
            send_telegram_message()
            # create/increase short position
            asset_close = float(get_asset_close())
            usd_order_size = order_size
            volume_to_sell = str(float(usd_order_size / asset_close))
            sll_trigger = str(round(float(asset_close * sll_trigger_pct), 1))
            sll_limit = str(round(float(asset_close * sll_limit_pct), 1))
            order_output = open_increase_short_position()
            if not order_output.json()['error']:
              print(f"{interval_time_simple} {asset_pair}: Sucessfully created created/increased short position with SLL: {order_output.json()}")
              tg_message = f"{interval_time_simple} {asset_pair}: Sucessfully created created/increased short position with SLL: {order_output.json()}"
              send_telegram_message()
              # add short txid and sll txid to asset dict lists
              short_txid = order_output.json()['result']['txid'][0]
              open_orders = query_open_orders().json()
              for key, value in open_orders['result']['open'].items():
                print(f"Key: {key}, Value: {value['refid']}")
                if short_txid == value['refid']:
                  print(f"Found a match")
                  conditional_order_txid = key
              short_pos_txid_list.append(short_txid)
              conditional_order_txid_list.append(conditional_order_txid)
              holdings_short_list.append(float(volume_to_sell))
              macd_hist_list.pop(0)
              asset_dict[asset_pair]["macd_hist"] = macd_hist_list
              asset_dict[asset_pair]["short_pos_txid"] = short_pos_txid_list
              asset_dict[asset_pair]["conditional_order_txid"] = conditional_order_txid_list
              asset_dict[asset_pair]["holdings_short"] = holdings_short_list
              write_to_asset_file()
            else:
              print(f"{interval_time_simple} {asset_pair}: An error occured when trying to create/increase a short position with SLL: {order_output.json()['error']}")
              tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to create/increase a short position with SLL: {order_output.json()['error']}"
              send_telegram_message()
              macd_hist_list.pop(0)
              asset_dict[asset_pair]["macd_hist"] = macd_hist_list
              write_to_asset_file()
      time.sleep(3) # sleep 3 seconds between asset pair
    list_24h.clear()
  time.sleep(loop_time_seconds)