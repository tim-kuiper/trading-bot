#!/bin/bash

mkdir screen_logs
for file in $(ls | grep .py); do
  screen -L -Logfile screen_logs/$file.txt -d -m -S $file python $file && echo "screen $file launched"
  sleep 10
done
