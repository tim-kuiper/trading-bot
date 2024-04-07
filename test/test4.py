import time

assets = [1, 2, 3, 4, 5]
list_1h = []
list_4h = []
list_24h = []
#main loop
while True:
  list_1h.append(1)
  list_4h.append(4)
  list_24h.append(24)
  print(f"1H list length: {len(list_1h)}")
  print(f"4H list length: {len(list_4h)}")
  print(f"24H list length: {len(list_24h)}")
  if len(list_1h) == 1:
    # loop over assets
    for asset in assets:
      print(f"Looping over 1h assets")
      time.sleep(1)
    list_1h.clear()
  if len(list_4h) == 4:
    # loop over assets
    for asset in assets:
      print(f"Looping over 4h assets")
      time.sleep(1)
    list_4h.clear()
  if len(list_24h) == 24:
    # loop over assets
    for asset in assets:
      print(f"Looping over 24h assets")
      time.sleep(1)
    list_24h.clear()
  time.sleep(3)
