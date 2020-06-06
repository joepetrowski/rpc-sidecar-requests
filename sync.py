#%% INFO
# Simple script to fetch block info from a Substrate node using:
# https://github.com/paritytech/substrate-api-sidecar
#
import requests
import json
import time
import pickle
import argparse
from tkinter import messagebox

class Sync:
	def __init__(self, endpoint, write, use_json, start_block, end_block, continue_sync, fprefix):
		# User inputs
		self.endpoint = endpoint
		self.write = write
		self.use_json = use_json
		self.start_block = start_block
		self.end_block = end_block
		self.continue_sync = continue_sync
		self.file_prefix = fprefix

		# Constructors
		self.blocks = []

		self.process_inputs()

	def get_block(self, index: int):
		return self.blocks[index]

	def process_inputs(self):
		if self.end_block > 0:
			assert(self.end_block > self.start_block)
		if self.end_block == 0:
			self.end_block = self.get_chain_height()

	# Construct a path to some sidecar info.
	def construct_url(self, path=None, param1=None, param2=None):
		base_url = self.endpoint
		if path:
			url = base_url + '/' + str(path)
			if param1 or param1 == 0:
				url = url + '/' + str(param1)
				if param2 or param2 == 0:
					url = url + '/' + str(param2)
		return url

	# Request some data from sidecar.
	def sidecar_request(self, endpoint):
		try:
			response = requests.get(endpoint)
		except:
			print('Unable to connect to sidecar.')

		data = {}
		if response.ok:
			data = json.loads(response.text)
		else:
			error_message = 'Response Error: {}'.format(response.status_code)
			print(error_message)
			data = { 'error' : error_message }
		return data

	# Get the block number of the current finalized head.
	def get_chain_height(self):
		url = self.construct_url('block')
		latest_block = self.sidecar_request(url)
		if 'error' in latest_block.keys():
			print('Warn! Bad response from client. Returning genesis block.')
			return 0
		self.process_block(latest_block)
		chain_height = latest_block['number']
		return chain_height

	def fetch_block(self, number: int):
		url = self.construct_url('block', number)
		block = self.sidecar_request(url)
		if 'error' in block.keys():
			print('Warn! Bad response from client on block {}.'.format(number))
		self.process_block(block)
		self.log_noteworthy(block)
		return block

	def log_noteworthy(self, block: dict):
		if block['number'] % 10_000 == 0:
			self.print_block_info(block)
		for xt in block['extrinsics']:
			if 'sudo' in xt['method']:
				print('Block {}: {}'.format(block['number'], xt['method']))
				messagebox.showwarning(
					title='Sudo',
					message='Block {}: {}'.format(block['number'], xt['method'])
				)
			if 'error' in xt['info']:
				print('Block {}: Fee error'.format(block['number']))
		if len(block['onInitialize']['events']) > 0:
			self.log_events(block['onInitialize']['events'], block['number'])
		if len(block['onFinalize']['events']) > 0:
			self.log_events(block['onFinalize']['events'], block['number'])

	def log_events(self, events: list, block_number: int):
		for event in events:
			if 'method' in event:
				if event['method'] == 'scheduler.Dispatched':
					print(
						'Block {}: Scheduler Dispatched {}'.format(block_number, event['data'][1])
					)
				elif event['method'] == 'system.CodeUpdated':
					print('Block {}: Code Updated'.format(block_number))
				elif event['method'] == 'session.NewSession':
					print('Block {}: New Session {}'.format(block_number, event['data'][0]))

	# A bunch of asserts to make sure we have a valid block. Make block number an int.
	def process_block(self, block: dict, block_number=None):
		assert('number' in block.keys())
		block['number'] = int(block['number'])
		assert('stateRoot' in block.keys())
		assert('onInitialize' in block.keys())
		assert('extrinsics' in block.keys())
		assert('onFinalize' in block.keys())
		if block_number:
			assert(int(block['number']) == block_number)

	# Print some info about a block. Mostly used to show that sync is progressing.
	def print_block_info(self, block: dict):
		print(
			'Block {:>9,} has state root {}'.format(
				int(block['number']), block['stateRoot']
			)
		)

	# Actually get blocks.
	def sync(self, from_block=0, to_block=None):
		if not to_block:
			to_block = self.get_chain_height()

		for block_number in range(from_block, to_block):
			block = self.fetch_block(block_number)
			self.blocks.append(block)

	# Get the block number of the highest synced block.
	def get_highest_synced(self):
		highest_synced = 0
		if len(self.blocks) > 0:
			highest_synced = self.blocks[-1]['number']
		return highest_synced

	# The main logic about adding new blocks to the chain.
	def add_new_blocks(self, highest_synced: int, chain_tip: int):
		# `highest_synced + 1` here because we only really want blocks with a child.
		if chain_tip == highest_synced + 1:
			print('Chain synced at height {:,}'.format(chain_tip))
			self.sleep(60)
		elif chain_tip > highest_synced + 1:
			self.sync(highest_synced + 1, chain_tip)
			self.sleep(1)
		elif chain_tip < highest_synced + 1:
			print('This is impossible, therefore somebody messed up.')
			self.sleep(60)

	# Wait, but if interrupted, exit.
	def sleep(self, sec: int):
		try:
			time.sleep(sec)
		except KeyboardInterrupt:
			self.write_and_exit()

	# Ask user if they want to save the block data and then exit.
	def write_and_exit(self):
		savedata = input('Do you want to save the block data? (y/N): ')
		if savedata.lower() == 'y':
			self.write_to_file()
		exit()

	# Write all blocks to a single file.
	def write_to_file(self):
		fname = input('Input a filename: ')
		if self.use_json:
			fn = fname + '.data'
			with open(fn, 'w') as f:
				json.dump(self.blocks, f)
		else:
			fn = fname + '.pickle'
			with open(fn, 'wb') as f:
				pickle.dump(self.blocks, f)

	# Write a single block to a JSON file.
	def write_block_to_file(self, reason='info'):
		fname = 'blocks/{}-{}-{}.json'.format(
			self.file_prefix,
			block['number'],
			reason
		)
		with open(fname, 'w') as f:
			json.dump(block, f, indent=2)

	# Read blocks from a file.
	def read_from_file(self, start_desired: int, end_desired: int):
		print('Importing blocks...')
		try:
			if use_json:
				fname = self.file_prefix + '.data'
				with open(fname, 'r') as f:
					self.blocks = json.load(f)
			else:
				fname = self.file_prefix + '.pickle'
				with open(fname, 'rb') as f:
					self.blocks = pickle.load(f)
		except:
			print('No data file.')
			self.blocks = []
		if blockdata:
			print('Imported {:,} blocks.'.format(len(self.blocks)))
			start_block = self.blocks[0]['number']
			end_block = self.block[-1]['number']
			if start_block <= start_desired and end_block >= end_desired:
				# TODO: Prune to desired set.
				print('Imported blocks {} to {}.'.format(start_block, end_block))
			else:
				# TODO: Return the partial set and sync around it.
				self.blocks = []
				print('Block data exists but does not cover desired blocks.')

def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument(
		'-w', '--write-files',
		help='Write blocks that have duplicate transactions to files.',
		action='store_true'
	)
	parser.add_argument(
		'-j', '--json',
		help='Import blocks from JSON (plaintext) file. Slower than the default, pickle.',
		action='store_true'
	)
	parser.add_argument(
		'-s', '--start-block',
		help='First block to import.',
		type=int,
		default=0
	)
	parser.add_argument(
		'-m', '--max-block',
		help='Max block number to import. 0 means chain tip. Default 0.',
		type=int,
		default=0
	)
	args = parser.parse_args()

	write = args.write_files
	use_json = args.json
	start_block = args.start_block
	max_block = args.max_block
	return (write, use_json, start_block, max_block)

if __name__ == "__main__":
	(write, use_json, start_block, max_block) = parse_args()

	endpoint = 'http://127.0.0.1:8080'
	syncer = Sync(endpoint, write, use_json, start_block, max_block, True, 'blockdata')

	if max_block == 0:
		max_block = syncer.get_chain_height()
	print('Starting sync from block {} to block {}'.format(start_block, max_block))
	blocks = syncer.sync(start_block, max_block)
	# blocks = read_from_file(0, 10)

	if syncer.continue_sync:
		while True:
			highest_synced = syncer.get_highest_synced()
			chain_tip = syncer.get_chain_height()
			blocks = syncer.add_new_blocks(highest_synced, chain_tip)
	else:
		syncer.write_and_exit()
