#%% INFO
# Simple script to fetch block info from a Substrate node using:
# https://github.com/paritytech/substrate-api-sidecar
#
import requests
import json

responses = []
max_block = 775_001

base_url = 'http://127.0.0.1:8080'
path = 'block'

def print_block_info(block_info):
	print(
		'Block {:>9,} has state root {}'.format(
			block_info['number'], block_info['stateRoot']
		)
	)

def process_response(response, block_number):
	if response.ok:
		block_info = json.loads(response.text)
		assert(block_info['number'] == block_number)
		if block_info['number'] % 5000 == 0:
			# Print some info... really just to show that it's making progress.
			print_block_info(block_info)
	else:
		print('Response Error: {}'.format(response.status_code))
		block_info = {
			'number' : block_number,
			'Response Error' : response.status_code
		}

for block in range(0, max_block):
	response = requests.get(base_url + '/' + path + '/' + str(block))
	block_info = process_response(response, block)
	responses.append(block_info)
