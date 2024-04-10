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

'''
- Buy RSI < 35 and MACD upwards trend 3 iterations
- Sell RSI > 65 and MACD downwards trend 3 iterations

Flow:
- Create dict to store asset_pair dict with rsi list, macd list and holdings list
- If RSI 35> and <65, dont do anything
- If RSI < 35, append value to asset_pair rsi and append macd value to asset_pair macd. At next iteration:
  - Keep RSI < 35 value in rsi list
  - Append MACD value to macd list
  - Keep appending MACD value to macd list
  - If MACD list values from asset_pair is in an upward trend for 3 iterations, buy asset append bought amount to asset_pair holding list. Clear asset_pair rsi and macd list
- If RSI > 65, append value to asset_pair rsi and append macd value to asset_pair macd. At next iteration:
  - Keep RSI > 65 value in rsi list
  - Append MACD value to macd list
  - Keep appending MACD value to macd list
  - If MACD list values from asset_pair is in an downwards trend for 3 iterations, sell asset and clear asset_pair holding, rsi and macd list

'''

# set vars
asset_dict = {}
asset_pairs = ['XXBTZUSD', 'XXRPZUSD', 'ADAUSD', 'SOLUSD', 'AVAXUSD', 'MATICUSD', 'XETHZUSD']
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_url = "https://api.kraken.com"
tg_token = os.environ['telegram_token']
list_1h = []
list_4h = []
list_24h = []
loop_time_seconds = 3600

# functions
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

def get_holdings():
    holdings = kraken_request('/0/private/Balance', {"nonce": str(int(1000*time.time()))}, api_key, api_sec)
    return holdings

# get min order size for asset_pair
def min_order_size():
    time.sleep(2)
    resp = requests.get('https://api.kraken.com/0/public/AssetPairs')
    minimum_order_size = float(resp.json()['result'][asset_pair]['ordermin'])
    return minimum_order_size

# get asset_pair close value
def get_asset_close():
    time.sleep(2)
    payload = {'pair': asset_pair}
    resp = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    close_value = resp.json()['result'][asset_pair]['c'][0]
    return close_value

# function for obtaining OHLC data and getting the close value, interval in minutes
def get_ohlcdata():
    time.sleep(2)
    payload = {'pair': asset_pair, 'interval': interval_time_minutes}
    ohlc_data_raw = requests.get('https://api.kraken.com/0/public/OHLC', params=payload)
    if not ohlc_data_raw.json()['error']:
      # construct a dataframe and assign columns using asset ohlc data
      df = pd.DataFrame(ohlc_data_raw.json()['result'][asset_pair])
      df.columns = ['unixtimestap', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
      # we are only interested in asset close data, so create var for close data columns and set var type as float
      close_data = df['close'].astype(float) # set close data to float
      return close_data
    else:
      print(f"Error requesting {asset_pair} OHLC data: {ohlc_data_raw.json()['error']}")
      tg_message = f"Error requesting {asset_pair} OHLC data {ohlc_data_raw.json()['error']}"
      send_telegram_message()

# function for obtaining OHLC data for MACD and getting the close value, interval in minutes
def get_ohlcdata_macd():
    time.sleep(2)
    payload = {'pair': asset_pair, 'interval': interval_time_minutes}
    ohlc_data_raw = requests.get('https://api.kraken.com/0/public/OHLC', params=payload)
    if not ohlc_data_raw.json()['error']:
      # construct a dataframe and assign columns using asset ohlc data
      df = pd.DataFrame(ohlc_data_raw.json()['result'][asset_pair])
      df.columns = ['unixtimestap', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
      # we are only interested in asset close data, so create var for close data columns and set var type as float
      close_data = df['close']
      return close_data
    else:
      print(f"Error requesting {asset_pair} OHLC data: {ohlc_data_raw.json()['error']}")
      tg_message = f"Error requesting {asset_pair} OHLC data {ohlc_data_raw.json()['error']}"
      send_telegram_message()

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
  
  # function to display RSI (tradingview calculcation)
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

def get_macd():
    close = get_ohlcdata_macd()
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd_dict = macd.to_dict()
    macd_values = list(macd_dict.values())
    return macd_values[-1]

# main loop
while True:
  list_1h.append(1)
  list_4h.append(4)
  list_24h.append(24)
  if len(list_1h) == 1:
    timeframe = "1h"
    file_extension = '.json'
    asset_file = timeframe + file_extension 
    asset_file_path = './' + asset_file
    interval_time_minutes = 60
    interval_time_simple = '1h'
    order_size = 50
    for asset_pair in asset_pairs:
      # set asset code / api tokens for asset pair 
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
      if asset_pair == "AVAXUSD":
        asset_code = "AVAX"
        api_sec = os.environ['api_sec_env_avax']
        api_key = os.environ['api_key_env_avax']
      if asset_pair == "MATICUSD":
        asset_code = "MATIC"
        api_sec = os.environ['api_sec_env_matic']
        api_key = os.environ['api_key_env_matic']
      if asset_pair == "XETHZUSD":
        asset_code = "XETH"
        api_sec = os.environ['api_sec_env_eth']
        api_key = os.environ['api_key_env_eth']

      asset_file_exists = os.path.exists(asset_file_path)
      # create file if it doesnt exist, add dictionary per asset to it
      if not asset_file_exists:
        print(f"Asset file {asset_file} doesnt exist , creating one")
        f = open(asset_file, "w")
        asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": []}})
        f.write(json.dumps(asset_dict))
        f.close()
      else:
        print(f"Asset file {asset_file} exists, reading")
        f = open(asset_file, "r")
        asset_json = f.read()
        f.close()
        asset_dict = json.loads(asset_json)
        if asset_pair not in asset_dict.keys():
          print(f"Asset pair {asset_pair} not present in asset file {asset_file}, updating file")
          asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": []}})
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
          print(f"Appended {asset_pair} to {asset_file}")

      # set variable for RSI
      rsi_list_values  = rsi_tradingview()
      rsi = float(rsi_list_values[-1])

      # set these vars for testing purposes
      # rsi = 25
      # macd_list = [1, 2, 3] # for buying asset
      # macd_list = [3, 2, 1] # for selling asset
      # order_size = 15

      print(f"{interval_time_simple} RSI  {asset_pair}: {rsi}")
    
      print(f"opening asset file {asset_file}")
      f = open(asset_file, "r")
      asset_json = f.read()
      f.close()

      asset_dict = json.loads(asset_json)
      macd_list = asset_dict[asset_pair]["macd"] 
      rsi_list = asset_dict[asset_pair]["rsi"]
      holdings_list = asset_dict[asset_pair]["holdings"]

      if len(rsi_list) == 1:
        if rsi_list[0] < 35:
          print(f"{interval_time_simple} {asset_pair}: Read {rsi_list[0]} RSI in file, keeping value in list")
          rsi = rsi_list[0]
        elif rsi_list[0] > 65:
          print(f"{interval_time_simple} {asset_pair}: Read {rsi_list[0]} RSI in file, keeping value in list")
          rsi = rsi_list[0]
        else:
          print(f"{interval_time_simple} {asset_pair}: Clearing RSI value {rsi_list[0]}")
          rsi_list.clear()
          rsi_list.append(rsi)
          asset_dict[asset_pair]["rsi"] = rsi_list
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
      elif len(rsi_list) == 0:
        print(f"{interval_time_simple} {asset_pair}: RSI list is empty, appending {rsi} to it")
        rsi_list.append(rsi)
        asset_dict[asset_pair]["rsi"] = rsi_list
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()

      if rsi < 35 and len(macd_list) < 3:
        print(f"{interval_time_simple} {asset_pair}: RSI {rsi} and length of macd list: {len(asset_dict[asset_pair]['macd'])}")
        # append macd value to macd list
        macd = get_macd() 
        macd_list.append(macd)
        asset_dict[asset_pair]["macd"] = macd_list
        # write to asset_file
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
        print(f"{interval_time_simple} {asset_pair}: Appended {macd} macd value to macd list")
        print(f"{interval_time_simple} {asset_pair}: MACD list {asset_dict[asset_pair]['macd']}")
        print(f"Current date/time: {datetime.datetime.now()}")
        tg_message = f"{interval_time_simple} {asset_pair}: RSI {rsi} and MACD list: {asset_dict[asset_pair]['macd']}"
        send_telegram_message()
      elif rsi < 35 and len(macd_list) >= 3:
        if macd_list[-3] < macd_list[-2] < macd_list[-1]:
          print(f"{interval_time_simple} {asset_pair}: MACD in upward trend for 3 iterations: {macd_list[-3:]}, buying {asset_pair}")
          tg_message = f"{interval_time_simple} {asset_pair}: MACD in upward trend for 3 iterations: {macd_list[-3:]}, buying {asset_pair}"
          send_telegram_message()
          asset_close = float(get_asset_close())
          usd_order_size = order_size
          volume_to_buy = str(float(usd_order_size / asset_close))
          order_output = buy_asset() # executes buy order and assigns output to var
          if not order_output.json()['error']:
            print(f"{interval_time_simple} {asset_pair}: Bought {volume_to_buy}")
            tg_message = order_output.json()['result']
            send_telegram_message()        
            # clear rsi/macd lists from asset_dict
            macd_list.clear()
            rsi_list.clear()
            holdings_list.append(float(volume_to_buy))
            asset_dict[asset_pair]["macd"] = macd_list
            asset_dict[asset_pair]["rsi"] = rsi_list
            asset_dict[asset_pair]["holdings"] = holdings_list
            f = open(asset_file, "w")
            f.write(json.dumps(asset_dict))
            f.close()
          else:
            print(f"{interval_time_simple} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}")
            tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}"
            send_telegram_message()
        else: 
          print(f"{interval_time_simple} {asset_pair}: No upward MACD yet, appending MACD value to macd list")
          tg_message = f"{interval_time_simple} {asset_pair}: No upward MACD yet, appending MACD value to macd list"
          send_telegram_message()
          # append macd value to macd list
          macd = get_macd() 
          macd_list.append(macd)
          asset_dict[asset_pair]["macd"] = macd_list
          # write to asset_file
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
          print(f"{interval_time_simple} {asset_pair}: Appended {macd} macd value to macd list")
          print(f"{interval_time_simple} {asset_pair}: MACD list {asset_dict[asset_pair]['macd']}")
          tg_message = f"{interval_time_simple} {asset_pair}: RSI {rsi} and MACD list: {asset_dict[asset_pair]['macd']}"
          send_telegram_message()
      elif rsi > 65 and len(macd_list) < 3:
        print(f"{interval_time_simple} {asset_pair}: RSI {rsi} and length of macd list: {len(asset_dict[asset_pair]['macd'])}")
        # append macd value to macd list
        macd = get_macd() 
        macd_list.append(macd)
        asset_dict[asset_pair]["macd"] = macd_list
        # write to asset_file
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
        print(f"Current date/time: {datetime.datetime.now()}")
        print(f"{interval_time_simple} {asset_pair}: Appended {macd} macd value to macd list")
        print(f"{interval_time_simple} {asset_pair}: MACD list {asset_dict[asset_pair]['macd']}")
        tg_message = f"{interval_time_simple} {asset_pair}: RSI {rsi} and MACD list: {asset_dict[asset_pair]['macd']}"
        send_telegram_message()
      elif rsi > 65 and len(macd_list) >= 3:
        if macd_list[-3] > macd_list[-2] > macd_list[-1]:
          # sell asset
          print(f"Current date/time: {datetime.datetime.now()}")
          print(f"{interval_time_simple} {asset_pair}: MACD in downward trend for 3 iterations: {macd_list[-3:]}, selling {asset_pair}")
          tg_message = f"{interval_time_simple} {asset_pair}: MACD in downward trend for 3 iterations: {macd_list[-3:]}, selling {asset_pair}"
          send_telegram_message()
          if float(sum(holdings_list)) > 0: # check if we have some in our holdings
            volume_to_sell = str(sum(holdings_list))
            if min_order_size() < float(volume_to_sell):
              order_output = sell_asset()
              if not order_output.json()['error']:
                macd_list.clear()
                rsi_list.clear()
                holdings_list.clear()
                asset_dict[asset_pair]["macd"] = macd_list
                asset_dict[asset_pair]["rsi"] = rsi_list
                asset_dict[asset_pair]["holdings"] = holdings_list
                f = open(asset_file, "w")
                f.write(json.dumps(asset_dict))
                f.close()
                print(f"Current date/time: {datetime.datetime.now()}")
                print(f"{interval_time_simple} {asset_pair}: Sold {volume_to_sell}")
                tg_message = order_output.json()['result']
                send_telegram_message()        
              else:
                print(f"Current date/time: {datetime.datetime.now()}")
                print(f"{interval_time_simple} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}")
                tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}"
                send_telegram_message()
            else:
              # clear rsi/macd lists from asset_dict
              macd_list.clear()
              rsi_list.clear()
              asset_dict[asset_pair]["macd"] = macd_list
              asset_dict[asset_pair]["rsi"] = rsi_list
              f = open(asset_file, "w")
              f.write(json.dumps(asset_dict))
              f.close()
              print(f"Current date/time: {datetime.datetime.now()}")
              print(f"{interval_time_simple} {asset_pair}: Not enough left to sell")
              tg_message = f"{interval_time_simple} {asset_pair}: Not enough left to sell"
              send_telegram_message()
          else:
            # clear rsi/macd lists from asset_dict
            macd_list.clear()
            rsi_list.clear()
            asset_dict[asset_pair]["macd"] = macd_list
            asset_dict[asset_pair]["rsi"] = rsi_list
            f = open(asset_file, "w")
            f.write(json.dumps(asset_dict))
            f.close()
            print(f"Current date/time: {datetime.datetime.now()}")
            print(f"{interval_time_simple} {asset_pair}: Nothing left to sell because we own 0 of it")  
            tg_message = f"{interval_time_simple} {asset_pair}: Nothing left to sell because we own 0 of it"
            send_telegram_message()
        else:
          print(f"{interval_time_simple} {asset_pair}: No downward MACD yet, appending MACD value to macd list")
          tg_message = f"{interval_time_simple} {asset_pair}: No downward MACD yet, appending MACD value to macd list"
          send_telegram_message()
          macd = get_macd() 
          macd_list.append(macd)
          asset_dict[asset_pair]["macd"] = macd_list
          # write to asset_file
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
          print(f"Current date/time: {datetime.datetime.now()}")
          print(f"{interval_time_simple} {asset_pair}: Appended {macd} macd value to macd list")
          print(f"{interval_time_simple} {asset_pair}: MACD list {asset_dict[asset_pair]['macd']}")
          tg_message = f"{interval_time_simple} {asset_pair}: RSI {rsi} and MACD list: {asset_dict[asset_pair]['macd']}"
          send_telegram_message()
      else:
        print(f"{interval_time_simple} {asset_pair}: RSI {rsi}, nothing to do. Checking back in {loop_time_seconds} seconds")
        print(f"Current date/time: {datetime.datetime.now()}")
        tg_message = f"{interval_time_simple} {asset_pair}: RSI {rsi}, nothing to do. Checking back in {loop_time_seconds} seconds"
        send_telegram_message()
      time.sleep(3) # sleep 3 seconds between asset pair
    list_1h.clear()
  if len(list_4h) == 4:
    timeframe = "4h"
    file_extension = '.json'
    asset_file = timeframe + file_extension 
    asset_file_path = './' + asset_file
    interval_time_minutes = 240
    interval_time_simple = '4h'
    order_size = 200
    for asset_pair in asset_pairs:
      # set asset code / api tokens for asset pair 
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
      if asset_pair == "AVAXUSD":
        asset_code = "AVAX"
        api_sec = os.environ['api_sec_env_avax']
        api_key = os.environ['api_key_env_avax']
      if asset_pair == "MATICUSD":
        asset_code = "MATIC"
        api_sec = os.environ['api_sec_env_matic']
        api_key = os.environ['api_key_env_matic']
      if asset_pair == "XETHZUSD":
        asset_code = "XETH"
        api_sec = os.environ['api_sec_env_eth']
        api_key = os.environ['api_key_env_eth']

      asset_file_exists = os.path.exists(asset_file_path)
      # create file if it doesnt exist, add dictionary per asset to it
      if not asset_file_exists:
        print(f"Asset file {asset_file} doesnt exist , creating one")
        f = open(asset_file, "w")
        asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": []}})
        f.write(json.dumps(asset_dict))
        f.close()
      else:
        print(f"Asset file {asset_file} exists, reading")
        f = open(asset_file, "r")
        asset_json = f.read()
        f.close()
        asset_dict = json.loads(asset_json)
        if asset_pair not in asset_dict.keys():
          print(f"Asset pair {asset_pair} not present in asset file {asset_file}, updating file")
          asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": []}})
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
          print(f"Appended {asset_pair} to {asset_file}")

      # set variable for RSI
      rsi_list_values  = rsi_tradingview()
      rsi = float(rsi_list_values[-1])

      # set these vars for testing purposes
      # rsi = 25
      # macd_list = [1, 2, 3] # for buying asset
      # macd_list = [3, 2, 1] # for selling asset
      # order_size = 15

      print(f"{interval_time_simple} RSI  {asset_pair}: {rsi}")
    
      print(f"opening asset file {asset_file}")
      f = open(asset_file, "r")
      asset_json = f.read()
      f.close()

      asset_dict = json.loads(asset_json)
      macd_list = asset_dict[asset_pair]["macd"] 
      rsi_list = asset_dict[asset_pair]["rsi"]
      holdings_list = asset_dict[asset_pair]["holdings"]

      if len(rsi_list) == 1:
        if rsi_list[0] < 35:
          print(f"{interval_time_simple} {asset_pair}: Read {rsi_list[0]} RSI in file, keeping value in list")
          rsi = rsi_list[0]
        elif rsi_list[0] > 65:
          print(f"{interval_time_simple} {asset_pair}: Read {rsi_list[0]} RSI in file, keeping value in list")
          rsi = rsi_list[0]
        else:
          print(f"{interval_time_simple} {asset_pair}: Clearing RSI value {rsi_list[0]}")
          rsi_list.clear()
          rsi_list.append(rsi)
          asset_dict[asset_pair]["rsi"] = rsi_list
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
      elif len(rsi_list) == 0:
        print(f"{interval_time_simple} {asset_pair}: RSI list is empty, appending {rsi} to it")
        rsi_list.append(rsi)
        asset_dict[asset_pair]["rsi"] = rsi_list
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()

      if rsi < 35 and len(macd_list) < 3:
        print(f"{interval_time_simple} {asset_pair}: RSI {rsi} and length of macd list: {len(asset_dict[asset_pair]['macd'])}")
        # append macd value to macd list
        macd = get_macd() 
        macd_list.append(macd)
        asset_dict[asset_pair]["macd"] = macd_list
        # write to asset_file
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
        print(f"{interval_time_simple} {asset_pair}: Appended {macd} macd value to macd list")
        print(f"{interval_time_simple} {asset_pair}: MACD list {asset_dict[asset_pair]['macd']}")
        tg_message = f"{interval_time_simple} {asset_pair}: RSI {rsi} and MACD list: {asset_dict[asset_pair]['macd']}"
        send_telegram_message()
      elif rsi < 35 and len(macd_list) >= 3:
        print(f"{interval_time_simple} {asset_pair}: RSI < 35 and macd_list >= 3")
        tg_message = f"{interval_time_simple} {asset_pair}: RSI < 35 and macd_list >= 3"
        send_telegram_message()
        if macd_list[-3] < macd_list[-2] < macd_list[-1]:
          print(f"{interval_time_simple} {asset_pair}: MACD in upward trend for 3 iterations: {macd_list[-3:]}, buying {asset_pair}")
          tg_message = f"{interval_time_simple} {asset_pair}: MACD in upward trend for 3 iterations: {macd_list[-3:]}, buying {asset_pair}"
          send_telegram_message()
          asset_close = float(get_asset_close())
          usd_order_size = order_size
          volume_to_buy = str(float(usd_order_size / asset_close))
          order_output = buy_asset() # executes buy order and assigns output to var
          if not order_output.json()['error']:
            print(f"{interval_time_simple} {asset_pair}: Bought {volume_to_buy}")
            tg_message = order_output.json()['result']
            send_telegram_message()        
            # clear rsi/macd lists from asset_dict
            macd_list.clear()
            rsi_list.clear()
            holdings_list.append(float(volume_to_buy))
            asset_dict[asset_pair]["macd"] = macd_list
            asset_dict[asset_pair]["rsi"] = rsi_list
            asset_dict[asset_pair]["holdings"] = holdings_list
            f = open(asset_file, "w")
            f.write(json.dumps(asset_dict))
            f.close()
          else:
            print(f"{interval_time_simple} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}")
            tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}"
            send_telegram_message()
        else: 
          # append macd value to macd list
          macd = get_macd() 
          macd_list.append(macd)
          print(f"{interval_time_simple} {asset_pair}: Appending {macd} macd list")
          asset_dict[asset_pair]["macd"] = macd_list
          # write to asset_file
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
      elif rsi > 65 and len(macd_list) < 3:
        print(f"{interval_time_simple} {asset_pair}: RSI {rsi} and length of macd list: {len(asset_dict[asset_pair]['macd'])}")
        # append macd value to macd list
        macd = get_macd() 
        macd_list.append(macd)
        asset_dict[asset_pair]["macd"] = macd_list
        # write to asset_file
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
        print(f"{interval_time_simple} {asset_pair}: Appended {macd} macd value to macd list")
        print(f"{interval_time_simple} {asset_pair}: MACD list {asset_dict[asset_pair]['macd']}")
        tg_message = f"{interval_time_simple} {asset_pair}: RSI {rsi} and MACD list: {asset_dict[asset_pair]['macd']}"
      elif rsi > 65 and len(macd_list) >= 3:
        if macd_list[-3] > macd_list[-2] > macd_list[-1]:
          # sell asset
          print(f"{interval_time_simple} {asset_pair}: MACD in downward trend for 3 iterations: {macd_list[-3:]}, selling {asset_pair}")
          tg_message = f"{interval_time_simple} {asset_pair}: MACD in downward trend for 3 iterations: {macd_list[-3:]}, selling {asset_pair}"
          send_telegram_message()
          if float(sum(holdings_list)) > 0: # check if we have some in our holdings
            volume_to_sell = str(sum(holdings_list))
            if min_order_size() < float(volume_to_sell):
              order_output = sell_asset()
              if not order_output.json()['error']:
                macd_list.clear()
                rsi_list.clear()
                holdings_list.clear()
                asset_dict[asset_pair]["macd"] = macd_list
                asset_dict[asset_pair]["rsi"] = rsi_list
                asset_dict[asset_pair]["holdings"] = holdings_list
                f = open(asset_file, "w")
                f.write(json.dumps(asset_dict))
                f.close()
                print(f"{interval_time_simple} {asset_pair}: Sold {volume_to_sell}")
                tg_message = order_output.json()['result']
                send_telegram_message()        
              else:
                print(f"{interval_time_simple} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}")
                tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}"
                send_telegram_message()
            else:
              # clear rsi/macd lists from asset_dict
              macd_list.clear()
              rsi_list.clear()
              asset_dict[asset_pair]["macd"] = macd_list
              asset_dict[asset_pair]["rsi"] = rsi_list
              f = open(asset_file, "w")
              f.write(json.dumps(asset_dict))
              f.close()
              print(f"{interval_time_simple} {asset_pair}: Not enough left to sell")
              tg_message = f"{interval_time_simple} {asset_pair}: Not enough left to sell"
              send_telegram_message()
          else:
            # clear rsi/macd lists from asset_dict
            macd_list.clear()
            rsi_list.clear()
            asset_dict[asset_pair]["macd"] = macd_list
            asset_dict[asset_pair]["rsi"] = rsi_list
            f = open(asset_file, "w")
            f.write(json.dumps(asset_dict))
            f.close()
            print(f"{interval_time_simple} {asset_pair}: Nothing left to sell because we own 0 of it")  
            tg_message = f"{interval_time_simple} {asset_pair}: Nothing left to sell because we own 0 of it"
            send_telegram_message()
        else:
          print(f"{interval_time_simple} {asset_pair}: No downward MACD trend yet")
          macd = get_macd() 
          macd_list.append(macd)
          asset_dict[asset_pair]["macd"] = macd_list
          # write to asset_file
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
      else:
        print(f"{interval_time_simple} {asset_pair}: RSI {rsi}, nothing to do. Checking back in {loop_time_seconds} seconds")
        tg_message = f"{interval_time_simple} {asset_pair}: RSI {rsi}, nothing to do. Checking back in {loop_time_seconds} seconds"
        send_telegram_message()
      time.sleep(3) # sleep 3 seconds between asset pair
    list_4h.clear()
  if len(list_24h) == 24:
    timeframe = "1d"
    file_extension = '.json'
    asset_file = timeframe + file_extension 
    asset_file_path = './' + asset_file
    interval_time_minutes = 1440
    interval_time_simple = '1d'
    order_size = 500
    for asset_pair in asset_pairs:
      # set asset code / api tokens for asset pair 
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
      if asset_pair == "AVAXUSD":
        asset_code = "AVAX"
        api_sec = os.environ['api_sec_env_avax']
        api_key = os.environ['api_key_env_avax']
      if asset_pair == "MATICUSD":
        asset_code = "MATIC"
        api_sec = os.environ['api_sec_env_matic']
        api_key = os.environ['api_key_env_matic']
      if asset_pair == "XETHZUSD":
        asset_code = "XETH"
        api_sec = os.environ['api_sec_env_eth']
        api_key = os.environ['api_key_env_eth']

      asset_file_exists = os.path.exists(asset_file_path)
      # create file if it doesnt exist, add dictionary per asset to it
      if not asset_file_exists:
        print(f"Asset file {asset_file} doesnt exist , creating one")
        f = open(asset_file, "w")
        asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": []}})
        f.write(json.dumps(asset_dict))
        f.close()
      else:
        print(f"Asset file {asset_file} exists, reading")
        f = open(asset_file, "r")
        asset_json = f.read()
        f.close()
        asset_dict = json.loads(asset_json)
        if asset_pair not in asset_dict.keys():
          print(f"Asset pair {asset_pair} not present in asset file {asset_file}, updating file")
          asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": []}})
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
          print(f"Appended {asset_pair} to {asset_file}")

      # set variable for RSI
      rsi_list_values  = rsi_tradingview()
      rsi = float(rsi_list_values[-1])

      # set these vars for testing purposes
      # rsi = 25
      # macd_list = [1, 2, 3] # for buying asset
      # macd_list = [3, 2, 1] # for selling asset
      # order_size = 15

      print(f"{interval_time_simple} RSI  {asset_pair}: {rsi}")
   
      print(f"opening asset file {asset_file}")
      f = open(asset_file, "r")
      asset_json = f.read()
      f.close()

      asset_dict = json.loads(asset_json)
      macd_list = asset_dict[asset_pair]["macd"] 
      rsi_list = asset_dict[asset_pair]["rsi"]
      holdings_list = asset_dict[asset_pair]["holdings"]

      if len(rsi_list) == 1:
        if rsi_list[0] < 35:
          print(f"{interval_time_simple} {asset_pair}: Read {rsi_list[0]} RSI in file, keeping value in list")
          rsi = rsi_list[0]
        elif rsi_list[0] > 65:
          print(f"{interval_time_simple} {asset_pair}: Read {rsi_list[0]} RSI in file, keeping value in list")
          rsi = rsi_list[0]
        else:
          print(f"{interval_time_simple} {asset_pair}: Clearing RSI value {rsi_list[0]}")
          rsi_list.clear()
          rsi_list.append(rsi)
          asset_dict[asset_pair]["rsi"] = rsi_list
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
      elif len(rsi_list) == 0:
        print(f"{interval_time_simple} {asset_pair}: RSI list is empty, appending {rsi} to it")
        rsi_list.append(rsi)
        asset_dict[asset_pair]["rsi"] = rsi_list
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
      if rsi < 35 and len(macd_list) < 3:
        print(f"{interval_time_simple} {asset_pair}: RSI {rsi} and length of macd list: {len(asset_dict[asset_pair]['macd'])}")
        # append macd value to macd list
        macd = get_macd() 
        macd_list.append(macd)
        asset_dict[asset_pair]["macd"] = macd_list
        # write to asset_file
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
        print(f"{interval_time_simple} {asset_pair}: Appended {macd} macd value to macd list")
        print(f"{interval_time_simple} {asset_pair}: MACD list {asset_dict[asset_pair]['macd']}")
        tg_message = f"{interval_time_simple} {asset_pair}: RSI {rsi} and MACD list: {asset_dict[asset_pair]['macd']}"
        send_telegram_message()
      elif rsi < 35 and len(macd_list) >= 3:
        print(f"{interval_time_simple} {asset_pair}: RSI < 35 and macd_list >= 3")
        tg_message = f"{interval_time_simple} {asset_pair}: RSI < 35 and macd_list >= 3"
        send_telegram_message()
        if macd_list[-3] < macd_list[-2] < macd_list[-1]:
          print(f"{interval_time_simple} {asset_pair}: MACD in upward trend for 3 iterations: {macd_list[-3:]}, buying {asset_pair}")
          tg_message = f"{interval_time_simple} {asset_pair}: MACD in upward trend for 3 iterations: {macd_list[-3:]}, buying {asset_pair}"
          send_telegram_message()
          asset_close = float(get_asset_close())
          usd_order_size = order_size
          volume_to_buy = str(float(usd_order_size / asset_close))
          order_output = buy_asset() # executes buy order and assigns output to var
          if not order_output.json()['error']:
            print(f"{interval_time_simple} {asset_pair}: Bought {volume_to_buy}")
            tg_message = order_output.json()['result']
            send_telegram_message()        
            # clear rsi/macd lists from asset_dict
            macd_list.clear()
            rsi_list.clear()
            holdings_list.append(float(volume_to_buy))
            asset_dict[asset_pair]["macd"] = macd_list
            asset_dict[asset_pair]["rsi"] = rsi_list
            asset_dict[asset_pair]["holdings"] = holdings_list
            f = open(asset_file, "w")
            f.write(json.dumps(asset_dict))
            f.close()
          else:
            print(f"{interval_time_simple} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}")
            tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}"
            send_telegram_message()
        else: 
          # append macd value to macd list
          macd = get_macd() 
          macd_list.append(macd)
          print(f"{interval_time_simple} {asset_pair}: Appending {macd} macd list")
          asset_dict[asset_pair]["macd"] = macd_list
          # write to asset_file
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
      elif rsi > 65 and len(macd_list) < 3:
        print(f"{interval_time_simple} {asset_pair}: RSI {rsi} and length of macd list: {len(asset_dict[asset_pair]['macd'])}")
        # append macd value to macd list
        macd = get_macd() 
        macd_list.append(macd)
        asset_dict[asset_pair]["macd"] = macd_list
        # write to asset_file
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
        print(f"{interval_time_simple} {asset_pair}: Appended {macd} macd value to macd list")
        print(f"{interval_time_simple} {asset_pair}: MACD list {asset_dict[asset_pair]['macd']}")
        tg_message = f"{interval_time_simple} {asset_pair}: RSI {rsi} and MACD list: {asset_dict[asset_pair]['macd']}"
      elif rsi > 65 and len(macd_list) >= 3:
        if macd_list[-3] > macd_list[-2] > macd_list[-1]:
          # sell asset
          print(f"{interval_time_simple} {asset_pair}: MACD in downward trend for 3 iterations: {macd_list[-3:]}, selling {asset_pair}")
          tg_message = f"{interval_time_simple} {asset_pair}: MACD in downward trend for 3 iterations: {macd_list[-3:]}, selling {asset_pair}"
          send_telegram_message()
          if float(sum(holdings_list)) > 0: # check if we have some in our holdings
            volume_to_sell = str(sum(holdings_list))
            if min_order_size() < float(volume_to_sell):
              order_output = sell_asset()
              if not order_output.json()['error']:
                macd_list.clear()
                rsi_list.clear()
                holdings_list.clear()
                asset_dict[asset_pair]["macd"] = macd_list
                asset_dict[asset_pair]["rsi"] = rsi_list
                asset_dict[asset_pair]["holdings"] = holdings_list
                f = open(asset_file, "w")
                f.write(json.dumps(asset_dict))
                f.close()
                print(f"{interval_time_simple} {asset_pair}: Sold {volume_to_sell}")
                tg_message = order_output.json()['result']
                send_telegram_message()        
              else:
                print(f"{interval_time_simple} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}")
                tg_message = f"{interval_time_simple} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}"
                send_telegram_message()
            else:
              # clear rsi/macd lists from asset_dict
              macd_list.clear()
              rsi_list.clear()
              asset_dict[asset_pair]["macd"] = macd_list
              asset_dict[asset_pair]["rsi"] = rsi_list
              f = open(asset_file, "w")
              f.write(json.dumps(asset_dict))
              f.close()
              print(f"{interval_time_simple} {asset_pair}: Not enough left to sell")
              tg_message = f"{interval_time_simple} {asset_pair}: Not enough left to sell"
              send_telegram_message()
          else:
            # clear rsi/macd lists from asset_dict
            macd_list.clear()
            rsi_list.clear()
            asset_dict[asset_pair]["macd"] = macd_list
            asset_dict[asset_pair]["rsi"] = rsi_list
            f = open(asset_file, "w")
            f.write(json.dumps(asset_dict))
            f.close()
            print(f"{interval_time_simple} {asset_pair}: Nothing left to sell because we own 0 of it")  
            tg_message = f"{interval_time_simple} {asset_pair}: Nothing left to sell because we own 0 of it"
            send_telegram_message()
        else:
          print(f"{interval_time_simple} {asset_pair}: No downward MACD trend yet")
          macd = get_macd() 
          macd_list.append(macd)
          asset_dict[asset_pair]["macd"] = macd_list
          # write to asset_file
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
      else:
        print(f"{interval_time_simple} {asset_pair}: RSI {rsi}, nothing to do. Checking back in {loop_time_seconds} seconds")
        tg_message = f"{interval_time_simple} {asset_pair}: RSI {rsi}, nothing to do. Checking back in {loop_time_seconds} seconds"
        send_telegram_message()
      time.sleep(3) # sleep 3 seconds between asset pair
    list_24h.clear()
  time.sleep(loop_time_seconds)