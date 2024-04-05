#!/bin/bash

for file in $(ls | grep .py); do
  screen -L -Logfile $file.txt -d -m -S $file python $file && echo "screen $file launched"
  sleep 10
done
