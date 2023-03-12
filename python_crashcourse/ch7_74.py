prompt = "\nPlease enter your pizza topping:"
prompt += "\n(Enter 'quit' when you are finished.)"

while True:
    pizza_topping = input(prompt)
    if pizza_topping == 'quit':
        break
    else:
        print(f"Adding topping {pizza_topping} to the pizza")