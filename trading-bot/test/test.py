import time

while True:
  print("outer loop")
  time.sleep(1)
  while True:
    print("inner loop")
    time.sleep(1)
