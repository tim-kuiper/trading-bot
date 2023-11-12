import requests
import json

rsi45_balance = 11
asset_pair = 'XBTUSDT'

# Get asset pair XBT/USDT (XBT is BTC)
payload = {'pair': asset_pair}
# asset_pair = requests.get('https://api.kraken.com/0/public/Ticker?pair=XBTUSDT')
request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
print(request.json())
ask_value = request.json()['result'][asset_pair]['a'][0]
print(ask_value)
current_btc_value = int(float(ask_value))
print(current_btc_value)
calc = str(rsi45_balance / current_btc_value)
print(calc)

print("Amount of BTC we need to buy:", calc)

if request.json()['error'] != []:
  print("No errors found!")
