# 7-2
dining_group_size = input("How many people are in your dining group?")
print(dining_group_size)
dining_group_size = int(dining_group_size)

if dining_group_size > 8:
    print("Please wait for a table")
else:
    print("The table is ready")

