import random
import time

while True:
  # calc rsi
  rsi = random.randint(0,100)
  if rsi < 35:
    macd_list = []
    while True:
      print(macd_list)
      # calc macd
      macd = random.randint(-500,500)
      macd_list.append(macd)
      if len(macd_list) < 2:
        # calc macd
        macd = random.randint(-500,500)
        macd_list.append(macd)
        continue
        print(macd_list)
      if macd_list[-1] > macd_list[-2]:
        # buy asset
        print("Buying asset")
        print("Clearing list")
        macd_list.clear()
        break
      time.sleep(1)
  elif rsi > 69:
    macd_list = []
    while True:
      print(macd_list)
      # calc macd
      macd = random.randint(-500,500)
      macd_list.append(macd)
      if len(macd_list) < 2:
        # calc macd
        macd = random.randint(-500,500)
        macd_list.append(macd)
        continue
        print(macd_list)
      if macd_list[-1] < macd_list[-2]:
        # buy asset
        print("Selling asset")
        print("Clearing list")
        macd_list.clear()
        break
      time.sleep(1)
  else:
    print("Nothing to do")
    time.sleep(1)
