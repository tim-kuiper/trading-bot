import requests
import json

usdt = 11

# Get asset pair XBT/USDT (XBT is BTC)
asset_pair = requests.get('https://api.kraken.com/0/public/Ticker?pair=XBTUSDT')
asset_pair_json = asset_pair.json()
print(asset_pair.json()['result']['XBTUSDT']['a'][0])

current_btc_value = float(asset_pair.json()['result']['XBTUSDT']['a'][0])
btc_value = int(current_btc_value)
print(btc_value)

calc = str(usdt / btc_value)
print(calc)

print(type(calc))
