#%%
# Example
import requests
import json

# Get a block by number.
url = 'http://127.0.0.1:8080/block/2077200'
response = requests.get(url)
if response.ok:
	block_by_number = json.loads(response.text)
	# print(block_by_number)
else:
	print(response.text)
