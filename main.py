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
asset_pairs = ['XXBTZUSD', 'SOLUSD', 'XETHZUSD', 'MINAUSD']
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_url = "https://api.kraken.com"
tg_token = os.environ['telegram_token']
loop_time_seconds = 86400 # 1d - iteration time for main loop
api_sec = os.environ['kraken_private_key']
api_key = os.environ['kraken_api_key']

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
def get_min_order_size():
    time.sleep(2)
    resp = requests.get('https://api.kraken.com/0/public/AssetPairs')
    minimum_order_size = float(resp.json()['result'][asset_pair]['ordermin'])
    return minimum_order_size

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def buy_asset():
    time.sleep(2)
    print("Buying the following amount of", asset_pair, ":", order_size)
    buy_order = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": order_size,
        "pair": asset_pair
    }, api_key, api_sec)
    return buy_order

# main loop
while True:
  for asset_pair in asset_pairs:
    order_size = get_min_order_size()
    try:
      buy_asset()
      print(f"DCA: bought {asset_pair}")
      tg_message = f"DCA: bought {asset_pair}"
      send_telegram_message()
    except:
      print(f"DCA: exception occured trying to buy {asset_pair}")
      tg_message = f"DCA: exception occured trying to buy {asset_pair}"
      send_telegram_message()
    print(f"{asset_pair} block done, sleeping 3 seconds")
    time.sleep(3) # sleep 3 seconds between asset pair
  print(f"DCA: sleeping for {loop_time_seconds} seconds")
  tg_message = f"DCA: sleeping for {loop_time_seconds} seconds"
  send_telegram_message()
  time.sleep(loop_time_seconds)
