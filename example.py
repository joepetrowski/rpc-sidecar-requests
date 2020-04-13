#%%
# Example
import requests
import json

# Get the latest finalized block.
url = 'http://127.0.0.1:8080/block/'
response = requests.get(url)
if response.ok:
	latest_block = json.loads(response.text)

# Get a block by number.
url = 'http://127.0.0.1:8080/block/1870616'
response = requests.get(url)
if response.ok:
	block_by_number = json.loads(response.text)

# Get the current (finalized head) balance of an address.
url = 'http://127.0.0.1:8080/balance/Gbuksma2CxcuYVZx2upsCXbAFgZMbJgAYGeHGmzdcJtFhX5'
response = requests.get(url)
if response.ok:
	address_balance = json.loads(response.text)

# Get the balance of an address at a particular block.
url = 'http://127.0.0.1:8080/balance/Gbuksma2CxcuYVZx2upsCXbAFgZMbJgAYGeHGmzdcJtFhX5/296229'
response = requests.get(url)
if response.ok:
	address_balance_at_block = json.loads(response.text)

# Get the staking information of a stash address.
url = 'http://127.0.0.1:8080/payout/DTLcUu92NoQw4gg6VmNgXeYQiNywDhfYMQBPYg2Y1W6AkJF'
response = requests.get(url)
if response.ok:
	payout_info = json.loads(response.text)

# Get the staking information of a stash address at a particular block.
url = 'http://127.0.0.1:8080/payout/DTLcUu92NoQw4gg6VmNgXeYQiNywDhfYMQBPYg2Y1W6AkJF/624584'
response = requests.get(url)
if response.ok:
	payout_info_at_block = json.loads(response.text)

# Get the latest metadata.
url = 'http://127.0.0.1:8080/metadata/'
response = requests.get(url)
if response.ok:
	metadata = json.loads(response.text)

# Get the metadata at a particular block.
url = 'http://127.0.0.1:8080/metadata/1000'
response = requests.get(url)
if response.ok:
	metadata_at_block = json.loads(response.text)

# Submit a serialized transaction.
url = 'http://127.0.0.1:8080/tx/'
tx_headers = {'Content-type' : 'application/json', 'Accept' : 'text/plain'}
response = requests.post(
	url,
	data='{"tx": "0xed0...000"}',
	headers=tx_headers
)
# Not checking the response here as it gives useful information in case of error.
tx_response = json.loads(response.text)
