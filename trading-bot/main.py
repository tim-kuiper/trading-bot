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

'''
Trading script utilizing the Kraken API to buy/sell BTCUSDT on RSI for DCA
Notes:
- Using Kraken API key 
- Using API built from flask able to receive HTTP(S) POST requests from Tradingview in order to obtain RSI value of asset
- Based on 1H BTCUSDT chart, executing a potential buy with the following properties:
  - RSI between 45-30: 0.005*0.75*balance
  - RSI <30: 0.01*0.75*balance
  - If a trade is executed (BTC is bought) then the value of BTC in USDT during execution is stored in a list
- List values should be stored and each hour the avg of this list should be printed, indicating the avg price that BTC was bought for
- When asset is sold, which is will be done manually for the time being, the list must be stored somewhere and a new list should be made starting the above process again
'''

# set vars
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_sec = os.environ['api_sec_env']
api_key = os.environ['api_key_env']
api_url = "https://api.kraken.com"
avg_btc_value = []
total_btc_assets = []

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
        # get_kraken_signature() as defined in the 'Authentication' section
        headers['API-Sign'] = get_kraken_signature(uri_path, data, api_sec)             
        req = requests.post((api_url + uri_path), headers=headers, data=data)
        return req
    
    # construct  request to get balance
    resp = kraken_request('/0/private/Balance', {
        "nonce": str(int(1000*time.time()))
    }, api_key, api_sec)
    
    # extract balance and do some calculcations according to the trade strategy
    balance_data = resp.json()
    balance_float = float(balance_data['result']['USDT'])
    balance = int(balance_float)
    dca_balance = int(balance) * 0.75
    rsi45_balance = int(dca_balance) * 0.005
    rsi30_balance = int(dca_balance) * 0.01
    
    # set asset pair
    asset_pair = 'XBTUSDT'
    
    print("Total balance: ", balance)
    print("DCA balance: ", dca_balance)
    print("RSI < 45 balance: ", rsi45_balance)
    print("RSI < 30 balance: ", rsi30_balance)
    
    # get ohcl (open/high/close/low) data from kraken using the hourly (1H) interval
    ohlc_data_raw = requests.get('https://api.kraken.com/0/public/OHLC?pair=XBTUSDT&interval=60')
    
    # construct a dataframe and assign columns using ohlc data
    df = pd.DataFrame(ohlc_data_raw.json()['result']['XBTUSDT'])
    df.columns = ['unixtimestap', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
    
    # we are only interested in the close data, so create var for close data columns and set var type as float
    close_data = df['close'].astype(float) # set close data to float
    
    # define function to display RSI (tradingview calculcation)
    def rsi_tradingview(period: int = 14, round_rsi: bool = True):
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
    
    # set variable for hourly rsi
    rsi = rsi_tradingview()
    hourly_rsi = float(rsi[-1])
    
    print("1H RSI:", hourly_rsi)
    
    if 30 <= hourly_rsi <= 45:
      print("30 <= hourly_rsi <= 45 block")
      # calculate how much btc we can buy according to the strategy, for this we need to convert an X amount of USDT to BTC value
      payload = {'pair': asset_pair}
      request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
      ask_value = request.json()['result'][asset_pair]['a'][0]
      current_btc_value = int(float(ask_value))
      
    elif hourly_rsi < 30:
      print("rsi<30 block")
    
    
    
    # place market order if rsi <45 or <35
    
    
    # sleep for 1 hour
    time.sleep(3600)
