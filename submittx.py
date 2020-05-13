import requests
import json

# Submit a serialized transaction.
# url = 'https://cb-cc1-h6ffqwh0ynup4.paritytech.net/tx/'
url = 'https://cb-runtime-wk8yx7pds0ag.paritytech.net/tx/'
tx_headers = {'Content-type' : 'application/json', 'Accept' : 'text/plain'}
response = requests.post(
	url,
	data='{"tx": ""}',
	headers=tx_headers
)

tx_response = json.loads(response.text)
print(response.status_code)
print(tx_response)
