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
Trading script utilizing the Kraken API to buy/sell asset pairs based on RSI for DCA
'''

# set vars
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_sec = os.environ['api_sec_env_btc']
api_key = os.environ['api_key_env_btc']
api_url = "https://api.kraken.com"
tg_token = os.environ['telegram_token']

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
    print("Current USD balance: ", balance)
  else:
    print("An error occured trying to get USD balance:", usd_holdings.json()['error'])

  # set asset pairs and start looping over them

  # asset_pairs = ['XXBTZUSD', 'XXRPZUSD', 'ADAUSD', 'SOLUSD']
  asset_pairs = ['XXBTZUSD']

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
        payload = {'pair': asset_pair, 'interval': 60}
        ohlc_data_raw = requests.get('https://api.kraken.com/0/public/OHLC', params=payload)
        if not ohlc_data_raw.json()['error']:
          # construct a dataframe and assign columns using asset ohlc data
          df = pd.DataFrame(ohlc_data_raw.json()['result'][asset_pair])
          df.columns = ['unixtimestap', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
          # we are only interested in asset close data, so create var for close data columns and set var type as float
          # close_data = df['close'].astype(float) # set close data to float
          close_data = df['close']
          return close_data
        else:
          print("Error requesting", asset_pair, "OHLC data:", ohlc_data_raw.json()['error'])
          tg_message = "Error requesting", asset_pair, "OHLC data", ohlc_data_raw.json()['error']
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

    def get_orderinfo():
        time.sleep(2)
        resp = kraken_request('/0/private/QueryOrders', {
            "nonce": str(int(1000*time.time())),
            "txid": transaction_id,
            "trades": True
             }, api_key, api_sec)
        return resp

    volume_to_buy = min_order_size()
    order_output = buy_asset()
    print(order_output.json())
    transaction_id = order_output.json()['result']['txid'][0]
    order_info  = get_orderinfo()
    executed_size = float(order_info.json()['result'][transaction_id]['vol_exec'])
    print(f"Executed size: {executed_size}")
    time.sleep(3600)
