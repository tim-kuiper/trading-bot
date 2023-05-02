sandwich_orders = ['hamkaas', 'gezond', 'filet', 'tonijn', 'pastrami', 'pastrami', 'pastrami']
finished_sandwiches = []

if 'pastrami' in sandwich_orders:
    print("We have run out of pastrami, sorry")

while 'pastrami' in sandwich_orders:
    sandwich_orders.remove('pastrami')

while sandwich_orders:
    current_sandwich = sandwich_orders.pop()
    print(f"\nMaking {current_sandwich} sandwich....")
    finished_sandwiches.append(current_sandwich)

# Print sandwiches that are finished
print("\nThe following sandwiches have been made:")
for finished_sandwich in finished_sandwiches:
    print(f"Sandwich {finished_sandwich} has been made.")