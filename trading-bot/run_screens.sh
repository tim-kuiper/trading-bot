#!/bin/bash

for file in $(ls | grep .py); do
  screen -d -m -S $file python $file
  sleep 10
done
