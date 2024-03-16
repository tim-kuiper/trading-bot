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
Trading script utilizing the Kraken API to buy/sell asset pairs based on RSI+MACD for DCA
'''

# set vars
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_sec = os.environ['api_sec_env_btc']
api_key = os.environ['api_key_env_btc']
api_url = "https://api.kraken.com"
tg_token = os.environ['telegram_token']
loop_time_seconds = 3600
interval_time_minutes = 60
interval_time_simple = '1h'
asset_list = []
order_size = 50

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

  # returns our holdings
  def get_holdings():
      holdings = kraken_request('/0/private/Balance', {"nonce": str(int(1000*time.time()))}, api_key, api_sec)
      return holdings

  # send message to our telegram bot
  def send_telegram_message():
      token = tg_token
      chat_id = "481520678"
      message = tg_message
      url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
      requests.get(url) # send message
      
  # extract balance and print/send to telegram 
  usd_holdings = get_holdings()
  if not usd_holdings.json()['error']:
    balance = float(usd_holdings.json()['result']['ZUSD']) 
    print(f"Current USD balance: {balance}")
  else:
    print(f"An error occured trying to get USD balance: {usd_holdings.json()['error']}")
 
  # set asset pairs and start looping over them
  
  asset_pairs = ['ADAUSD']

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

    # set vars for file / file path
    file_extension = '.json'
    asset_file = asset_code.lower() + '_' + interval_time_simple  + file_extension
    asset_file_path = './' + asset_file

    # get min order size for asset_pair
    def min_order_size():
        time.sleep(2)
        resp = requests.get('https://api.kraken.com/0/public/AssetPairs')
        minimum_order_size = float(resp.json()['result'][asset_pair]['ordermin'])
        return minimum_order_size

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
    rsi  = rsi_tradingview()
    hourly_rsi = float(rsi[-1])
   
    # set variable for MACD list
    macd_list = []

    # set these vars for testing purposes
    # hourly_rsi = 75
    # macd_list = [1, 2, 3] # for buying asset
    # macd_list = [3, 2, 1] # for selling asset
    # order_size = 15

    print(f"{interval_time_simple} RSI  {asset_pair}: {hourly_rsi}")

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

    # buy asset
    if hourly_rsi < 35:
      print(f"{asset_pair}: {interval_time_simple} RSI {hourly_rsi}, looking for buy opportunity")
      tg_message = f"{asset_pair}: {interval_time_simple} RSI {hourly_rsi}, looking for buy opportunity"
      send_telegram_message()
      while len(macd_list) < 3:
        # keep adding macd values to list until it has 3 values in it
        macd_value = get_macd()
        print(f"Adding {macd_value} to {asset_pair} MACD value list")
        macd_list.append(macd_value)
        time.sleep(loop_time_seconds)
      while macd_list[-1] < macd_list[-2] < macd_list[-3]:
        # keep adding macd values to list until macd_list[-1] > macd_list[-2] > macd_list[-3]
        macd_value = get_macd()
        print(f"Adding {macd_value} to {asset_pair} MACD value list")
        macd_list.append(macd_value)
        print(f"{asset_pair}: No upward MACD trend, waiting to buy. Checking back again in {loop_time_seconds} seconds")
        tg_message = f"{asset_pair}: No upward MACD trend, waiting to buy. Checking back again in {loop_time_seconds} seconds"
        send_telegram_message()
        time.sleep(loop_time_seconds)
      # buy asset
      print(f"MACD in upward trend for 3 iterations, buying {asset_pair}")
      if min_order_size() < order_size:
        asset_close = float(get_asset_close())
        usd_order_size = order_size
        volume_to_buy = str(float(usd_order_size / asset_close))
        order_output = buy_asset() # executes buy order and assigns output to var
        if not order_output.json()['error']:
          macd_list.clear()
          asset_list.append(float(volume_to_buy))
          print(f"Bought {volume_to_buy} of {asset_pair}")
          tg_message = order_output.json()['result']
          send_telegram_message()
          file_exists = os.path.exists(asset_file_path)
          if not file_exists:
            print(f"Asset file {asset_file} does not exist yet, creating one")
            f = open(asset_file, "w")
            f.write(json.dumps(asset_list))
            f.close
            print(f"Appended {asset_list} to {asset_file}")
          else:
            print(f"Asset file {asset_file} already exists, reading from file and appending {volume_to_buy} {asset_code} to it")
            f = open(asset_file, "r")
            asset_json = f.read()
            f.close
            asset_list = json.loads(asset_json)
            asset_list.append(float(volume_to_buy))
            f = open(asset_file, "w")
            f.write(json.dumps(asset_list))
            f.close
            print(f"Appended {volume_to_buy} to {asset_file}")
        else:
          macd_list.clear()
          print(f"An error occured while trying to place a {asset_pair} buy order: {order_output.json()['error']}")
          tg_message = f"An error occured while trying to place a {asset_pair} buy order: {order_output.json()['error']}"
          send_telegram_message()
      else:
        macd_list.clear()
        print(f"Not enough {asset_pair} left to buy, checking back later")
        tg_message = f"Not enough {asset_pair} left to buy, checking back later"
        send_telegram_message()
    # sell asset
    elif hourly_rsi > 65:
      print(f"{asset_pair}: {interval_time_simple} RSI {hourly_rsi}, looking for sell opportunity if we have {asset_pair} in our holdings")
      tg_message = f"{asset_pair}: {interval_time_simple} RSI {hourly_rsi}, looking for sell opportunity if we have {asset_pair} in our holdings"
      send_telegram_message()
      while len(macd_list) < 3:
        # keep adding macd values to list until it has 3 values in it
        macd_value = get_macd()
        print(f"Adding {macd_value} to {asset_pair} MACD value list")
        macd_list.append(macd_value)
        time.sleep(loop_time_seconds)
      while macd_list[-1] > macd_list[-2] > macd_list[-3]:
        # keep adding macd values to list until macd_list[-1] < macd_list[-2] < macd_list[-3]
        macd_value = get_macd()
        print(f"Adding {macd_value} to {asset_pair} MACD value list")
        macd_list.append(macd_value)
        print(f"{asset_pair}: No downward MACD trend, waiting to sell. Checking back again in {loop_time_seconds} seconds")
        tg_message = f"{asset_pair}: No downward MACD trend, waiting to sell. Checking back again in {loop_time_seconds} seconds"
        send_telegram_message()
        time.sleep(loop_time_seconds)
      if asset_code in get_holdings().json()['result']: # check whether asset is present in our holdings
        if float(get_holdings().json()['result'][asset_code]) > 0: # check whether we actually have more than 0
          # check our asset list and determine the volume to sell
          file_exists = os.path.exists(asset_file_path)
          if not file_exists:
            print(f"We dont have an asset file, so there is nothing to sell")
          else:
            print(f"We do have an asset file, reading asset file")
            f = open(asset_file, "r")
            asset_json = f.read()
            asset_list = json.loads(asset_json)
            volume_to_sell = str(sum(asset_list))
            f.close()
          # volume_to_sell = str(float(get_holdings().json()['result'][asset_code]))
            # if min_order_size() < float(get_holdings().json()['result'][asset_code]):
            if min_order_size() < float(volume_to_sell):
              print(f"Selling {volume_to_sell} of {asset_pair}")
              order_output = sell_asset() # executes sell order and assigns output to var
              if not order_output.json()['error']:
                asset_list.clear()
                print(f"Removing {asset_file} from the current directory")
                os.remove(asset_file)
                print(f"Removed {asset_file} from the current directory")
                print(f"Sold {volume_to_sell} of {asset_pair}")
                tg_message = order_output.json()['result']
                send_telegram_message()
              else:
                print(f"An error occured when trying to place a sell order for {asset_pair}: {order_output.json()['error']}")
                tg_message = f"An error occured when trying to place a sell order for {asset_pair}: {order_output.json()['error']}"
                send_telegram_message()
            else:
              print(f"Not enough {asset_pair} left to sell, checking back later")
              tg_message = f"Not enough {asset_pair} left to sell, checking back later"
              send_telegram_message()
        else:
          print(f"No {asset_pair} to sell because we own 0 of it")
          tg_message = f"No {asset_pair} to sell because we own 0 of it"
          send_telegram_message()
      else:
        print(f"No {asset_pair} to sell because we don't have it in our holdings")
        tg_message = f"No {asset_pair} to sell because we don't have it in our holdings"
        send_telegram_message()
    else:
      print(f"{asset_pair} {interval_time_simple} RSI {hourly_rsi}")
      tg_message = f"{asset_pair} {interval_time_simple} RSI {hourly_rsi}"
      send_telegram_message()
  print(f"Current date/time: {time.asctime()}")
  print(f"Current asset holdings: {get_holdings().json()['result']}")
  print(f"Checking back again in {loop_time_seconds} seconds")
  time.sleep(loop_time_seconds)
