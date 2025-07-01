import urllib.parse
import argparse
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
import sys

parser = argparse.ArgumentParser(description="Add trading bot arguments")
parser.add_argument("timeframe", type=str, help="Add timeframe (1m/5m/15m/30m/1h/4h/1d/1w)")
parser.add_argument("order_size", type=int, help="Order size in USD")
parser.add_argument("strategy", type=str, help="Strategy (dca-macd-rsi/dca-flat/macd-crossover/rsi/macd-rsi)")
args = parser.parse_args()

# program args
timeframe = args.timeframe
order_size = args.order_size
strategy = args.strategy

# set vars
## general vars
asset_dict = {}
asset_pairs = ['XXBTZUSD', 'XXRPZUSD', 'ADAUSD', 'SOLUSD', 'XETHZUSD']
pd.options.display.max_rows = 999
pd.options.display.max_columns = 8
api_url = "https://api.kraken.com"
tg_token = os.environ['telegram_token']
loop_time_seconds = 86400
rsi_lower_boundary = 35
rsi_upper_boundary = 65
api_sec = os.environ['kraken_private_key']
api_key = os.environ['kraken_api_key']

def get_asset_code():
    """Get asset code from asset pair
       TODO: use asset_pair as function arg 
    """
    if asset_pair == "XXBTZUSD":
        kraken_asset_code = "XXBT"
    if asset_pair == "XXRPZUSD":
        kraken_asset_code = "XXRP"
    if asset_pair == "ADAUSD":
        kraken_asset_code = "ADA"
    if asset_pair == "SOLUSD":
        kraken_asset_code = "SOL"
    if asset_pair == "XETHZUSD":
        kraken_asset_code = "XETH"
    if asset_pair == "MINAUSD":
        kraken_asset_code = "MINA"
    return kraken_asset_code

def send_telegram_message():
    """Send TG message
       TODO: use telegram token and message as function arg
    """
    token = tg_token
    chat_id = "481520678"
    message = tg_message
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    requests.get(url, timeout=10) # send tg msg

def get_kraken_signature(urlpath, data, secret):
    """Create HMAC signature from request"""
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()

def kraken_request(uri_path, data, api_key, api_sec):
    """Construct request for Kraken API using API credentials"""
    headers = {}
    headers['API-Key'] = api_key
    headers['API-Sign'] = get_kraken_signature(uri_path, data, api_sec)
    req = requests.post((api_url + uri_path), headers=headers, data=data, timeout=10)
    return req

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def get_holdings():
    """Function for obtaining holdings"""
    kraken_holdings = kraken_request('/0/private/Balance', {"nonce": str(int(1000*time.time()))}, api_key, api_sec)
    return kraken_holdings

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def min_order_size():
    """Obtain minimum order size for asset pair
       TODO: use asset_pair as function arg
    """
    time.sleep(2)
    resp = requests.get('https://api.kraken.com/0/public/AssetPairs', timeout=10)
    minimum_order_size = float(resp.json()['result'][asset_pair]['ordermin'])
    return minimum_order_size

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def get_asset_close():
    """Get last asset close price
       TODO: Use asset_pair as function arg
    """
    time.sleep(2)
    payload = {'pair': asset_pair}
    resp = requests.get('https://api.kraken.com/0/public/Ticker', params=payload, timeout=10)
    close_value = resp.json()['result'][asset_pair]['c'][0]
    return close_value

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def get_ohlcdata():
    """Get OHLC (Open/High/Low/Close) data for asset pair
       TODO: Use asset_pair and interval_time_minutes as function arg
    """
    time.sleep(2)
    payload = {'pair': asset_pair, 'interval': interval_time_minutes}
    ohlc_data_raw = requests.get('https://api.kraken.com/0/public/OHLC', params=payload, timeout=10)
    df = pd.DataFrame(ohlc_data_raw.json()['result'][asset_pair])
    df.columns = ['unixtimestap', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
    close_data = df['close'].astype(float) # set close data to float
    return close_data

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def get_ohlcdata_macd():
    """Get OHLC data without float type for MACD
       TODO: Use asset_pair and interval_time_minutes as function arg
    """
    time.sleep(2)
    payload = {'pair': asset_pair, 'interval': interval_time_minutes}
    ohlc_data_raw = requests.get('https://api.kraken.com/0/public/OHLC', params=payload, timeout=10)
    # construct a dataframe and assign columns using asset ohlc data
    df = pd.DataFrame(ohlc_data_raw.json()['result'][asset_pair])
    df.columns = ['unixtimestap', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
    # we are only interested in asset close data, so create var for close data columns and set var type as float
    close_data = df['close']
    return close_data

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def get_orderinfo():
    """Get information about open order with TXID as input
       TODO: Use TXID as function arg  
    """
    time.sleep(2)
    resp = kraken_request('/0/private/QueryOrders', {
        "nonce": str(int(1000*time.time())),
        "txid": transaction_id,
        "trades": True
    }, api_key, api_sec)
    return resp

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def buy_asset():
    """Buy asset_pair with volume_to_buy amount
       TODO: Use asset_pair and volume_to_buy as function arg
    """
    print("Buying the following amount of", asset_pair, ":", volume_to_buy)
    buy_order = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "buy",
        "volume": volume_to_buy,
        "pair": asset_pair
    }, api_key, api_sec)
    return buy_order

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def sell_asset():
    """Sell asset_pair with volume_to_sell amount
       TODO: use asset_pair and volume_to_sell as function args
    """
    print("Selling the following amount of", asset_pair, ":", volume_to_sell)
    sell_order = kraken_request('/0/private/AddOrder', {
        "nonce": str(int(1000*time.time())),
        "ordertype": "market",
        "type": "sell",
        "volume": volume_to_sell,
        "pair": asset_pair
    }, api_key, api_sec)
    return sell_order

def rsi_tradingview(period: int = 14, round_rsi: bool = True):
    """Calculate RSI based on TradingView calculation
       TODO: add source for this calculation
    """
    delta = get_ohlcdata().diff()
    up = delta.copy()
    up[up < 0] = 0
    up = pd.Series.ewm(up, alpha=1/period).mean()
    down = delta.copy()
    down[down > 0] = 0
    down *= -1
    down = pd.Series.ewm(down, alpha=1/period).mean()
    rsi_tv = np.where(up == 0, 0, np.where(down == 0, 100, 100 - (100 / (1 + up / down))))
    return np.round(rsi_tv, 2) if round_rsi else rsi_tv

def get_macd():
    """Calculate MACD value
       TODO: use get_ohlcdata_macd return value as function arg
    """
    close = get_ohlcdata_macd()
    macd_value, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd_dict = macd_value.to_dict()
    macd_values = list(macd_dict.values())
    return macd_values[-1]

def check_create_asset_file():
    """Check if asset file exists, otherwise create a JSON asset file with asset_pairs
       TODO: remove global asset_dict var from this function, its not neat
    """
    global asset_dict
    asset_file_exists = os.path.exists(asset_file_path)
    if not asset_file_exists:
        print(f"Asset file {asset_file} doesnt exist , creating one")
        asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": [], "price_bought": [], "avg_price_bought": [], "current_price": [], "price_difference_pct": []}})
        write_to_asset_file()
    else:
        print(f"Asset file {asset_file} exists, reading")
        asset_dict = json.loads(read_asset_file())
        if asset_pair not in asset_dict.keys():
            print(f"Asset pair {asset_pair} not present in asset file {asset_file}, updating file")
            asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": [], "price_bought": [], "avg_price_bought": [], "current_price": [], "price_difference_pct": []}})
            write_to_asset_file()
            print(f"Appended {asset_pair} to {asset_file}")
        if "rsi" not in asset_dict[asset_pair].keys():
            y = {"rsi": []} 
            asset_dict[asset_pair].update(y)
            write_to_asset_file()
        if "macd" not in asset_dict[asset_pair].keys():
            y = {"macd": []} 
            asset_dict[asset_pair].update(y)
            write_to_asset_file()
        if "holdings" not in asset_dict[asset_pair].keys():
            y = {"holdings": []} 
            asset_dict[asset_pair].update(y)
            write_to_asset_file()
        if "price_bought" not in asset_dict[asset_pair].keys():
            y = {"price_bought": []} 
            asset_dict[asset_pair].update(y)
            write_to_asset_file()
        if "avg_price_bought" not in asset_dict[asset_pair].keys():
            y = {"avg_price_bought": []} 
            asset_dict[asset_pair].update(y)
            write_to_asset_file()
        if "current_price" not in asset_dict[asset_pair].keys():
            y = {"current_price": []} 
            asset_dict[asset_pair].update(y)
            write_to_asset_file()
        if "price_difference_pct" not in asset_dict[asset_pair].keys():
            y = {"price_difference_pct": []} 
            asset_dict[asset_pair].update(y)
            write_to_asset_file()

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def write_to_asset_file():
    """Write the asset_dictionary to file"""
    f = open(asset_file, "w")
    f.write(json.dumps(asset_dict))
    f.close()

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(5))
def read_asset_file():
    """Read asset file into memory"""
    f = open(asset_file, "r")
    asset_json = f.read()
    f.close()
    return asset_json

def get_kraken_leverage():
    """Get leverage amount for asset pair on kraken
       TODO: dynamically obtain leverage ratio using Kraken API
    """
    if asset_pair == "XXBTZUSD":
        kraken_leverage = "5:1"
    if asset_pair == "XXRPZUSD":
        kraken_leverage= "5:1"
    if asset_pair == "ADAUSD":
        kraken_leverage = "3:1"
    if asset_pair == "SOLUSD":
        kraken_leverage = "4:1"
    if asset_pair == "XETHZUSD":
        kraken_leverage = "5:1"
    if asset_pair == "MINAUSD":
        kraken_leverage = "4:1"
    return kraken_leverage

def get_timeframe_in_seconds():
    """Convert timeframe to seconds
       TODO: use timeframe as input arg
    """
    if timeframe == "1m":
        loop_time_sec = 60
    elif timeframe == "5m":
        loop_time_sec = 300
    elif timeframe == "15m":
        loop_time_sec = 900
    elif timeframe == "30m":
        loop_time_sec = 1800
    elif timeframe == "1h":
        loop_time_sec = 3600
    elif timeframe == "4h":
        loop_time_sec = 14400
    elif timeframe == "1d":
        loop_time_sec = 86400
    elif timeframe == "1w":
        loop_time_sec = 604800
    return loop_time_sec

def get_timeframe_in_minutes():
    """Convert timeframe to seconds
       TODO: use timeframe as input arg
    """
    if timeframe == "1m":
        interval_time_min = 1
    elif timeframe == "5m":
        interval_time_min = 5
    elif timeframe == "15m":
        interval_time_min = 15
    elif timeframe == "30m":
        interval_time_min = 30
    elif timeframe == "1h":
        interval_time_min = 60
    elif timeframe == "4h":
        interval_time_min = 240
    elif timeframe == "1d":
        interval_time_min = 1440
    elif timeframe == "1w":
        interval_time_min = 10080
    return interval_time_min

loop_time_seconds = get_timeframe_in_seconds()
interval_time_minutes = get_timeframe_in_minutes()

if strategy == "dca-macd-rsi":
    while True:
        file_extension = '.json'
        asset_file = timeframe + file_extension 
        asset_file_path = './' + asset_file
        # interval_time_minutes = 1440
        # timeframe = '1d'
        # order_size = 25
        # loop over assets
        for asset_pair in asset_pairs:
            asset_code = get_asset_code()
            check_create_asset_file()
            rsi_list_values  = rsi_tradingview()
            rsi = float(rsi_list_values[-1])
            print(f"{timeframe} RSI  {asset_pair}: {rsi}")
            print(f"opening asset file {asset_file}")
            asset_dict = json.loads(read_asset_file())
            macd_list = asset_dict[asset_pair]["macd"] 
            rsi_list = asset_dict[asset_pair]["rsi"]
            holdings_list = asset_dict[asset_pair]["holdings"]
            price_bought_list = asset_dict[asset_pair]["price_bought"]
            avg_price_list = asset_dict[asset_pair]["avg_price_bought"]
            current_price_list = asset_dict[asset_pair]["current_price"]
            price_difference_pct_list = asset_dict[asset_pair]["price_difference_pct"]
            holdings = get_holdings()
            # In the case of selling asset manually, clear our holdings/price bought/avg price bought from the asset dict
            if asset_code in holdings.json()['result']:
                print(f"{timeframe} {asset_pair} present in holdings on kraken, checking if we actually have more than 0")
                if float(holdings.json()['result'][asset_code]) > 0:
                    print(f"{timeframe} {asset_pair} holdings: {float(holdings.json()['result'][asset_code])}, nothing to clear")
                    # Check for when holdings on Kraken matching the holdings in file. If not, set Kraken holdings to file
                    if float(holdings.json()['result'][asset_code]) == sum(holdings_list):
                        print(f"{timeframe} {asset_pair}: holdings matching the holdings on file")
                    else:
                        print(f"{timeframe} {asset_pair}: append Kraken holdings to file")
                        holdings_list.clear()
                        holdings_list.append(float(holdings.json()['result'][asset_code]))
                        asset_dict[asset_pair]["holdings"] = holdings_list
                        asset_dict[asset_pair]["price_bought"] = price_bought_list
                        asset_dict[asset_pair]["avg_price_bought"] = avg_price_list
                        asset_dict[asset_pair]["current_price"] = current_price_list
                        asset_dict[asset_pair]["price_difference_pct"] = price_difference_pct_list
                        write_to_asset_file()
                        check_create_asset_file()
                        asset_dict = json.loads(read_asset_file())
                        macd_list = asset_dict[asset_pair]["macd"] 
                        rsi_list = asset_dict[asset_pair]["rsi"]
                        holdings_list = asset_dict[asset_pair]["holdings"]
                        price_bought_list = asset_dict[asset_pair]["price_bought"]
                        avg_price_list = asset_dict[asset_pair]["avg_price_bought"]
                        current_price_list = asset_dict[asset_pair]["current_price"]
                        price_difference_pct_list = asset_dict[asset_pair]["price_difference_pct"]
                else:
                    print(f"{timeframe} {asset_pair} holdings zero on kraken, clearing price bought/avg price brought/holdings from asset dict")
                    holdings_list.clear()
                    price_bought_list.clear()
                    avg_price_list.clear()
                    current_price_list.clear()
                    current_price_list.append(float(get_asset_close()))
                    price_difference_pct_list.clear()
                    asset_dict[asset_pair]["holdings"] = holdings_list
                    asset_dict[asset_pair]["price_bought"] = price_bought_list
                    asset_dict[asset_pair]["avg_price_bought"] = avg_price_list
                    asset_dict[asset_pair]["current_price"] = current_price_list
                    asset_dict[asset_pair]["price_difference_pct"] = price_difference_pct_list
                    write_to_asset_file()
                    check_create_asset_file()
                    asset_dict = json.loads(read_asset_file())
                    macd_list = asset_dict[asset_pair]["macd"] 
                    rsi_list = asset_dict[asset_pair]["rsi"]
                    holdings_list = asset_dict[asset_pair]["holdings"]
                    price_bought_list = asset_dict[asset_pair]["price_bought"]
                    avg_price_list = asset_dict[asset_pair]["avg_price_bought"]
                    current_price_list = asset_dict[asset_pair]["current_price"]
                    price_difference_pct_list = asset_dict[asset_pair]["price_difference_pct"]
            else:
                print(f"{timeframe} {asset_pair} not present in holdings on kraken")
            if len(rsi_list) == 1:
                if rsi_list[0] < rsi_lower_boundary:
                    print(f"{timeframe} {asset_pair}: Read {rsi_list[0]} RSI in file, keeping value in list")
                    rsi = rsi_list[0]
                # elif rsi_list[0] > rsi_upper_boundary:
                #   print(f"{timeframe} {asset_pair}: Read {rsi_list[0]} RSI in file, keeping value in list")
                #   rsi = rsi_list[0]
                else:
                    print(f"{timeframe} {asset_pair}: Clearing RSI value {rsi_list[0]}")
                    rsi_list.clear()
                    rsi_list.append(rsi)
                    current_price_list.clear()
                    current_price_list.append(float(get_asset_close()))
                    asset_dict[asset_pair]["rsi"] = rsi_list
                    asset_dict[asset_pair]["current_price"] = current_price_list
                    write_to_asset_file()
                    check_create_asset_file()
                    asset_dict = json.loads(read_asset_file())
                    macd_list = asset_dict[asset_pair]["macd"] 
                    rsi_list = asset_dict[asset_pair]["rsi"]
                    holdings_list = asset_dict[asset_pair]["holdings"]
                    price_bought_list = asset_dict[asset_pair]["price_bought"]
                    avg_price_list = asset_dict[asset_pair]["avg_price_bought"]
                    current_price_list = asset_dict[asset_pair]["current_price"]
                    price_difference_pct_list = asset_dict[asset_pair]["price_difference_pct"]
            elif len(rsi_list) == 0:
                print(f"{timeframe} {asset_pair}: RSI list is empty, appending {rsi} to it")
                rsi_list.append(rsi)
                asset_dict[asset_pair]["rsi"] = rsi_list
                write_to_asset_file()
                check_create_asset_file()
                asset_dict = json.loads(read_asset_file())
                macd_list = asset_dict[asset_pair]["macd"] 
                rsi_list = asset_dict[asset_pair]["rsi"]
                holdings_list = asset_dict[asset_pair]["holdings"]
                price_bought_list = asset_dict[asset_pair]["price_bought"]
                avg_price_list = asset_dict[asset_pair]["avg_price_bought"]
                current_price_list = asset_dict[asset_pair]["current_price"]
                price_difference_pct_list = asset_dict[asset_pair]["price_difference_pct"]
            # set these vars for testing purposes
            # buy:
            # rsi = 29
            # macd_list = [1, 2]
            # order_size = 5
            # sell:
            # rsi = 66
            # macd_list = [2, 1]
            if rsi < rsi_lower_boundary and len(macd_list) < 2:
                print(f"{timeframe} {asset_pair}: RSI {rsi} and length of macd list: {len(asset_dict[asset_pair]['macd'])}")
                macd = get_macd() 
                macd_list.append(macd)
                current_price_list.clear()
                current_price_list.append(float(get_asset_close()))
                if avg_price_list:
                    price_difference_pct_list.clear()
                    price_difference_pct_value = float((float(current_price_list[0])-float(avg_price_list[0]))/float(avg_price_list[0])*100)
                    price_difference_pct_list.append(price_difference_pct_value)
                    asset_dict[asset_pair]["price_difference_pct"] = price_difference_pct_list
                asset_dict[asset_pair]["current_price"] = current_price_list
                asset_dict[asset_pair]["macd"] = macd_list
                write_to_asset_file()
                check_create_asset_file()
                asset_dict = json.loads(read_asset_file())
                macd_list = asset_dict[asset_pair]["macd"] 
                rsi_list = asset_dict[asset_pair]["rsi"]
                holdings_list = asset_dict[asset_pair]["holdings"]
                price_bought_list = asset_dict[asset_pair]["price_bought"]
                avg_price_list = asset_dict[asset_pair]["avg_price_bought"]
                current_price_list = asset_dict[asset_pair]["current_price"]
                price_difference_pct_list = asset_dict[asset_pair]["price_difference_pct"]
                print(f"{timeframe} {asset_pair}: Appended {macd} macd value to macd list")
                print(f"{timeframe} {asset_pair}: MACD list {asset_dict[asset_pair]['macd']}")
                # tg_message = f"{timeframe} {asset_pair}: RSI {rsi} and MACD list: {asset_dict[asset_pair]['macd']}"
                # send_telegram_message()
            elif rsi < rsi_lower_boundary and len(macd_list) >= 2:
                print(f"{timeframe} {asset_pair}: RSI < {rsi_lower_boundary} and macd_list >= 2")
                tg_message = f"{timeframe} {asset_pair}: RSI < {rsi_lower_boundary} and macd_list >= 2"
                send_telegram_message()
                if macd_list[-2] < macd_list[-1]:
                    print(f"{timeframe} {asset_pair}: MACD in upward trend for {len(macd_list)} iterations, buying {asset_pair}")
                    tg_message = f"{timeframe} {asset_pair}: MACD in upward trend for {len(macd_list)} iterations, buying {asset_pair}"
                    send_telegram_message()
                    asset_close = float(get_asset_close())
                    usd_order_size = order_size
                    volume_to_buy = str(float(usd_order_size / asset_close))
                    order_output = buy_asset()
                    if not order_output.json()['error']:
                        print(f"{timeframe} {asset_pair}: Bought {volume_to_buy}")
                        tg_message = order_output.json()['result']
                        send_telegram_message()        
                        macd_list.clear()
                        rsi_list.clear()
                        transaction_id = order_output.json()['result']['txid'][0]
                        order_info = get_orderinfo()
                        executed_size = order_info.json()['result'][transaction_id]['vol_exec']
                        holdings_list.append(float(executed_size))
                        price_bought_list.append(asset_close)
                        current_price_list.clear()
                        current_price_list.append(asset_close)
                        avg_price_list.clear()
                        avg_price_list.append((sum(price_bought_list)/(len(price_bought_list))))
                        price_difference_pct_list.clear()
                        price_difference_pct_value = float((float(current_price_list[0])-float(avg_price_list[0]))/float(avg_price_list[0])*100)
                        price_difference_pct_list.append(price_difference_pct_value)
                        asset_dict[asset_pair]["price_difference_pct"] = price_difference_pct_list
                        asset_dict[asset_pair]["macd"] = macd_list
                        asset_dict[asset_pair]["rsi"] = rsi_list
                        asset_dict[asset_pair]["holdings"] = holdings_list
                        asset_dict[asset_pair]["price_bought"] = price_bought_list
                        asset_dict[asset_pair]["avg_price_bought"] = avg_price_list
                        asset_dict[asset_pair]["current_price"] = current_price_list
                        write_to_asset_file()
                        check_create_asset_file()
                        asset_dict = json.loads(read_asset_file())
                        macd_list = asset_dict[asset_pair]["macd"] 
                        rsi_list = asset_dict[asset_pair]["rsi"]
                        holdings_list = asset_dict[asset_pair]["holdings"]
                        price_bought_list = asset_dict[asset_pair]["price_bought"]
                        avg_price_list = asset_dict[asset_pair]["avg_price_bought"]
                        current_price_list = asset_dict[asset_pair]["current_price"]
                        price_difference_pct_list = asset_dict[asset_pair]["price_difference_pct"]
                        print(f"{timeframe} asset_dict: {asset_dict}")
                        #avg_price_list.clear()
                        #asset_dict[asset_pair]["avg_price_bought"] = avg_price_list
                    else:
                        print(f"{timeframe} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}")
                        tg_message = f"{timeframe} {asset_pair}: An error occured when trying to place a buy order: {order_output.json()['error']}"
                        send_telegram_message()
                else: 
                    print(f"{timeframe} {asset_pair}: Not enough MACD values yet, appending one to the list")
                    macd = get_macd() 
                    macd_list.append(macd)
                    current_price_list.clear()
                    current_price_list.append(float(get_asset_close()))
                    if avg_price_list:
                        price_difference_pct_list.clear()
                        price_difference_pct_value = float((float(current_price_list[0])-float(avg_price_list[0]))/float(avg_price_list[0])*100)
                        price_difference_pct_list.append(price_difference_pct_value)
                        asset_dict[asset_pair]["price_difference_pct"] = price_difference_pct_list
                    asset_dict[asset_pair]["current_price"] = current_price_list
                    print(f"{timeframe} {asset_pair}: Appending {macd} to macd list")
                    asset_dict[asset_pair]["macd"] = macd_list
                    write_to_asset_file()
                    check_create_asset_file()
                    asset_dict = json.loads(read_asset_file())
                    macd_list = asset_dict[asset_pair]["macd"] 
                    rsi_list = asset_dict[asset_pair]["rsi"]
                    holdings_list = asset_dict[asset_pair]["holdings"]
                    price_bought_list = asset_dict[asset_pair]["price_bought"]
                    avg_price_list = asset_dict[asset_pair]["avg_price_bought"]
                    current_price_list = asset_dict[asset_pair]["current_price"]
                    price_difference_pct_list = asset_dict[asset_pair]["price_difference_pct"]
                    print(f"{timeframe} asset_dict: {asset_dict}")
            else:
                print(f"{timeframe} {asset_pair}: RSI {rsi}, nothing to do. Checking back in {loop_time_seconds} seconds")
                tg_message = f"{timeframe} {asset_pair}: RSI {rsi}, nothing to do. Checking back in {loop_time_seconds} seconds"
                send_telegram_message()
                current_price_list.clear()
                current_price_list.append(float(get_asset_close()))
                if avg_price_list:
                    price_difference_pct_list.clear()
                    price_difference_pct_value = float((float(current_price_list[0])-float(avg_price_list[0]))/float(avg_price_list[0])*100)
                    price_difference_pct_list.append(price_difference_pct_value)
                    asset_dict[asset_pair]["price_difference_pct"] = price_difference_pct_list
                asset_dict[asset_pair]["current_price"] = current_price_list
                write_to_asset_file()
            time.sleep(3) # sleep 3 seconds between asset pair
        tg_message = f"{timeframe} asset dict: {json.dumps(asset_dict, indent=2)}"
        send_telegram_message()
        time.sleep(loop_time_seconds)
elif strategy == "dca-flat":
    while True:
        for asset_pair in asset_pairs:
            order_size = min_order_size()
            try:
                buy_asset()
                print(f"DCA: bought {asset_pair}")
                tg_message = f"DCA: bought {asset_pair}"
                send_telegram_message()
            except:
                print(f"DCA: exception occured trying to buy {asset_pair}")
                tg_message = f"DCA: exception occured trying to buy {asset_pair}"
                send_telegram_message()
                raise SystemError
            print(f"{asset_pair} block done, sleeping 3 seconds")
            time.sleep(3) # sleep 3 seconds between asset pair
        print(f"DCA: sleeping for {loop_time_seconds} seconds")
        tg_message = f"DCA: sleeping for {loop_time_seconds} seconds"
        send_telegram_message()
        time.sleep(loop_time_seconds)
elif strategy == "macd-crossover":
    while True:
        sll_short_trigger_pct = 1.09 # trigger pct from current price
        sll_short_limit_pct = 1.10 # limit pct from current price
        sll_long_trigger_pct = 0.91 # trigger pct from current price
        sll_long_limit_pct = 0.90 # limit pct from current price
        for asset_pair in asset_pairs:
          leverage = get_kraken_leverage()
          asset_pair_short = get_asset_vars()[4]
          macd_hist_list = asset_dict[asset_pair]
          if len(macd_hist_list) == 0:
            print(f"{timeframe} {asset_pair}: MACD hist list length: {len(macd_hist_list)}, appending 2 MACD hist values")
            macd_hist_tmp = get_macdhist_start()
            macd_hist_list.append(macd_hist_tmp[-2])
            macd_hist_list.append(macd_hist_tmp[-1])
            asset_dict[asset_pair] = macd_hist_list
            time.sleep(1)
            print(f"{timeframe} {asset_pair}: Appended MACD hist: {macd_hist_list}")
            tg_message = f"{timeframe} {asset_pair}: Appended MACD hist: {macd_hist_list}"
            send_telegram_message()
          if len(macd_hist_list) == 1:
            print(f"{timeframe} {asset_pair}: {macd_hist_list}, appending 1 MACD hist value")
            print(f"{timeframe} {asset_pair}: MACD hist list length: {len(macd_hist_list)}, appending 1 MACD hist value")
            macd_hist_list.append(get_macdhist())
            asset_dict[asset_pair] = macd_hist_list
            time.sleep(1)
            print(f"{timeframe} {asset_pair}: Appended MACD hist: {macd_hist_list}")
            tg_message = f"{timeframe} {asset_pair}: Appended MACD hist: {macd_hist_list}"
            send_telegram_message()
          ############## for testing purposes ####################
          # macd_hist_list = [-1, 1] ######## BUY
          # macd_hist_list = [1, -1] # ######## SELL
          if macd_hist_list[-2] < 0:
            # if macd_hist_list = [< 0, y]
            print(f"{timeframe} {asset_pair}: Watching to buy asset when MACD hist crosses 0")
            if macd_hist_list[-1] < 0:
              # if macd_hist_list = [<0, <0]
              print(f"{timeframe} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing")
              macd_hist_list.pop(0)
              # macd_hist_list = [<0]
              # append macd_hist_list to asset_dict[asset_pair]
              asset_dict[asset_pair] = macd_hist_list
              tg_message = f"{timeframe} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing"
              send_telegram_message()
            elif macd_hist_list[-1] > 0:
              print(f"{timeframe} {asset_pair}: MACD hist crossed 0, closing short pos if any and opening long pos")
              tg_message = f"{timeframe} {asset_pair}: MACD hist crossed 0, closing short pos if any and opening long pos"
              send_telegram_message()
              open_orders = query_open_orders().json()['result']
              if not open_orders['open']:
                print(f"No open orders currently present")
                print(f"{timeframe} {asset_pair}: Opening los pos")
                asset_close = float(get_asset_close())
                usd_order_size = order_size
                order_volume = str(float(usd_order_size / asset_close))
                sll_trigger = str(round(float(asset_close * sll_long_trigger_pct), 1))
                sll_limit = str(round(float(asset_close * sll_long_limit_pct), 1))
                order_output = open_increase_long_pos()
                if not order_output.json()['error']:
                  print(f"{timeframe} {asset_pair}: Succesfully opened long pos: {order_output.json()}")
                  tg_message = f"{timeframe} {asset_pair} Succesfully opened long pos: {order_output.json()}"
                  send_telegram_message()
                  macd_hist_list.pop(0)
                  asset_dict[asset_pair] = macd_hist_list
                else:
                  print(f"{timeframe} {asset_pair}: Something went wrong opening a long pos: {order_output.json()}")
                  tg_message = f"{timeframe} {asset_pair} Something went wrong opening a long pos: {order_output.json()}"
                  send_telegram_message()
                  macd_hist_list.pop(0)
                  asset_dict[asset_pair] = macd_hist_list
              else:
                print(f"There are open orders")
                print(f"Checking if there are open orders for {asset_pair}")
                open_orders = query_open_orders().json()['result']
                open_order_dict = {}
                for key, value in open_orders['open'].items():
                  # key = asset pair short
                  # value = order txid
                  open_order_dict.update({value['descr']['pair']: key})
                  '''
                  open_order_keys = [asset_pair_short]
                  open_order_values = [order_txid]
                  open_order_dict = {asset_pair_short: order_txid, asset_pair_short: order_txid}
                  '''
                if asset_pair_short in open_order_dict.keys():
                  print(f"{timeframe} {asset_pair}: cancelling SLL order")
                  order_txid = open_order_dict[asset_pair_short]
                  order_output = cancel_order(order_txid)
                  if not order_output.json()['error']:
                    print(f"{timeframe} {asset_pair}: Succesfully cleared SLL order: {order_output.json()}")
                    tg_message = f"{timeframe} {asset_pair} Succesfully cleared SLL order: {order_output.json()}"
                    send_telegram_message()
                    print(f"{timeframe} {asset_pair}: Closing short pos")
                    time.sleep(5)
                    order_output = close_short_pos()
                    print(f"Result closing short pos for {asset_pair}: {order_output}")
                    if not order_output.json()['error']:
                      print(f"{timeframe} {asset_pair}: Succesfully closed short pos: {order_output.json()}")
                      tg_message = f"{timeframe} {asset_pair} Succesfully closed short pos: {order_output.json()}"
                      send_telegram_message()
                      print(f"{timeframe} {asset_pair}: Opening long pos")
                      asset_close = float(get_asset_close())
                      usd_order_size = order_size
                      order_volume = str(float(usd_order_size / asset_close))
                      sll_trigger = str(round(float(asset_close * sll_long_trigger_pct), 1))
                      sll_limit = str(round(float(asset_close * sll_long_limit_pct), 1))
                      order_output = open_increase_long_pos()
                      if not order_output.json()['error']:
                        print(f"{timeframe} {asset_pair}: Succesfully opened long pos: {order_output.json()}")
                        tg_message = f"{timeframe} {asset_pair} Succesfully opened long pos: {order_output.json()}"
                        send_telegram_message()
                        macd_hist_list.pop(0)
                        asset_dict[asset_pair] = macd_hist_list
                      else:
                        print(f"{timeframe} {asset_pair}: Something went wrong opening a long pos: {order_output.json()}")
                        tg_message = f"{timeframe} {asset_pair} Something went wrong opening a long pos: {order_output.json()}"
                        send_telegram_message()
                        macd_hist_list.pop(0)
                        asset_dict[asset_pair] = macd_hist_list
                    else:
                      print(f"{timeframe} {asset_pair}: Something went wrong closing short pos: {order_output.json()}")
                      tg_message = f"{timeframe} {asset_pair} Something went wrong closing short pos: {order_output.json()}"
                      send_telegram_message()
                      macd_hist_list.pop(0)
                      asset_dict[asset_pair] = macd_hist_list
                  else:
                    print(f"{timeframe} {asset_pair}: Something went wrong cancelling SLL order: {order_output.json()}")
                    tg_message = f"{timeframe} {asset_pair} Something went wrong cancelling SLL order: {order_output.json()}"
                    send_telegram_message()
                    macd_hist_list.pop(0)
                    asset_dict[asset_pair] = macd_hist_list
                else:
                  print(f"{timeframe} {asset_pair} not present in orders, opening long pos")
                  asset_close = float(get_asset_close())
                  usd_order_size = order_size
                  order_volume = str(float(usd_order_size / asset_close))
                  sll_trigger = str(round(float(asset_close * sll_long_trigger_pct), 1))
                  sll_limit = str(round(float(asset_close * sll_long_limit_pct), 1))
                  order_output = open_increase_long_pos()
                  if not order_output.json()['error']:
                    print(f"{timeframe} {asset_pair}: Succesfully opened long pos: {order_output.json()}")
                    tg_message = f"{timeframe} {asset_pair} Succesfully opened long pos: {order_output.json()}"
                    send_telegram_message()
                    macd_hist_list.pop(0)
                    asset_dict[asset_pair] = macd_hist_list
                  else:
                    print(f"{timeframe} {asset_pair}: Someting went wrong opening a long pos: {order_output.json()}")
                    tg_message = f"{timeframe} {asset_pair} Something went wrong opening a long pos: {order_output.json()}"
                    send_telegram_message()
                    macd_hist_list.pop(0)
                    asset_dict[asset_pair] = macd_hist_list
          elif macd_hist_list[-2] > 0:
            print(f"{timeframe} {asset_pair}: Watching to sell asset when MACD hist crosses 0 and opening a short position")
            if macd_hist_list[-1] > 0:
              print(f"{timeframe} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing")
              macd_hist_list.pop(0)
              asset_dict[asset_pair] = macd_hist_list
              tg_message = f"{timeframe} {asset_pair}: MACD hist did not cross 0, clearing first element (oldest) in MACD hist list and continuing"
              send_telegram_message()
            elif macd_hist_list[-1] < 0:
              print(f"{timeframe} {asset_pair}: MACD hist crossed 0, closing long pos if any and opening short pos")
              tg_message = f"{timeframe} {asset_pair}: MACD hist crossed 0, closing long pos if any and opening short pos"
              send_telegram_message()
              open_orders = query_open_orders().json()['result']
              if not open_orders['open']:
                print(f"No open orders currently present")
                print(f"{timeframe} {asset_pair}: Opening short pos")
                asset_close = float(get_asset_close())
                usd_order_size = order_size
                order_volume = str(float(usd_order_size / asset_close))
                sll_trigger = str(round(float(asset_close * sll_short_trigger_pct), 1))
                sll_limit = str(round(float(asset_close * sll_short_limit_pct), 1))
                order_output = open_increase_short_pos()
                if not order_output.json()['error']:
                  print(f"{timeframe} {asset_pair}: Succesfully opened short pos: {order_output.json()}")
                  tg_message = f"{timeframe} {asset_pair} Succesfully opened short pos: {order_output.json()}"
                  send_telegram_message()
                  macd_hist_list.pop(0)
                  asset_dict[asset_pair] = macd_hist_list
                else:
                  print(f"{timeframe} {asset_pair}: Something went wrong opening a short pos: {order_output.json()}")
                  tg_message = f"{timeframe} {asset_pair} Something went wrong opening a short pos: {order_output.json()}"
                  send_telegram_message()
                  macd_hist_list.pop(0)
                  asset_dict[asset_pair] = macd_hist_list
              else:
                print(f"There are open orders")
                print(f"Checking if there are open orders for {asset_pair}")
                open_orders = query_open_orders().json()['result']
                open_order_dict = {}
                for key, value in open_orders['open'].items():
                  # key = asset pair short
                  # value = order txid
                  open_order_dict.update({value['descr']['pair']: key})
                  '''
                  open_order_keys = [asset_pair_short]
                  open_order_values = [order_txid]
                  open_order_dict = {asset_pair_short: order_txid, asset_pair_short: order_txid}
                  '''
                if asset_pair_short in open_order_dict.keys():
                  print(f"{timeframe} {asset_pair}: cancelling SLL order")
                  order_txid = open_order_dict[asset_pair_short]
                  order_output = cancel_order(order_txid)
                  if not order_output.json()['error']:
                    print(f"{timeframe} {asset_pair}: Succesfully cleared SLL order: {order_output.json()}")
                    tg_message = f"{timeframe} {asset_pair} Succesfully cleared SLL order: {order_output.json()}"
                    send_telegram_message()
                    time.sleep(5)
                    print(f"{timeframe} {asset_pair}: Closing long pos")
                    order_output = close_long_pos()
                    print(f"Result closing long pos for {asset_pair}: {order_output}")
                    if not order_output.json()['error']:
                      print(f"{timeframe} {asset_pair}: Succesfully closed long pos: {order_output.json()}")
                      tg_message = f"{timeframe} {asset_pair} Succesfully closed long pos: {order_output.json()}"
                      send_telegram_message()
                      print(f"{timeframe} {asset_pair}: Opening short pos")
                      asset_close = float(get_asset_close())
                      usd_order_size = order_size
                      order_volume = str(float(usd_order_size / asset_close))
                      sll_trigger = str(round(float(asset_close * sll_short_trigger_pct), 1))
                      sll_limit = str(round(float(asset_close * sll_short_limit_pct), 1))
                      order_output = open_increase_short_pos()
                      if not order_output.json()['error']:
                        print(f"{timeframe} {asset_pair}: Succesfully opened short pos: {order_output.json()}")
                        tg_message = f"{timeframe} {asset_pair} Succesfully opened short pos: {order_output.json()}"
                        send_telegram_message()
                        macd_hist_list.pop(0)
                        asset_dict[asset_pair] = macd_hist_list
                      else:
                        print(f"{timeframe} {asset_pair}: Something went wrong opening a short pos: {order_output.json()}")
                        tg_message = f"{timeframe} {asset_pair} Something went wrong opening a short pos: {order_output.json()}"
                        send_telegram_message()
                        macd_hist_list.pop(0)
                        asset_dict[asset_pair] = macd_hist_list
                    else:
                      print(f"{timeframe} {asset_pair}: Something went wrong closing long pos: {order_output.json()}")
                      tg_message = f"{timeframe} {asset_pair} Something went wrong closing long pos: {order_output.json()}"
                      send_telegram_message()
                      macd_hist_list.pop(0)
                      asset_dict[asset_pair] = macd_hist_list
                  else:
                    print(f"{timeframe} {asset_pair}: Something went wrong cancelling SLL order: {order_output.json()}")
                    tg_message = f"{timeframe} {asset_pair} Something went wrong cancelling SLL order: {order_output.json()}"
                    send_telegram_message()
                    macd_hist_list.pop(0)
                    asset_dict[asset_pair] = macd_hist_list
                else:
                  print(f"{timeframe} {asset_pair} not present in orders, opening short pos")
                  asset_close = float(get_asset_close())
                  usd_order_size = order_size
                  order_volume = str(float(usd_order_size / asset_close))
                  sll_trigger = str(round(float(asset_close * sll_short_trigger_pct), 1))
                  sll_limit = str(round(float(asset_close * sll_short_limit_pct), 1))
                  order_output = open_increase_short_pos()
                  if not order_output.json()['error']:
                    print(f"{timeframe} {asset_pair}: Succesfully opened short pos: {order_output.json()}")
                    tg_message = f"{timeframe} {asset_pair} Succesfully opened short pos: {order_output.json()}"
                    send_telegram_message()
                    macd_hist_list.pop(0)
                    asset_dict[asset_pair] = macd_hist_list
                  else:
                    print(f"{timeframe} {asset_pair}: Someting went wrong opening a short pos: {order_output.json()}")
                    tg_message = f"{timeframe} {asset_pair} Something went wrong opening a short pos: {order_output.json()}"
                    send_telegram_message()
                    macd_hist_list.pop(0)
                    asset_dict[asset_pair] = macd_hist_list
          print(f"{asset_pair} block done, sleeping 3 seconds")
          time.sleep(3) # sleep 3 seconds between asset pair
        print(f"Done with all assets, sleeping for {loop_time_seconds} seconds")
        time.sleep(loop_time_seconds)