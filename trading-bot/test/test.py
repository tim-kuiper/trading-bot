# get ticket info

import requests
import json

asset_pair = 'XBTUSDT'
payload = {'pair': asset_pair}

request = requests.get('https://api.kraken.com/0/public/Ticker', params=payload)
print(request.json()['result'])
