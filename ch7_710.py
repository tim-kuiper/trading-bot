vacation_destinations = []

polling_active = True

while polling_active:
    vacation_destination = input("if you could visit one place in the world, where would you go?")
    vacation_destinations.append(vacation_destination)

    repeat = input("Would you like to specify another destination? (yes / no)")
    if repeat == 'no':
        polling_active = False
print("\n--- Poll Results ---")
for vacation_destination in vacation_destinations:
    print(f"You chose {vacation_destination}")

