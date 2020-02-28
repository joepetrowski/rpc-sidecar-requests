#%% INFO
# Simple script to fetch block info from a Substrate node using:
# https://github.com/paritytech/substrate-api-sidecar
#
import requests
import json
import time

# Block to start initial sync at (0 for genesis).
start_block = 0
# Block to sync to (set to 0 to sync to current chain tip).
max_block = 0
# Keep syncing? `False` will stop program after initial sync.
continue_sync = True

def construct_url(path=None, param1=None, param2=None):
	base_url = 'http://127.0.0.1:8080'
	if path:
		url = base_url + '/' + str(path)
		if param1 or param1 == 0:
			url = url + '/' + str(param1)
			if param2 or param2 == 0:
				url = url + '/' + str(param2)
	return url

def print_block_info(block_info: dict):
	print(
		'Block {:>9,} has state root {}'.format(
			block_info['number'], block_info['stateRoot']
		)
	)

def process_response(response, block_number=None):
	if response.ok:
		block_info = json.loads(response.text)
		if block_number:
			assert(block_info['number'] == block_number)
		if block_info['number'] % 10_000 == 0:
			# Print some info... really just to show that it's making progress.
			print_block_info(block_info)
	else:
		print('Response Error: {}'.format(response.status_code))
		block_info = {
			'number' : block_number,
			'Response Error' : response.status_code
		}
	return block_info

def get_chain_height():
	try:
		url = construct_url('block')
		response = requests.get(url)
	except:
		print('Unable to fetch latest block.')
		return 0 # genesis
	
	block_info = process_response(response)

	if block_info['number']:
		chain_height = block_info['number']
	else:
		chain_height = 0
		print('Warn! Bad response from client. Returning genesis block.')
	return chain_height

def sync(from_block=0, to_block=None):
	responses = []
	if not to_block:
		to_block = get_chain_height()

	for block in range(from_block, to_block):
		try:
			url = construct_url('block', block)
			response = requests.get(url)
		except:
			# Probably the sidecar has crashed.
			print('Sidecar request failed! Returning blocks fetched so far...')
			break
		block_info = process_response(response, block)
		check_for_double_xt(block_info)
		responses.append(block_info)
	return responses

def check_for_double_xt(block_info: dict):
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
					write_block_to_file(block_info, 'duplicate-xt')
	else:
		print('Block {} has no extrinsics.'.format(block_info['number']))

def get_highest_synced(blocks: list):
	highest_synced = 0
	if len(blocks) > 0:
		highest_synced = blocks[-1]['number']
	return highest_synced

def add_new_blocks(blocks: list, highest_synced: int, chain_tip: int):
	# `highest_synced + 1` here because we only really want blocks with a child.
	if chain_tip == highest_synced + 1:
		print('Chain synced.')
		sleep(10, blocks)
	elif chain_tip > highest_synced + 1:
		new_blocks = sync(highest_synced + 1, chain_tip)
		blocks.extend(new_blocks)
		sleep(1, blocks)
	elif chain_tip < highest_synced + 1:
		print('This is impossible, therefore somebody messed up.')
		sleep(10, blocks)
	return blocks

def sleep(sec: int, blocks: list):
	try:
		time.sleep(sec)
	except KeyboardInterrupt:
		write_and_exit(blocks)

def write_and_exit(blocks: list):
	savedata = input('Do you want to save the block data? (y/N): ')
	if savedata.lower() == 'y':
		write_to_file(blocks)
	exit()

def write_to_file(blocks: list):
	with open('blocks.data', 'w') as f:
		json.dump(blocks, f)

def write_block_to_file(block: dict, reason='info'):
	fname = 'block-{}-{}.json'.format(block['number'], reason)
	with open(fname, 'w') as f:
		json.dump(block, f)

def read_from_file(start_desired: int, end_desired: int):
	try:
		with open('blocks.data', 'r') as f:
			blockdata = json.load(f)
	except:
		print('No data file.')
		blockdata = []
	if blockdata:
		start_block = blockdata[0]['number']
		end_block = blockdata[-1]['number']
		if start_block <= start_desired and end_block >= end_desired:
			# TODO: Prune to desired set.
			print('Imported blocks {} to {}.'.format(start_block, end_block))
		else:
			# TODO: Return the partial set and sync around it.
			blockdata = []
			print('Block data exists but does not cover desired blocks.')
	return blockdata

if __name__ == "__main__":
	if max_block == 0:
		max_block = get_chain_height()
	print('Starting sync from block {} to block {}'.format(start_block, max_block))
	blocks = sync(start_block, max_block)

	if continue_sync:
		while True:
			highest_synced = get_highest_synced(blocks)
			chain_tip = get_chain_height()
			blocks = add_new_blocks(blocks, highest_synced, chain_tip)
	else:
		write_and_exit(blocks)
