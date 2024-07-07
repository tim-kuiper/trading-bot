import pymongo

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
print(f"step 1")

mydb = myclient["mydatabase"]

print(f"step 2")

dblist = myclient.list_database_names()
if "mydatabase" in dblist:
  print("The database exists.")

print(f"{myclient.list_database_names()}")
print(f"step 3")
