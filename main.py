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
asset_pairs = ['XXBTZUSD', 'SOLUSD', 'XETHZUSD', 'XXRPZUSD']
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_url = "https://api.kraken.com"
tg_token = os.environ['telegram_token']
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
      asset_pair_short = "SOLUSD"
    if asset_pair == "XETHZUSD":
      asset_code = "XETH"
      leverage = "5:1"
      api_sec = os.environ['api_sec_env_eth']
      api_key = os.environ['api_key_env_eth']
      asset_pair_short = "ETHUSD"
    if asset_pair == "XXRPZUSD":
      asset_code = "XXRP"
      leverage = "5:1"
      api_sec = os.environ['api_sec_env_xrp']
      api_key = os.environ['api_key_env_xrp']
      asset_pair_short = "XRPUSD"
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
    return response

def cancel_order(order_txid):
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

'''
construct asset dict to story macd hist values in per asset pair   
asset_dict = {
  <pair 1>: [],
  <pair 2>: [],
  <pair 3>: []
  }
'''
def create_asset_dict():
    func_dict = {}
    for asset_pair in asset_pairs:
       func_dict[asset_pair] = []
    return func_dict

asset_dict = create_asset_dict()

print(f"Asset dict: {asset_dict}")

# main loop
while True:
  interval_time_minutes = 1440
  interval_time_simple = '1d'
  order_size = 1200
  # order_size = 10
  sll_short_trigger_pct = 1.09 # trigger pct from current price
  sll_short_limit_pct = 1.10 # limit pct from current price
  sll_long_trigger_pct = 0.91 # trigger pct from current price
  sll_long_limit_pct = 0.90 # limit pct from current price
  for asset_pair in asset_pairs:
    api_key = get_asset_vars()[2]
    api_sec = get_asset_vars()[1]
    leverage = get_asset_vars()[3]
    asset_pair_short = get_asset_vars()[4]
    macd_hist_list = asset_dict[asset_pair]
    if len(macd_hist_list) == 0:
      print(f"{interval_time_simple} {asset_pair}: MACD hist list length: {len(macd_hist_list)}, appending 2 MACD hist values")
      macd_hist_tmp = get_macdhist_start()
      macd_hist_list.append(macd_hist_tmp[-2])
      macd_hist_list.append(macd_hist_tmp[-1])
      asset_dict[asset_pair] = macd_hist_list
      time.sleep(1)
      print(f"{interval_time_simple} {asset_pair}: Appended MACD hist: {macd_hist_list}")
      tg_message = f"{interval_time_simple} {asset_pair}: Appended MACD hist: {macd_hist_list}"
      send_telegram_message()
    if len(macd_hist_list) == 1:
      print(f"{interval_time_simple} {asset_pair}: {macd_hist_list}, appending 1 MACD hist value")
      print(f"{interval_time_simple} {asset_pair}: MACD hist list length: {len(macd_hist_list)}, appending 1 MACD hist value")
      macd_hist_list.append(get_macdhist())
      asset_dict[asset_pair] = macd_hist_list
      time.sleep(1)
      print(f"{interval_time_simple} {asset_pair}: Appended MACD hist: {macd_hist_list}")
      tg_message = f"{interval_time_simple} {asset_pair}: Appended MACD hist: {macd_hist_list}"
      send_telegram_message()
    ############## for testing purposes ####################
    # macd_hist_list = [-1, 1] ######## BUY
    # macd_hist_list = [1, -1] # ######## SELL
    if macd_hist_list[-2] < 0:
      # if macd_hist_list = [< 0, y]
      print(f"{interval_time_simple} {asset_pair}: Watching to buy asset when MACD hist crosses 0")
      if macd_hist_list[-1] < 0:
        # if macd_hist_list = [<0, <0]
        print(f"{interval_time_simple} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing")
        macd_hist_list.pop(0)
        # macd_hist_list = [<0]
        # append macd_hist_list to asset_dict[asset_pair]
        asset_dict[asset_pair] = macd_hist_list
        tg_message = f"{interval_time_simple} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing"
        send_telegram_message()
      elif macd_hist_list[-1] > 0:
        print(f"{interval_time_simple} {asset_pair}: MACD hist crossed 0, closing short pos if any and opening long pos")
        tg_message = f"{interval_time_simple} {asset_pair}: MACD hist crossed 0, closing short pos if any and opening long pos"
        send_telegram_message()
        open_orders = query_open_orders().json()['result']
        if not open_orders['open']:
          print(f"No open orders currently present")
          print(f"{interval_time_simple} {asset_pair}: Opening los pos")
          asset_close = float(get_asset_close())
          usd_order_size = order_size
          order_volume = str(float(usd_order_size / asset_close))
          sll_trigger = str(round(float(asset_close * sll_long_trigger_pct), 1))
          sll_limit = str(round(float(asset_close * sll_long_limit_pct), 1))
          order_output = open_increase_long_pos()
          if not order_output.json()['error']:
            print(f"{interval_time_simple} {asset_pair}: Succesfully opened long pos: {order_output.json()}")
            tg_message = f"{interval_time_simple} {asset_pair} Succesfully opened long pos: {order_output.json()}"
            send_telegram_message()
            macd_hist_list.pop(0)
            asset_dict[asset_pair] = macd_hist_list
          else:
            print(f"{interval_time_simple} {asset_pair}: Something went wrong opening a long pos: {order_output.json()}")
            tg_message = f"{interval_time_simple} {asset_pair} Something went wrong opening a long pos: {order_output.json()}"
            send_telegram_message()
            macd_hist_list.pop(0)
            asset_dict[asset_pair] = macd_hist_list
        else:
          print(f"There are open orders")
          print(f"Checking if there are open orders for {asset_pair}")
          open_orders = query_open_orders().json()['result']
          open_order_dict = {}
          for key, value in open_orders['open'].items():
            # key = asset pair short
            # value = order txid
            open_order_dict.update({value['descr']['pair']: key})
            '''
            open_order_keys = [asset_pair_short]
            open_order_values = [order_txid]
            open_order_dict = {asset_pair_short: order_txid, asset_pair_short: order_txid}
            '''
          if asset_pair_short in open_order_dict.keys():
            print(f"{interval_time_simple} {asset_pair}: cancelling SLL order")
            order_txid = open_order_dict[asset_pair_short]
            order_output = cancel_order(order_txid)
            if not order_output.json()['error']:
              print(f"{interval_time_simple} {asset_pair}: Succesfully cleared SLL order: {order_output.json()}")
              tg_message = f"{interval_time_simple} {asset_pair} Succesfully cleared SLL order: {order_output.json()}"
              send_telegram_message()
              print(f"{interval_time_simple} {asset_pair}: Closing short pos")
              time.sleep(5)
              order_output = close_short_pos()
              print(f"Result closing short pos for {asset_pair}: {order_output}")
              if not order_output.json()['error']:
                print(f"{interval_time_simple} {asset_pair}: Succesfully closed short pos: {order_output.json()}")
                tg_message = f"{interval_time_simple} {asset_pair} Succesfully closed short pos: {order_output.json()}"
                send_telegram_message()
                print(f"{interval_time_simple} {asset_pair}: Opening long pos")
                asset_close = float(get_asset_close())
                usd_order_size = order_size
                order_volume = str(float(usd_order_size / asset_close))
                sll_trigger = str(round(float(asset_close * sll_long_trigger_pct), 1))
                sll_limit = str(round(float(asset_close * sll_long_limit_pct), 1))
                order_output = open_increase_long_pos()
                if not order_output.json()['error']:
                  print(f"{interval_time_simple} {asset_pair}: Succesfully opened long pos: {order_output.json()}")
                  tg_message = f"{interval_time_simple} {asset_pair} Succesfully opened long pos: {order_output.json()}"
                  send_telegram_message()
                  macd_hist_list.pop(0)
                  asset_dict[asset_pair] = macd_hist_list
                else:
                  print(f"{interval_time_simple} {asset_pair}: Something went wrong opening a long pos: {order_output.json()}")
                  tg_message = f"{interval_time_simple} {asset_pair} Something went wrong opening a long pos: {order_output.json()}"
                  send_telegram_message()
                  macd_hist_list.pop(0)
                  asset_dict[asset_pair] = macd_hist_list
              else:
                print(f"{interval_time_simple} {asset_pair}: Something went wrong closing short pos: {order_output.json()}")
                tg_message = f"{interval_time_simple} {asset_pair} Something went wrong closing short pos: {order_output.json()}"
                send_telegram_message()
                macd_hist_list.pop(0)
                asset_dict[asset_pair] = macd_hist_list
            else:
              print(f"{interval_time_simple} {asset_pair}: Something went wrong cancelling SLL order: {order_output.json()}")
              tg_message = f"{interval_time_simple} {asset_pair} Something went wrong cancelling SLL order: {order_output.json()}"
              send_telegram_message()
              macd_hist_list.pop(0)
              asset_dict[asset_pair] = macd_hist_list
          else:
            print(f"{interval_time_simple} {asset_pair} not present in orders, opening long pos")
            asset_close = float(get_asset_close())
            usd_order_size = order_size
            order_volume = str(float(usd_order_size / asset_close))
            sll_trigger = str(round(float(asset_close * sll_long_trigger_pct), 1))
            sll_limit = str(round(float(asset_close * sll_long_limit_pct), 1))
            order_output = open_increase_long_pos()
            if not order_output.json()['error']:
              print(f"{interval_time_simple} {asset_pair}: Succesfully opened long pos: {order_output.json()}")
              tg_message = f"{interval_time_simple} {asset_pair} Succesfully opened long pos: {order_output.json()}"
              send_telegram_message()
              macd_hist_list.pop(0)
              asset_dict[asset_pair] = macd_hist_list
            else:
              print(f"{interval_time_simple} {asset_pair}: Someting went wrong opening a long pos: {order_output.json()}")
              tg_message = f"{interval_time_simple} {asset_pair} Something went wrong opening a long pos: {order_output.json()}"
              send_telegram_message()
              macd_hist_list.pop(0)
              asset_dict[asset_pair] = macd_hist_list
    elif macd_hist_list[-2] > 0:
      print(f"{interval_time_simple} {asset_pair}: Watching to sell asset when MACD hist crosses 0 and opening a short position")
      if macd_hist_list[-1] > 0:
        print(f"{interval_time_simple} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing")
        macd_hist_list.pop(0)
        asset_dict[asset_pair] = macd_hist_list
        tg_message = f"{interval_time_simple} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing"
        send_telegram_message()
      elif macd_hist_list[-1] < 0:
        print(f"{interval_time_simple} {asset_pair}: MACD hist crossed 0, closing long pos if any and opening short pos")
        tg_message = f"{interval_time_simple} {asset_pair}: MACD hist crossed 0, closing long pos if any and opening short pos"
        send_telegram_message()
        open_orders = query_open_orders().json()['result']
        if not open_orders['open']:
          print(f"No open orders currently present")
          print(f"{interval_time_simple} {asset_pair}: Opening short pos")
          asset_close = float(get_asset_close())
          usd_order_size = order_size
          order_volume = str(float(usd_order_size / asset_close))
          sll_trigger = str(round(float(asset_close * sll_short_trigger_pct), 1))
          sll_limit = str(round(float(asset_close * sll_short_limit_pct), 1))
          order_output = open_increase_short_pos()
          if not order_output.json()['error']:
            print(f"{interval_time_simple} {asset_pair}: Succesfully opened short pos: {order_output.json()}")
            tg_message = f"{interval_time_simple} {asset_pair} Succesfully opened short pos: {order_output.json()}"
            send_telegram_message()
            macd_hist_list.pop(0)
            asset_dict[asset_pair] = macd_hist_list
          else:
            print(f"{interval_time_simple} {asset_pair}: Something went wrong opening a short pos: {order_output.json()}")
            tg_message = f"{interval_time_simple} {asset_pair} Something went wrong opening a short pos: {order_output.json()}"
            send_telegram_message()
            macd_hist_list.pop(0)
            asset_dict[asset_pair] = macd_hist_list
        else:
          print(f"There are open orders")
          print(f"Checking if there are open orders for {asset_pair}")
          open_orders = query_open_orders().json()['result']
          open_order_dict = {}
          for key, value in open_orders['open'].items():
            # key = asset pair short
            # value = order txid
            open_order_dict.update({value['descr']['pair']: key})
            '''
            open_order_keys = [asset_pair_short]
            open_order_values = [order_txid]
            open_order_dict = {asset_pair_short: order_txid, asset_pair_short: order_txid}
            '''
          if asset_pair_short in open_order_dict.keys():
            print(f"{interval_time_simple} {asset_pair}: cancelling SLL order")
            order_txid = open_order_dict[asset_pair_short]
            order_output = cancel_order(order_txid)
            if not order_output.json()['error']:
              print(f"{interval_time_simple} {asset_pair}: Succesfully cleared SLL order: {order_output.json()}")
              tg_message = f"{interval_time_simple} {asset_pair} Succesfully cleared SLL order: {order_output.json()}"
              send_telegram_message()
              time.sleep(5)
              print(f"{interval_time_simple} {asset_pair}: Closing long pos")
              order_output = close_long_pos()
              print(f"Result closing long pos for {asset_pair}: {order_output}")
              if not order_output.json()['error']:
                print(f"{interval_time_simple} {asset_pair}: Succesfully closed long pos: {order_output.json()}")
                tg_message = f"{interval_time_simple} {asset_pair} Succesfully closed long pos: {order_output.json()}"
                send_telegram_message()
                print(f"{interval_time_simple} {asset_pair}: Opening short pos")
                asset_close = float(get_asset_close())
                usd_order_size = order_size
                order_volume = str(float(usd_order_size / asset_close))
                sll_trigger = str(round(float(asset_close * sll_short_trigger_pct), 1))
                sll_limit = str(round(float(asset_close * sll_short_limit_pct), 1))
                order_output = open_increase_short_pos()
                if not order_output.json()['error']:
                  print(f"{interval_time_simple} {asset_pair}: Succesfully opened short pos: {order_output.json()}")
                  tg_message = f"{interval_time_simple} {asset_pair} Succesfully opened short pos: {order_output.json()}"
                  send_telegram_message()
                  macd_hist_list.pop(0)
                  asset_dict[asset_pair] = macd_hist_list
                else:
                  print(f"{interval_time_simple} {asset_pair}: Something went wrong opening a short pos: {order_output.json()}")
                  tg_message = f"{interval_time_simple} {asset_pair} Something went wrong opening a short pos: {order_output.json()}"
                  send_telegram_message()
                  macd_hist_list.pop(0)
                  asset_dict[asset_pair] = macd_hist_list
              else:
                print(f"{interval_time_simple} {asset_pair}: Something went wrong closing long pos: {order_output.json()}")
                tg_message = f"{interval_time_simple} {asset_pair} Something went wrong closing long pos: {order_output.json()}"
                send_telegram_message()
                macd_hist_list.pop(0)
                asset_dict[asset_pair] = macd_hist_list
            else:
              print(f"{interval_time_simple} {asset_pair}: Something went wrong cancelling SLL order: {order_output.json()}")
              tg_message = f"{interval_time_simple} {asset_pair} Something went wrong cancelling SLL order: {order_output.json()}"
              send_telegram_message()
              macd_hist_list.pop(0)
              asset_dict[asset_pair] = macd_hist_list
          else:
            print(f"{interval_time_simple} {asset_pair} not present in orders, opening short pos")
            asset_close = float(get_asset_close())
            usd_order_size = order_size
            order_volume = str(float(usd_order_size / asset_close))
            sll_trigger = str(round(float(asset_close * sll_short_trigger_pct), 1))
            sll_limit = str(round(float(asset_close * sll_short_limit_pct), 1))
            order_output = open_increase_short_pos()
            if not order_output.json()['error']:
              print(f"{interval_time_simple} {asset_pair}: Succesfully opened short pos: {order_output.json()}")
              tg_message = f"{interval_time_simple} {asset_pair} Succesfully opened short pos: {order_output.json()}"
              send_telegram_message()
              macd_hist_list.pop(0)
              asset_dict[asset_pair] = macd_hist_list
            else:
              print(f"{interval_time_simple} {asset_pair}: Someting went wrong opening a short pos: {order_output.json()}")
              tg_message = f"{interval_time_simple} {asset_pair} Something went wrong opening a short pos: {order_output.json()}"
              send_telegram_message()
              macd_hist_list.pop(0)
              asset_dict[asset_pair] = macd_hist_list
    print(f"{asset_pair} block done, sleeping 3 seconds")
    time.sleep(3) # sleep 3 seconds between asset pair
  print(f"Done with all assets, sleeping for {loop_time_seconds} seconds")
  time.sleep(loop_time_seconds)
