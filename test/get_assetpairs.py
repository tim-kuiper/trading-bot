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

  def get_assetpairs():
      req = kraken_request('/0/public/AssetPairs', {"nonce": str(int(1000*time.time()))}, api_key, api_sec)
      return req

  def test():
      req = requests.get('https://api.kraken.com/0/public/AssetPairs')
      return req

output = test().json()
print(output)
time.sleep(1000)
