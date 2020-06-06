#%%
import requests
import json

# Submit a serialized transaction.
url = 'http://127.0.0.1:8080/tx/fee-estimate/'
tx_headers = {'Content-type' : 'application/json', 'Accept' : 'text/plain'}
response = requests.post(
	url,
	data='{"tx": ""}',
	headers=tx_headers
)

tx_response = json.loads(response.text)
print(response.status_code)
print(tx_response)
