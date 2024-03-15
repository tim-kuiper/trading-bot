#!/bin/bash

screen -d -m -S sol python main_sol.py
sleep 10
screen -d -m -S ada python main_ada.py
sleep 10
screen -d -m -S btc python main_btc.py
sleep 10
screen -d -m -S xrp python main_xrp.py
sleep 10
screen -d -m -S matic python main_matic.py
sleep 10
screen -d -m -S eth python main_eth.py
sleep 10
screen -d -m -S avax python main_avax.py
