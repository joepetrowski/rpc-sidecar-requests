#%% INFO
# Simple script to fetch block info from a Substrate node using:
# https://github.com/paritytech/substrate-api-sidecar
#
import requests
import json

max_block = 775_000

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
	return block_info

def sync(height):
	responses = []
	for block in range(0, height):
		try:
			response = requests.get(base_url + '/' + path + '/' + str(block))
		except:
			# Probably the sidecar has crashed.
			print('Sidecar request failed! Returning blocks fetched so far...')
			break
		block_info = process_response(response, block)
		check_for_double_xt(block_info)
		responses.append(block_info)
	return responses

def check_for_double_xt(block_info):
	assert(type(block_info) == dict)
	if 'extrinsics' in block_info.keys():
		xts = block_info['extrinsics']
		assert(type(xts) == list)
		xt_len = len(xts)
		for ii in range(0, xt_len):
			for jj in range(0, ii):
				if xts[ii]['hash'] == xts[jj]['hash'] and ii != jj:
					print(
						'Warn! Block {} has duplicate extrinsics. Hash: {}'.format(
							block_info['number'],
							xts[ii]['hash']
						)
					)
	else:
		print('Block {} has no extrinsics.'.format(block_info['number']))

if __name__ == "__main__":
	blocks = sync(max_block)
