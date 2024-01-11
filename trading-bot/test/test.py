var = {'error': [], 'result': {'txid': ['OEAC7P-VMLSM-PVMWTP'], 'descr': {'order': 'sell 1.50000000 DOTUSD @ market'}}}

print(var['error'])

if not var['error']:
  print("im empty!")
else:
  print("im not empty!")
