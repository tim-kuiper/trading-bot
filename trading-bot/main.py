# Trade BTC/USDT, mainly with DCA strategy in mind.

import time
import os
import requests
import urllib
import hashlib
import hmac
import base64

# Set Nonce: https://support.kraken.com/hc/en-us/articles/360000906023-What-is-a-nonce-
api_nonce = str(int(time.time()*1000))

# Get API-Sign key: https://docs.kraken.com/rest/#section/Authentication/Headers-and-Signature

def get_kraken_signature(urlpath, data, secret):

    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()

    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()

api_sec = os.environ['API_SEC_KRAKEN']

data = {
    "nonce": api_nonce 
}

signature = get_kraken_signature("/0/private/Balance", data, api_sec)
print("API-Sign: {}".format(signature))
