import requests
TOKEN = "6636019746:AAHBxy9eZH-RhP4Reubb3vxwJY8VhPj_T_U"
chat_id = "481520678"
message = "hello from python"
url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
requests.get(url)
# print(requests.get(url).json())
