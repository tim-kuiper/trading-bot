message = "\n What is your age?"
age = int(input(message))

while age < 3:
    print(f"Because you are under {age} years old, the movie is free of charge.")
    break

while age >= 3 and age <= 12:
    print(f"Because you are {age} years old, you have to pay $10 to watch the movie.")
    break

while age > 12:
    print(f"Because you are over {age} years old, you have to pay $15 to watch the movie.")
    break
