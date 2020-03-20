#%%
# Example
import requests

url = 'http://127.0.0.1:8080/block/'
response = requests.get(url)
if response.ok:
	block_info = json.loads(response.text)
