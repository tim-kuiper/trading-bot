# get all asset pairs

import requests
import json
import time
from pathlib import Path


#while True:
# asset_pairs = ['XBTUSDT', 'ETHUSDT', 'XRPUSDT', 'ADAUSDT', 'SOLUSDT']
#for asset_pair in asset_pairs:
#  print("bla", asset_pair, ":")

asset_pair = 'XBTUSDT'
file = asset_pair + "_bought.json"

# if Path(file).exists():
if file.exists():
  print("file exists")
else:
  print("file doesnt exist")
