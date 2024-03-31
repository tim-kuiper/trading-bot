import json
import random
import os
import time

'''
- Buy RSI < 35 and MACD upwards trend 3 iterations
- Sell RSI > 65 and MACD downwards trend 3 iterations

Flow:
- Create dict to store asset_pair dict with rsi list, macd list and holdings list
- If RSI 35> and <65, dont do anything
- If RSI < 35, append value to asset_pair rsi and append macd value to asset_pair macd. At next iteration:
  - Keep RSI < 35 value in rsi list
  - Append MACD value to macd list
  - Keep appending MACD value to macd list
  - If MACD list values from asset_pair is in an upward trend for 3 iterations, buy asset append bought amount to asset_pair holding list. Clear asset_pair rsi and macd list
- If RSI > 65, append value to asset_pair rsi and append macd value to asset_pair macd. At next iteration:
  - Keep RSI > 65 value in rsi list
  - Append MACD value to macd list
  - Keep appending MACD value to macd list
  - If MACD list values from asset_pair is in an downwards trend for 3 iterations, sell asset and clear asset_pair holding, rsi and macd list

'''
# my_dict = {"asset1": {"rsi": 37, "macd": [1, 2, 3]}, "asset2": {"rsi": 40, "macd": [2, 3, 1]}}
asset_dict = {}
timeframe = "1h"
file_extension = '.json'
asset_file = timeframe + file_extension 
asset_file_path = './' + asset_file
asset_pairs = ['XXBTZUSD', 'XXRPZUSD', 'ADAUSD', 'SOLUSD', 'AVAXUSD', 'MATICUSD', 'XETHZUSD']

# for loop for instantiating asset_dict 
for asset_pair in asset_pairs:
  asset_file_exists = os.path.exists(asset_file_path)
  # create file if it doesnt exist, add dictionary per asset to it
  if not asset_file_exists:
    print(f"Asset file {asset_file} doesnt exist , creating one")
    f = open(asset_file, "w")
    asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": []}})
    f.write(json.dumps(asset_dict))
    f.close()
  else:
    print(f"Asset file {asset_file} exists, reading")
    f = open(asset_file, "r")
    asset_json = f.read()
    f.close()
    asset_dict = json.loads(asset_json)
    if asset_pair not in asset_dict.keys():
      print(f"Asset pair {asset_pair} not present in asset file {asset_file}, updating file")
      asset_dict.update({asset_pair: {"rsi": [], "macd": [], "holdings": []}})
      f = open(asset_file, "w")
      f.write(json.dumps(asset_dict))
      f.close()
      print(f"Appended {asset_pair} to {asset_file}")

while True:
  # main for loop for hourly loop
  for asset_pair in asset_pairs:
    # set asset code since Kraken asset codes are not consistent
    if asset_pair == "XXBTZUSD":
      asset_code = "XXBT"
    if asset_pair == "XXRPZUSD":
      asset_code = "XXRP"
    if asset_pair == "ADAUSD":
      asset_code = "ADA"
    if asset_pair == "SOLUSD":
      asset_code = "SOL"
    if asset_pair == "AVAXUSD":
       asset_code = "AVAX"
    if asset_pair == "MATICUSD":
      asset_code = "MATIC"
    if asset_pair == "XETHZUSD":
      asset_code = "XETH"
  
    # open asset_dict, check for existing rsi value
    # if existing rsi value exists, its 
    print(f"opening asset file {asset_file}")
    f = open(asset_file, "r")
    asset_json = f.read()
    f.close()
    asset_dict = json.loads(asset_json)
    macd_list = asset_dict[asset_pair]["macd"] 
    rsi_list = asset_dict[asset_pair]["rsi"]
    holdings_list = asset_dict[asset_pair]["holdings"]
    if not rsi_list:
      print(f"rsi list for  {asset_pair} empty, appending new rsi entry")
      # asset_pair rsi list empty, calculating rsi/macd and appending to list
      rsi = random.randint(1,100)
      macd = random.randint(1,100)
      rsi_list.append(rsi)
      macd_list.append(macd)
      asset_dict[asset_pair]["rsi"] = rsi_list
      asset_dict[asset_pair]["macd"] = macd_list
      f = open(asset_file, "w")
      f.write(json.dumps(asset_dict))
      f.close()
      print(f"appended rsi value {rsi} for {asset_pair} to rsi list")
    else:
      # asset_pair has rsi, reading rsi value and macd list
      print(f"rsi list for {asset_pair} not empty, reading value")
      rsi = rsi_list[0]
      print(f"read rsi {rsi} value")
      if rsi < 35 and len(macd_list) <= 3:
        print(f"rsi < 35 and macd_list < 3 for {asset_pair}")
        # append macd value to macd list
        macd = random.randint(1,100)
        macd_list.append(macd)
        asset_dict[asset_pair]["macd"] = macd_list
        # write to asset_file
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
        print(f"appended {macd} macd_value to macd list for {asset_pair}")
      elif rsi < 35 and len(macd_list) >= 3:
        print(f"rsi < 35 and macd_list > 3 for {asset_pair}")
        if macd_list[-3] < macd_list[-2] < macd_list[-1]:
          # buy asset
          buy_asset = True
          print(f"Buying {asset_pair}")
          if buy_asset:
            buy_amount = random.randint(1,100)
            # clear rsi/macd lists from asset_dict
            macd_list.clear()
            rsi_list.clear()
            holdings_list.append(buy_amount)
            asset_dict[asset_pair]["macd"] = macd_list
            asset_dict[asset_pair]["rsi"] = rsi_list
            asset_dict[asset_pair]["holdings"] = holdings_list
            f = open(asset_file, "w")
            f.write(json.dumps(asset_dict))
            f.close()
        else: 
          # append macd value to macd list
          macd = random.randint(1,100)
          macd_list.append(macd)
          asset_dict[asset_pair]["macd"] = macd_list
          # write to asset_file
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
      elif rsi > 65 and len(macd_list) <= 3:
        # append macd value to macd list
        macd = random.randint(1,100)
        macd_list.append(macd)
        asset_dict[asset_pair]["macd"] = macd_list
        # write to asset_file
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
      elif rsi > 65 and len(macd_list) >= 3:
        if macd_list[-3] > macd_list[-2] > macd_list[-1]:
          # sell asset
          sell_asset = True
          print(f"Selling {asset_pair}")
          if sell_asset:
            # clear rsi/macd/holdings lists from asset_dict
            macd_list.clear()
            rsi_list.clear()
            holdings_list.clear()
            asset_dict[asset_pair]["macd"] = macd_list
            asset_dict[asset_pair]["rsi"] = rsi_list
            asset_dict[asset_pair]["holdings"] = holdings_list
            f = open(asset_file, "w")
            f.write(json.dumps(asset_dict))
            f.close()
        else: 
          # append macd value to macd list
          macd = random.randint(1,100)
          macd_list.append(macd)
          asset_dict[asset_pair]["macd"] = macd_list
          # write to asset_file
          f = open(asset_file, "w")
          f.write(json.dumps(asset_dict))
          f.close()
      else:
        print(f"rsi value read from file is {rsi}, calculating new rsi value and adding it to file")
        rsi = random.randint(1,100)
        rsi_list.clear()
        rsi_list.append(rsi)
        asset_dict[asset_pair]["rsi"] = rsi_list
        f = open(asset_file, "w")
        f.write(json.dumps(asset_dict))
        f.close()
    #time.sleep(1) 
