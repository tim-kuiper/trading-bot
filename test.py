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
from tenacity import *

# set vars
## general vars
asset_dict = {}
asset_pairs = ['XXBTZUSD', 'XXRPZUSD', 'ADAUSD', 'SOLUSD', 'XETHZUSD']
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_url = "https://api.kraken.com"
tg_token = os.environ['telegram_token']
list_1h = []
list_4h = []
list_24h = []
start_list_24h = [] # use this list in combination with the regular 24h list in order to execute the 24h block without waiting a full day
loop_time_seconds = 14400
rsi_lower_boundary = 31
rsi_upper_boundary = 69
api_sec = os.environ['kraken_private_key']
api_key = os.environ['kraken_api_key']

# functions
def get_asset_code():
    ## asset pair specific vars
    if asset_pair == "XXBTZUSD":
      asset_code = "XXBT"
    if asset_pair == "XXRPZUSD":
      asset_code = "XXRP"
    if asset_pair == "ADAUSD":
      asset_code = "ADA"
    if asset_pair == "SOLUSD":
      asset_code = "SOL"
    if asset_pair == "XETHZUSD":
      asset_code = "XETH"
    return asset_code
    
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

holdings = get_holdings()
print(f"holdings: {holdings.json()['result']}")
for asset_pair in asset_pairs:
  asset_code = get_asset_code()
  if asset_code in holdings.json()['result']:
    if float(holdings.json()['result'][asset_code]) > 0:
       print(f"Asset {asset_pair} present in our holdings")
    else:
       print(f"Asset {asset_pair} not present in our holdings")
  else:
     print(f"Asset pair {asset_pair} not present")
       