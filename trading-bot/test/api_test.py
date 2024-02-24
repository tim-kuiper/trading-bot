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
from pathlib import Path

api_sec = os.environ['api_sec_env']
api_key = os.environ['api_key_env']
api_url = "https://api.kraken.com"

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

def get_asset_close():
    payload = {'pair': asset_pair}
    resp = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
    close_value = resp.json()['result'][asset_pair]['c'][0]
    return close_value

# construct  request to get balance
# resp = kraken_request('/0/private/Balance', {"nonce": str(int(1000*time.time()))}, api_key, api_sec)
asset_pairs = ['XXBTZUSD', 'XETHZUSD', 'XXRPZUSD', 'ADAUSD', 'SOLUSD']
# usd_order_size = float(30)
#for asset_pair in asset_pairs:
#  resp = requests.get('https://api.kraken.com/0/public/AssetPairs')
#  size = float(resp.json()['result'][asset_pair]['ordermin'])
#  asset_close = float(get_asset_close())
#  amount_to_buy = float((usd_order_size / asset_close) * 10)
#  #print("USD Close for", asset_pair, ":", asset_close)
#  print("Amount to buy of", asset_pair, ":", amount_to_buy)

resp = requests.get('https://api.kraken.com/0/public/AssetPairs')
print(resp.json())

