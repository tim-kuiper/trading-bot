#!/bin/bash

for file in $(ls | grep .py); do
  screen -d -m -S $file python $file && echo "screen $file launched"
  sleep 10
done
