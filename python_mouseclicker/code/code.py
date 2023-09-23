# mouse clicker using screen coordinates

import pyautogui
import time
import random

#print(pyautogui.size())


# print(pyautogui.position())

# time.sleep()

# while True:

def move_to(x,y,d):
    pyautogui.moveTo(x, y, duration = d)

def move_rel(x,y,d):
    pyautogui.moveRel(x, y, duration = d)

list = [1, 2, 3, 4, 4]
for z in range(1000000000):
    move_to(960,540,0.1) # go to center
    random_element = random.choice(list) # pick random element from list

    if random_element == 1:
        move_rel(50,0,0.1) # go right
        current_pos = pyautogui.position() # get current pos
        pyautogui.keyDown('ctrlleft')
        pyautogui.click(current_pos.x, current_pos.y, clicks=1, duration=0.25) # click
        pyautogui.keyUp('ctrlleft')
    elif random_element == 2:
        move_rel(0,50,0.1) # go down
        current_pos = pyautogui.position() # get current pos
        pyautogui.click(current_pos.x, current_pos.y, clicks=1, duration=0.25) # click
    elif random_element == 3:
        move_rel(-50,0,0.1) # go left
        current_pos = pyautogui.position() # get current pos
        pyautogui.click(current_pos.x, current_pos.y, clicks=1, duration=0.25) # click
    elif random_element == 4:
        move_rel(0,-50,0.1) # go up
        current_pos = pyautogui.position() # get current pos
        pyautogui.click(current_pos.x, current_pos.y, clicks=1, duration=0.25) # click
    # every 1000 iterations press f1
    if z % 1000 == 0:
        pyautogui.hotkey("F1")