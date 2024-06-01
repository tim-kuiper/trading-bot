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
loop_time_seconds = 14400
rsi_lower_boundary = 35
rsi_upper_boundary = 65
file_extension = '.json'
timeframe = "4h"
asset_file = timeframe + file_extension 
asset_file_path = './' + asset_file

def check_create_asset_file():
    global asset_dict
    print(f"Asset dict: {asset_dict}")
    asset_file_exists = os.path.exists(asset_file_path)
    # create file if it doesnt exist, add dictionary per asset to it
    if not asset_file_exists:
      print(f"Asset file {asset_file} doesnt exist , creating one")
      # asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": [], "price_bought": []}})
      asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": []}})
      print(f"Asset dict: {asset_dict}")
      write_to_asset_file()
    else:
      print(f"Asset file {asset_file} exists, reading")
      asset_dict = json.loads(read_asset_file())
      print(f"Asset dict keys: {asset_dict.keys()}")
      if asset_pair not in asset_dict.keys():
        print(f"Asset pair {asset_pair} not present in asset file {asset_file}, updating file")
        # asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": [], "price_bought": []}})
        asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": []}})
        print(f"Asset dict: {asset_dict}")
        write_to_asset_file()
        print(f"Appended {asset_pair} to {asset_file}")
      if "price_bought" not in asset_dict[asset_pair].keys():
        print(f"price bought not present in asset dict, appending")
        y = {"price_bought": []}
        asset_dict[asset_pair].update(y)
        write_to_asset_file()

def write_to_asset_file():
    try:
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
    except OSError as e:
        print(f"Error opening asset file: {e}")

def read_asset_file():
    try:
        f = open(asset_file, "r")
        asset_json = f.read()
        f.close()
        return asset_json
    except OSError as e:
        print(f"Error opening asset file: {e}")

for asset_pair in asset_pairs:
  check_create_asset_file()
  time.sleep(1)
