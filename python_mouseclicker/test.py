import pyautogui
import re

z = 15

z % 5

duration_seconds = 0.1
x_center_coords = 960
y_center_coords = 540

pyautogui.moveTo(x_center_coords, y_center_coords, duration = duration_seconds) # move to center
current_pos = pyautogui.position() # get current pos
pyautogui.click(current_pos.x, current_pos.y, clicks=1, duration=0.5) # click 1

pyautogui.hotkey("F1")

def move_to(x,y,d):
    pyautogui.moveTo(x, y, duration = d) # move to center

center = move_to(960,540,0.1)
east = 

