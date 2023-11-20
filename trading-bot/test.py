from pathlib import Path

my_file = Path("/home/str1der/python/trading-bot/testfile")
if my_file.is_file():
  print("File exists!")
