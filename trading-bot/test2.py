import time
from statistics import mean
import random

list = []
while True:
  time.sleep(1)
  random_number = random.randint(0, 9)
  list.append(random_number)
  print(list)
  list_avg = mean(list)
  print(list_avg)
