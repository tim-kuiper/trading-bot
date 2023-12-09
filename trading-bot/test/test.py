# get all asset pairs

import requests
import json
import time

asset_pair = 'XBTUSDT'
payload = {'pair': asset_pair, 'interval': 60}

req = requests.get('https://api.kraken.com/0/public/OHLC', params=payload)
print(req.json())
