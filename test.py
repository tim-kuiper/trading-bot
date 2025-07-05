import requests

#output = requests.get(url="https://api.kraken.com/0/public/AssetPairs")
#print(output.json()['result']['XXBTZUSD'])

asset_pair = "XXBTZUSD"

def get_asset_pair_short(asset_pair):
    """Get asset pair short or altname, see https://docs.kraken.com/api/docs/rest-api/get-asset-info
       TODO: use asset_pair as function arg and dynamically get asset pair short code from Kraken API 
    """
    output = requests.get(url="https://api.kraken.com/0/public/AssetPairs")
    asset_pair_short = output.json()['result'][asset_pair]['altname']
    return asset_pair_short

print(f"{get_asset_pair_short(asset_pair)}")