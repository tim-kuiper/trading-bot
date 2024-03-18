import json
import os

asset = 'btc'
asset_file = 'asset_file.json'
asset_list = []
file_extension = '.json'
asset_code = 'XXBT'

asset_file = asset_code.lower() + file_extension
asset_file_path = './' + asset_file
print(asset_file)
print(asset_file_path)

# define empty python
# buy asset
# check if file exist
# if file exists, read from file/convert to python list / append to python list / convert to json / write to file
# if file doesnt exist, create file / 
# convert json to python list
# append bought volume to python list
# convert python list to json 
# write json to file
# close file

# sell asset
# after selling, remove asset file


# check if file exists
file_exists = os.path.exists(asset_file_path)

# if file doesnt exist, create it
if not file_exists:
  print(f"{asset_file} doesnt exist yet, creating a new one")
  f = open(asset_file, "w")
  asset_list.append(3)
  f.write(json.dumps(asset_list))
  f.close
else:
  print(f"{asset_file} already exists, reading from file and appending element")
  f = open(asset_file, "r")
  data_json = f.read()
  f.close
  asset_list = json.loads(data_json)
  asset_list.append(3)
  f = open(asset_file, "w")
  f.write(json.dumps(asset_list))
  f.close
  
  
  

