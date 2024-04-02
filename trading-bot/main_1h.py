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
import talib

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
# my_dict = {"asset1": {"rsi": 37, "macd": [1, 2, 3]}, "asset2": {"rsi": 40, "macd": [2, 3, 1]}}
asset_dict = {}
timeframe = "1h"
file_extension = '.json'
asset_file = timeframe + file_extension 
asset_file_path = './' + asset_file
asset_pairs = ['XXBTZUSD', 'XXRPZUSD', 'ADAUSD', 'SOLUSD', 'AVAXUSD', 'MATICUSD', 'XETHZUSD']

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

def send_telegram_message():
    token = tg_token
    chat_id = "481520678"
    message = tg_message
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    requests.get(url) # send message

# for loop for instantiating asset_dict 
for asset_pair in asset_pairs:
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

while True:
  # extract balance and print/send to telegram 
  usd_holdings = get_holdings()
  if not usd_holdings.json()['error']:
    balance = float(usd_holdings.json()['result']['ZUSD'])
    print(f"Current USD balance: {balance}")
  else:
    print(f"An error occured trying to get USD balance: {usd_holdings.json()['error']}")

  # main for loop for hourly loop
  for asset_pair in asset_pairs:
    # set asset code since Kraken asset codes are not consistent
    if asset_pair == "XXBTZUSD":
      asset_code = "XXBT"
    if asset_pair == "XXRPZUSD":
      asset_code = "XXRP"
    if asset_pair == "ADAUSD":
      asset_code = "ADA"
    if asset_pair == "SOLUSD":
      asset_code = "SOL"
    if asset_pair == "AVAXUSD":
       asset_code = "AVAX"
    if asset_pair == "MATICUSD":
      asset_code = "MATIC"
    if asset_pair == "XETHZUSD":
      asset_code = "XETH"

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

    # set variable for RSI
    rsi_list_values  = rsi_tradingview()
    rsi = float(rsi_list_values[-1])

    # set these vars for testing purposes
    # rsi = 25
    # macd_list = [1, 2, 3] # for buying asset
    # macd_list = [3, 2, 1] # for selling asset
    # order_size = 15

    print(f"{interval_time_simple} RSI  {asset_pair}: {rsi}")

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
  
    # open asset_dict, check for existing rsi value
    # if existing rsi value exists, overwrite it with a newly discovered one
    print(f"opening asset file {asset_file}")
    f = open(asset_file, "r")
    asset_json = f.read()
    f.close()
    asset_dict = json.loads(asset_json)
    macd_list = asset_dict[asset_pair]["macd"] 
    rsi_list = asset_dict[asset_pair]["rsi"]
    holdings_list = asset_dict[asset_pair]["holdings"]
    if not rsi_list:
      print(f"rsi list for  {asset_pair} empty, appending new rsi entry")
      # asset_pair rsi list empty, calculating rsi/macd and appending to list
      rsi_list.append(rsi)
      macd = get_macd()
      macd_list.append(macd)
      asset_dict[asset_pair]["rsi"] = rsi_list
      asset_dict[asset_pair]["macd"] = macd_list
      f = open(asset_file, "w")
      f.write(json.dumps(asset_dict))
      f.close()
      print(f"appended rsi value {rsi} for {asset_pair} to rsi list")
    else:
      # asset_pair has rsi, reading rsi value and macd list
      print(f"rsi list for {asset_pair} not empty, reading value")
      rsi = rsi_list[0]
      if rsi < 35 and len(macd_list) < 3:
        print(f"{asset_pair} RSI: {rsi} and length of macd list: {len(asset_dict[asset_pair]['macd'])}")
        # append macd value to macd list
        macd = get_macd() 
        macd_list.append(macd)
        asset_dict[asset_pair]["macd"] = macd_list
        # write to asset_file
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
        print(f"Appended {macd} macd value to macd list for {asset_pair}")
        print(f"{asset_pair} MACD list: {asset_dict[asset_pair]['macd']}")
        tg_message = f"{asset_pair} RSI: {rsi} and MACD list: {asset_dict[asset_pair]['macd']}"
        send_telegram_message()
      elif rsi < 35 and len(macd_list) >= 3:
        print(f"{asset_pair} RSI: 35 and macd_list >= 3 for {asset_pair}")
        tg_message = f"RSI < 35 and macd_list >= 3 for {asset_pair}")
        send_telegram_message()
        if macd_list[-3] < macd_list[-2] < macd_list[-1]:
          # buy asset
          buy_asset = True
          print(f"Buying {asset_pair}")
          print(f"MACD in upward trend for 3 iterations, buying {asset_pair}")
          if buy_asset:
            buy_amount = random.randint(1,100)
            # clear rsi/macd lists from asset_dict
            macd_list.clear()
            rsi_list.clear()
            holdings_list.append(buy_amount)
            asset_dict[asset_pair]["macd"] = macd_list
            asset_dict[asset_pair]["rsi"] = rsi_list
            asset_dict[asset_pair]["holdings"] = holdings_list
            f = open(asset_file, "w")
            f.write(json.dumps(asset_dict))
            f.close()
        else: 
          # append macd value to macd list
          macd = random.randint(1,100)
          macd_list.append(macd)
          asset_dict[asset_pair]["macd"] = macd_list
          # write to asset_file
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
      elif rsi > 65 and len(macd_list) < 3:
        # append macd value to macd list
        macd = random.randint(1,100)
        macd_list.append(macd)
        asset_dict[asset_pair]["macd"] = macd_list
        # write to asset_file
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
      elif rsi > 65 and len(macd_list) >= 3:
        if macd_list[-3] > macd_list[-2] > macd_list[-1]:
          # sell asset
          sell_asset = True
          print(f"Selling {asset_pair}")
          if sell_asset:
            # clear rsi/macd/holdings lists from asset_dict
            macd_list.clear()
            rsi_list.clear()
            holdings_list.clear()
            asset_dict[asset_pair]["macd"] = macd_list
            asset_dict[asset_pair]["rsi"] = rsi_list
            asset_dict[asset_pair]["holdings"] = holdings_list
            f = open(asset_file, "w")
            f.write(json.dumps(asset_dict))
            f.close()
        else: 
          # append macd value to macd list
          macd = random.randint(1,100)
          macd_list.append(macd)
          asset_dict[asset_pair]["macd"] = macd_list
          # write to asset_file
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
      else:
        print(f"rsi value read from file is {rsi}, calculating new rsi value and adding it to file")
        rsi = random.randint(1,100)
        rsi_list.clear()
        rsi_list.append(rsi)
        asset_dict[asset_pair]["rsi"] = rsi_list
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
    time.sleep(1) 
