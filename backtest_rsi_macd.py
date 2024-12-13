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
import itertools
import warnings

warnings.filterwarnings("ignore")

# set vars
## general vars

asset_dict = {}
asset_pairs = ['XXBTZUSD', 'XXRPZUSD', 'XETHZUSD', 'ADAUSD', 'SOLUSD']
# asset_pairs = ['XXBTZUSD']
asset_csv_dir = "/home/str1der/crypto/kraken_ohlc/30-11-24"
pd.options.display.max_rows = 9999999
pd.options.display.max_columns = 8
api_url = "https://api.kraken.com"
rsi_lower_boundary = 70
rsi_upper_boundary = 30
# interval_time_minutes = 1 # 4h timeframe
# interval_time_minutes = 1440 # 1d timeframe
# interval_time_minutes = 10080 # 1w timeframe
# interval_time_minutes = 60 # 1h timeframe
# interval_time_minutes = 15 # 15m timeframe
# interval_time_minutes = 30 # 30m timeframe
data_dict = {}
# balance_usd = 5000
order_size = 1000
# intervals = ['1', '5', '15', '30', '60', '240', '720', '1440']
# intervals = [1, 5, 15, 30, 60, 240, 720, 1440]
# intervals = [240]
intervals = [1]

#api_sec = os.environ['kraken_private_key']
#api_key = os.environ['kraken_api_key']

# functions
def get_asset_code(asset_pair):
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

def get_asset_pair_short(asset_pair):
    if asset_pair == "XXBTZUSD":
      asset_pair_short = "XBTUSD"
    if asset_pair == "XXRPZUSD":
      asset_pair_short = "XRPUSD"
    if asset_pair == "ADAUSD":
      asset_pair_short = "ADAUSD"
    if asset_pair == "SOLUSD":
      asset_pair_short = "SOLUSD"
    if asset_pair == "XETHZUSD":
      asset_pair_short = "ETHUSD"
    return asset_pair_short

def get_ohlc():
    df = pd.read_csv(asset_csv_dir + '/' + asset_pair_short + '_' + str(interval_time_minutes) + '.csv')
    df.columns = ['unixtimestamp', 'open', 'high', 'low', 'close', 'volume', 'count']
    return df

def get_close():
    # time.sleep(2)
    ohlc_data = get_ohlc()
    close_data = ohlc_data['close'].astype(float)
    return close_data

def get_time():
    # time.sleep(2)
    ohlc_data = get_ohlc()
    time_data_dict = ohlc_data['unixtimestamp'].to_dict()
    time_data_list = list(time_data_dict.values())
    time_data_list_datetime = []
    for i in time_data_list:
      normal_time_unformatted = datetime.datetime.utcfromtimestamp(i)
      normal_time = normal_time_unformatted.strftime('%Y-%m-%d %H:%M:%S')
      time_data_list_datetime.append(normal_time)
    return time_data_list_datetime

def get_macd():
    # close = get_ohlcdata_macd()
    close = get_close()
    # macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=3, slowperiod=12, signalperiod=6)
    macd_dict = macd.to_dict()
    macd_values = list(macd_dict.values())
    return macd_values

def get_rsi(period: int = 14, round_rsi: bool = True):
    close_data = get_close()
    delta = close_data.diff()
    up = delta.copy()
    up[up < 0] = 0 
    up = pd.Series.ewm(up, alpha=1/period).mean()
    down = delta.copy()
    down[down > 0] = 0 
    down *= -1
    down = pd.Series.ewm(down, alpha=1/period).mean()
    rsi = np.where(up == 0, 0, np.where(down == 0, 100, 100 - (100 / (1 + up / down))))
    return np.round(rsi, 2) if round_rsi else rsi

def get_asset_amount():
    asset_amount_list = []
    close_list = get_close().tolist()
    for i in close_list:
      asset_amount_list.append(float(order_size)/float(i))
    return asset_amount_list

for asset_pair in asset_pairs:
  for interval_time_minutes in intervals:
    holdings = []
    asset_pair_short = get_asset_pair_short(asset_pair)
    asset_code = get_asset_code(asset_pair)
    time_list = get_time()
    macd_list = get_macd()
    rsi_list = get_rsi().tolist()
    close_list = get_close().tolist()
    amount_list = get_asset_amount()
    rsi_list_temp = []
    macd_list_temp = []
    amount_list_temp = []
    holdings_list = []
    price_bought_list = []
    balance_usd_temp = []
    balance_usd = 200000 # starting balance
    print(f"{asset_pair} {interval_time_minutes}m starting balance: {balance_usd}")
    print(f"{asset_pair} {interval_time_minutes}m order size: {order_size}")
    for (times, macd, rsi, close, amount) in zip(time_list, macd_list, rsi_list, close_list, amount_list):
      #print(f"{times}, {macd}, {rsi}, {close}, {amount}")
      # print(f"Balance USD: {balance_usd}")
      is_macd_float = isinstance(macd,float)
      if 0 < rsi < 100 and macd == macd: # NaN type is always not equal, also to itself
        # print(f"rsi {rsi} and macd is a float: {macd}")
        if len(rsi_list_temp) == 1:
          #print(f"Length RSI temp list: {rsi_list_temp}")
          if rsi_list_temp[0] < rsi_lower_boundary:
            #print(f"RSI in RSI temp list is lower than RSI lower boundary {rsi_lower_boundary}: {rsi_list_temp[0]}, keeping value in list")
            rsi = rsi_list_temp[0]
          elif rsi_list_temp[0] > rsi_upper_boundary:
            #print(f"RSI in RSI temp list is higher than RSI upper boundary {rsi_upper_boundary}: {rsi_list_temp[0]}, keeping value in list")
            rsi = rsi_list_temp[0]
          else:
            #print(f"RSI is between {rsi_lower_boundary} and {rsi_upper_boundary}: {rsi} so we're clearing it from the RSI temp list")
            rsi_list_temp.clear()
            rsi_list_temp.append(rsi)
        elif len(rsi_list_temp) == 0:
          #print(f"RSI temp list empty: {rsi_list_temp}, appending rsi {rsi} to list")
          rsi_list_temp.append(rsi)
        # if rsi < rsi_lower_boundary and len(macd_list_temp) < 3:
        if rsi < rsi_lower_boundary and len(macd_list_temp) < 2:
          #print(f"RSI: {rsi} and length of macd list temp lower than 3: {macd_list_temp}")
          macd_list_temp.append(macd)
        # if rsi < rsi_lower_boundary and len(macd_list_temp) >= 3:
        if rsi < rsi_lower_boundary and len(macd_list_temp) >= 2:
          #print(f"RSI: {rsi} and macd list temp: {macd_list_temp}")
          # if macd_list_temp[-3] < macd_list_temp[-2] < macd_list_temp[-1]:
          if macd_list_temp[-2] < macd_list_temp[-1]:
            #print(f"MACD in upward trend, buying asset")
            holdings_list.append(amount)
            # usd_bought = sum(holdings_list) * close
            balance_usd = balance_usd - order_size
            balance_usd_temp.append(balance_usd)
            # print(f"USD balance after buy: {balance_usd}")
            # print(f"Holdings list: {holdings_list}")
            price_bought_list.append(close)
            #print(f"Price bought list: {price_bought_list}")
            macd_list_temp.clear()
            rsi_list_temp.clear()
          else:
            #print(f"MACD list temp not in upward trend, appending {macd} to macd list temp")
            macd_list_temp.append(macd)
            #print(f"Appended macd {macd} to macd list temp: {macd_list_temp}")
        # elif rsi > rsi_upper_boundary and len(macd_list_temp) < 3:
        elif rsi > rsi_upper_boundary and len(macd_list_temp) < 2:
          #print(f"RSI {rsi} but macd list temp has not enough length: {macd_list_temp}")
          macd_list_temp.append(macd)
          #print(f"Appended {macd} to macd list temp, macd list temp: {macd_list_temp}")
        # elif rsi > rsi_upper_boundary and len(macd_list_temp) >= 3:
        elif rsi > rsi_upper_boundary and len(macd_list_temp) >= 2:
          #print(f"RSI {rsi} and macd list temp > 3: {macd_list_temp}")
          # if macd_list_temp[-3] > macd_list_temp[-2] > macd_list_temp[-1]:
          if macd_list_temp[-2] > macd_list_temp[-1]:
            #print(f"Downward macd trend for macd_list_temp: {macd_list_temp}, selling asset if we have any")
            if float(sum(holdings_list)) > 0:
              #print(f"Holdings greater than 0: {sum(holdings_list)}")
              price_bought_avg = sum(price_bought_list) / len(price_bought_list)
              #print(f"Avg price bought: {price_bought_avg}")
              # if close > price_bought_avg:
              usd_sold = sum(holdings_list) * close
              balance_usd = balance_usd + usd_sold
              #print(f"USD balance after sell: {balance_usd}")
              macd_list_temp.clear()
              rsi_list_temp.clear()
              price_bought_list.clear()
              holdings_list.clear()
             # else:
             #   #print(f"Avg too low")
             #   macd_list_temp.clear()
             #   rsi_list_temp.clear()
            else:
              #print(f"Nothing in our holdings, clearing rsi and macd temp list")
              macd_list_temp.clear()
              rsi_list_temp.clear()
          else:
            #print(f"No downward MACD trend yet, keeping rsi and appending macd {macd} to macd list")
            macd_list_temp.append(macd)
            #rsi_list_temp.clear()
        #else:
          #print(f"Nothing to do")
      #else:
        #print(f"Incorrect test for macd {macd} and rsi {rsi}") 
    print(f"Ending balance for {interval_time_minutes}m {asset_pair} with RSI < {rsi_lower_boundary} and RSI > {rsi_upper_boundary}: {balance_usd}")
    print(f"{asset_pair} {interval_time_minutes}m max drawdown: {min(balance_usd_temp)}")
    balance_usd = []
    balance_usd_temp.clear()
    time.sleep(2)
