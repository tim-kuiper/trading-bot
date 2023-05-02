prompt = "\nPlease enter a pizza topping:"
prompt += "\n(Enter 'quit' when you are finished.) "

pizza = []
while True:
  pizza_topping = input(prompt)
  if pizza_topping == 'quit':
    break
  else:
    print(f"Adding {pizza_topping.title()} to the pizza!")
    pizza.append(pizza_topping)

print("Your pizza consists of the following toppings:\n")
for i in pizza:
  print(i)