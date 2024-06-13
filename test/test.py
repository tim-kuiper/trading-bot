import time

list_24h = []

while True:
  list_24h.append(24)
  if len(list_24h) == 6:
    print("list_24 block")
    list_24h.clear()
  time.sleep(1)
