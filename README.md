# Python trading bot trading timeframes 1H, 4H and 1D. 

- Buy RSI < 35 and MACD upwards trend 3 iterations
- Sell RSI > 65 and MACD downwards trend 3 iterations

Flow:
- Create dict to store asset_pair dict with rsi list, macd list and holdings list
- If RSI 35> and <65, dont do anything
- If RSI < 35, append value to asset_pair rsi and append macd value to asset_pair macd. At next iteration:
  - Keep RSI < 35 value in rsi list
  - Append MACD value to macd list
  - Keep appending MACD value to macd list
  - If MACD list values from asset_pair is in an upward trend for 3 iterations, buy asset append bought amount to asset_pair holding list. Clear asset_pair rsi and macd list
- If RSI > 65, append value to asset_pair rsi and append macd value to asset_pair macd. At next iteration:
  - Keep RSI > 65 value in rsi list
  - Append MACD value to macd list
  - Keep appending MACD value to macd list
  - If MACD list values from asset_pair is in an downwards trend for 3 iterations, sell asset and clear asset_pair holding, rsi and macd list


Todo: 
- Merge timeframes into  1 python program
- 
