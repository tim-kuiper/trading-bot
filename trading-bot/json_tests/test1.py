import json

# a Python object (list):
x = ['test1', 'test2']

# convert into JSON:
y = json.dumps(x, indent=4)

# dump to file
with open('data.json', 'w') as f:
    f.write(y)

# read from file
file = open('data.json', 'r')
contents = file.read()

print(contents)

# convert to python data
data = json.loads(contents)
print(data)

# append to python data 
data.append("test3")
print(data)

# convert to JSON again
z = json.dumps(data, indent=4)

# dump to file again
with open('data.json', 'w') as f:
    f.write(z)
