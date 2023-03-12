# Ex 7-5 variance
message = "\n What is your age?"
message += "\n Enter 'quit' to exit the program."

active = True
while active:
    input = input(message)
    if input == 'quit':
        break
    elif int(input) < 3:
        print(f"Because you are under {input} years old, the movie is free of charge.")
        break
    elif int(input) >= 3 and int(input) <= 12:
        print(f"Because you are {input} years old, you have to pay $10 to watch the movie.")
        break
    elif int(input) > 12:
        print(f"Because you are over {input} years old, you have to pay $15 to watch the movie.")
        break
