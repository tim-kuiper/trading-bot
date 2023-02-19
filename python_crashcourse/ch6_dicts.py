# Dictionaries

# 6-1
kameraad = {
    'first_name': 'Thijs',
    'last_name': 'Hemelt',
    'age': 30,
    'city': 'Enschede'
}

print(kameraad['first_name'])
print(kameraad['last_name'])
print(kameraad['age'])
print(kameraad['city'])

# 6-2
mensen = {
    'jantje': 2,
    'pietje': 4,
    'klaasje': 6,
    'berta': 7,
    'oscar': 13
}

for k,v in mensen.items():
    print(f"{k}" ":" f"{v}")

# 6-5
rivers = {
    'nile': 'egypt',
    'amazon': 'brazil',
    'rijn': 'netherlands'
}

for k, v  in rivers.items():
    print(f"The {k.title()} runs through {v.title()}")

for name in rivers.keys():
    print(name.title())

for country in rivers.values():
    print(country.title())

# 6-6
favorite_languages = {
'jen': 'python',
'sarah': 'c',
'edward': 'ruby',
'phil': 'python',
}

people_list = ['jen', 'edward', 'tim', 'paul']

for person in favorite_languages.keys():
    if person in people_list:
        print(f"Thanks {person.title()} for responding")
    else:
        print(f"{person.title()}, please fill in the poll.")

# 6-7
kameraad_1 = {
    'first_name': 'Thijs',
    'last_name': 'Hemelt',
    'age': 30,
    'city': 'Enschede'
}

kameraad_2 = {
    'first_name': 'Niek',
    'last_name': 'Siero',
    'age': 29,
    'city': 'Losser'
}

kameraad_3 = {
    'first_name': 'Floris',
    'last_name': 'Tattersall',
    'age': 31,
    'city': 'Mettingen'
}

people = [kameraad_1, kameraad_2, kameraad_3]

for person in people:
    for k, v in person.items():
        print(f"{k.title()} : {v}")

# 6-8
# same as 6-7

# 6-9
favorite_places = {
    'thijs': 'enschede',
    'niek': 'losser',
    'floris': 'mettingen'
}

for k,v in favorite_places.items():
    print(f"{k.title()} favorite place is {v.title()}")

# 6-10
mensen = {
    'jantje': [2, 3],
    'pietje': [4, 5],
    'klaasje': [8, 19],
    'berta': [7, 9],
    'oscar': [13, 6]
}

for k,v in mensen.items():
    print(f"{k.title()}'s favorite numbers are {v}")

# 6-11
cities = {
    'enschede': {
        'country': 'netherlands',
        'population': 170000,
        'fact': 'grootste stad van overijssel'
    },
    'wijhe': {
        'country': 'netherlands',
        'population': 60000,
        'fact': 'stad aan de ijssel'
    },
    'zwolle': {
        'country': 'netherlands',
        'population': 150000,
        'fact': 'hoofdstad van overijssel'
    }
}

for k,v in cities.items():
    stad = f"{k.title()}"
    land = f"{v['country'].title()}"
    inwoners = f"{v['population']}"
    feit = f"{v['fact'].title()}"
    print(stad,"\n",land,"\n",inwoners,"\n",feit)