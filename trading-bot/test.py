import json
data = "this is some string"
with open("data_file.json", "w") as write_file:
    json.dump(data, write_file)
