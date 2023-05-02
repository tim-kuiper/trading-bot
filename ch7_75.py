while True:
  prompt = "\n What is your age?"
  age = int(input(prompt))
  if age <= 3:
    print("Your ticket will be free!")
    break
  elif age >= 3 and age <= 12:
    print("The ticket costs $10")
    break
  elif age >= 12:
    print("The ticket costs 15$")
    break