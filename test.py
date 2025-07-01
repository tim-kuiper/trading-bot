import requests

output = requests.get(url="https://api.kraken.com/0/public/AssetPairs")

print(output.json()['result']['MINAUSD'])