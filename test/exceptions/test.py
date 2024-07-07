import random
from tenacity import *

@retry(reraise=True, wait=wait_fixed(2), stop=stop_after_attempt(3))
def wait_2_s():
    test = "hello"
    return test
    

print(wait_2_s())

print(f"hello2")
