#%% INFO
# Simple script to fetch block info from a Substrate node using:
# https://github.com/paritytech/substrate-api-sidecar
#
import sys
import requests
import json
import time
from datetime import datetime
import pickle
import argparse

class Sync:
	def __init__(self, inputs):
		# User inputs
		self.endpoint = inputs['endpoint']
		self.write = inputs['write']
		self.use_json = inputs['use_json']
		self.start_block = inputs['start_block']
		self.end_block = inputs['end_block']
		self.pruning = inputs['pruning']
		self.file_prefix = inputs['fprefix']
		self.addresses_of_interest = inputs['addresses']

		self.process_inputs()

		# Constructors
		self.blocks = []
		self.last_block_time = 0
		self.network = self.get_chain_spec()
		if self.network == 'polkadot':
			self.decimals = 1e10
		else:
			self.decimals = 1e12

		print('Connected to Sidecar on the {} network.'.format(self.network))

	# Process the user's inputs to the class.
	def process_inputs(self):
		if self.end_block > 0:
			assert(self.end_block > self.start_block)
		if self.end_block == 0:
			self.end_block = self.get_chain_height()
		if self.endpoint[-1] != '/':
			self.endpoint = self.endpoint + '/'
	
	def get_chain_spec(self):
		url = self.construct_url('tx', 'artifacts')
		artifacts = self.sidecar_request(url)
		return artifacts['specName']

	# Construct a path to some sidecar info.
	def construct_url(self, path=None, param1=None, param2=None):
		base_url = self.endpoint
		if path:
			url = base_url + str(path)
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
			print('Unable to connect to sidecar. Pausing for 30 seconds.')
			time.sleep(30)
			self.erase_line()
			return { 'error' : 'Unable to connect to sidecar.' }

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
		while 'error' in latest_block.keys():
			latest_block = self.sidecar_request(url)
		latest_block = self.process_block(latest_block)
		chain_height = latest_block['number']
		return chain_height

	# Fetch a block, make sure it has all the things we think it should have, and log any
	# interesting events or transactions.
	def fetch_block(self, number: int):
		url = self.construct_url('block', number)
		block = self.sidecar_request(url)
		if 'error' in block.keys():
			print('Warn! Bad response from client on block {}.'.format(number))
			print('Error message: {}'.format(block['error']))
			return { 'error' : 'No block.' }
		block = self.process_block(block)
		self.log_noteworthy(block)
		return block

	# Get the UNIX time of a block.
	def get_block_time(self, block: dict):
		ts = 0
		for xt in block['extrinsics']:
			if xt['method'] == 'timestamp.set':
				# Block timestamp is in _milliseconds_ since epoch
				ts = int(xt['args']['now']) / 1000
				break
		if ts == 0:
			print('No time set for block {}'.format(block['number']))
		return ts

	# If this is the first block of a new (UTC) day, log it.
	def log_new_day(self, block: dict):
		this_block_time = self.get_block_time(block)
		last_block_date = datetime.utcfromtimestamp(self.last_block_time).strftime('%Y-%m-%d')
		this_block_date = datetime.utcfromtimestamp(this_block_time).strftime('%Y-%m-%d')
		self.last_block_time = this_block_time
		if this_block_date > last_block_date and len(self.blocks) > 0:
			print('Block {}: First block of {}'.format(block['number'], this_block_date))

	# Lots of interesting checks to perform on each block.
	def log_noteworthy(self, block: dict):
		bn = block['number']
		# Log if it's a new day
		self.log_new_day(block)

		# Log any interesting events from hooks
		if len(block['onInitialize']['events']) > 0:
			self.log_events(block['onInitialize']['events'], bn)

		# Log some noteable extrinsics
		for xt in block['extrinsics']:
			# Did I get paid, yo
			if xt['method'] == 'staking.payoutStakers' or xt['method'] == 'utility.batch':
				payout = self.check_for_payouts(xt)
				if payout > 0:
					print('Block {}: Staking payout! {} tokens'.format(bn, payout / self.decimals))

			if 'equivocation' in xt['method'].lower():
				print('Block {}: Equivocation Reported'.format(bn))
				for event in xt['events']:
					if 'method' in event and event['method'] == 'offences.Offence':
						self.process_offence(bn, event)

			# Sudo stuff
			if self.network == 'polkadot' and bn < 799302:
				# Did the proxy sudo account make a transaction
				proxy = '14TKt6bUNjKJdfYqVDNFBqzDAwmJ7WaQwfUmxmizJHHrr1Gs'
				if xt['signature'] and xt['signature']['signer'] == proxy:
					print('Block {}: Sudo Proxy Alert! {}'.format(bn, xt['method']))

				# Did the sudo account make a transaction
				sudo = '1KvKReVmUiTc2LW2a4qyHsaJJ9eE9LRsywZkMk5hyBeyHgw'
				if xt['signature'] and xt['signature']['signer'] == sudo:
					print('Block {}: Sudo Alert! {}'.format(bn, xt['method']))

			# Did sidecar fail to get transaction fees
			fee_error = False
			if 'error' in xt['info']:
				print('Block {}: Fee error on {}'.format(bn, xt['method']))
				fee_error = True

			# Fees brainstorming
			if xt['signature'] and xt['paysFee'] and not fee_error:
				self.check_deposit_events(xt, bn)

		if len(block['onFinalize']['events']) > 0:
			self.log_events(block['onFinalize']['events'], bn)

	# Curiosity function. Does `partialFee` match the `Deposit` events.
	def check_deposit_events(self, xt: dict, bn: int):
		if 'events' not in xt.keys():
			print('Extrinsic with no events')
			return
		e = xt['events']
		calc_fee = int(xt['tip']) + int(xt['info']['partialFee'])

		balances_events = self.count_events(e, 'balances.Deposit')
		treasury_events = self.count_events(e, 'treasury.Deposit')

		if balances_events > 1:
			print('Block {}: Multiple balances.Deposit events'.format(bn))
		if treasury_events > 1:
			print('Block {}: Multiple treasury.Deposit events'.format(bn))

		if balances_events == 1 and treasury_events == 1:
			balances_deposit = self.get_deposit_value(e, 'balances')
			treasury_deposit = self.get_deposit_value(e, 'treasury')

			actual_fee = balances_deposit + treasury_deposit
			if actual_fee != calc_fee:
				print('Block {}: Fee mismatch!\n  Events: {}\n  Calc:   {}'
					.format(bn, actual_fee, calc_fee))

	# Count the number of events that match a method.
	def count_events(self, events: list, method: str):
		count = 0
		for e in events:
			if 'method' in e.keys() and e['method'] == method:
				count += 1
		return count
	
	# Get the value of a balances or treasury deposit event. Only works for these two methods.
	def get_deposit_value(self, events: list, pallet: str):
		v = 0
		for e in events:
			if e['method'] == pallet + '.Deposit':
				v = int(e['data'][-1])
		return v

	# Add some addresses that we're interested in and see if they received any staking rewards.
	# Note: does not associate rewards with address. Generally only useful if the list of addresses
	# is e.g. one for Polkadot, one for Kusama, etc.
	def check_for_payouts(self, xt: dict):
		a = self.addresses_of_interest
		payout = 0
		if 'events' in xt:
			for event in xt['events']:
				if (
					'method' in event
					and event['method'] == 'staking.Reward'
					and 'data' in event
					and event['data'][0] in a.keys()
				):
					payout += int(event['data'][1])
		return payout

	# Log interesting events that take place on initialize/finalize.
	def log_events(self, events: list, bn: int):
		for event in events:
			if 'method' in event:
				if event['method'] == 'scheduler.Dispatched':
					print('Block {}: Scheduler Dispatched {}'.format(bn, event['data'][1]))
				elif event['method'] == 'system.CodeUpdated':
					print('Block {}: Code Updated'.format(bn))
				elif event['method'] == 'session.NewSession':
					print('Block {}: New Session {}'.format(bn, event['data'][0]))
				elif event['method'] == 'offences.Offence':
					self.process_offence(bn, event)
				elif event['method'] == 'imOnline.SomeOffline':
					self.process_offline(bn, event)
				elif event['method'] == 'staking.EraPayout':
					era = int(event['data'][0])
					validators = int(event['data'][1]) / self.decimals
					treasury = int(event['data'][2]) / self.decimals
					print(
						'Block {}: Era {} finished\n  Validators: {:,}\n  Treasury:    {:,}'
						.format(bn, era, validators, treasury)
					)
				elif event['method'] == 'grandpa.NewAuthorities':
					count = len(event['data'][0])
					print('Block {}: {} new authorities'.format(bn, count))

	# A bunch of asserts to make sure we have a valid block. Make block number an int.
	def process_block(self, block: dict, bn=None):
		assert('number' in block.keys())
		block['number'] = int(block['number'])
		assert('stateRoot' in block.keys())
		assert('onInitialize' in block.keys())
		assert('extrinsics' in block.keys())
		assert('onFinalize' in block.keys())
		if bn:
			assert(int(block['number']) == bn)
		return block

	# Process an offence event
	def process_offence(self, bn, event):
		kind = str(bytes.fromhex(event['data'][0][2:]), 'utf-8')
		applied = 'applied'
		if not event['data'][2]:
			applied = 'not ' + applied
		print('Block {}: Offence {} for {}'.format(bn, applied, kind))
	
	def process_offline(self, bn, event):
		for offline_validator in event['data'][0]:
			stash = offline_validator[0]
			if stash in self.addresses_of_interest:
				stash = self.addresses_of_interest[stash]
			nominations = offline_validator[1]
			print('Block {}: {} offline'.format(bn, stash))
			for who in nominations['others']:
				nominator = who['who']
				if nominator in self.addresses_of_interest:
					print('  {} nominating'.format(self.addresses_of_interest[nominator]))

	# Print some info about a block. Mostly used to show that sync is progressing.
	def print_block_info(self, block: dict):
		print('Just passed block {:,}'.format(block['number']))

	# Actually get blocks.
	def sync(self, from_block=0, to_block=None):
		if not to_block:
			to_block = self.get_chain_height()

		for bn in range(from_block, to_block):
			block = self.fetch_block(bn)
			if 'error' not in block.keys():
				self.blocks.append(block)
		
		if self.pruning and len(self.blocks) > 1000:
			self.blocks = self.blocks[-1000:]

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
			self.sleep(12)
			self.erase_line()
		elif chain_tip > highest_synced + 1:
			self.sync(highest_synced + 1, chain_tip)
			self.sleep(1)
		elif chain_tip < highest_synced + 1:
			print('This is impossible, therefore somebody messed up.')
			self.sleep(300)

	def erase_line(self):
		CURSOR_UP_ONE = '\x1b[1A'
		ERASE_LINE = '\x1b[2K'
		sys.stdout.write(CURSOR_UP_ONE)
		sys.stdout.write(ERASE_LINE)

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
		help='Max block number to import. 0 means chain tip. Default 0. Implies no continuation of sync.',
		type=int,
		default=0
	)
	parser.add_argument(
		'-o', '--output-prefix',
		help='Prefix for any output files.',
		type=str,
		default='blockdata'
	)
	parser.add_argument(
		'--sidecar',
		help='Endpoint for Sidecar.',
		type=str,
		default='http://127.0.0.1:8080/'
	)
	parser.add_argument(
		'--no-continue',
		help='Do not continue syncing the chain after reaching the chain tip.',
		action='store_true',
	)
	parser.add_argument(
		'-p', '--no-pruning',
		help='Do not prune the block list in memory. Default is 1,000.',
		action='store_false',
	)
	args = parser.parse_args()

	input_args = {
		'write' : args.write_files,
		'use_json' : args.json,
		'start_block' : args.start_block,
		'end_block' : args.max_block,
		'continue_sync' : not args.no_continue,
		'pruning' : args.no_pruning,
		'fprefix' : args.output_prefix,
		'endpoint' : args.sidecar
	}
	if int(input_args['end_block']) != 0:
		input_args['continue_sync'] = False
	return input_args

if __name__ == "__main__":
	with open('./addresses.json', mode='r') as address_file:
		addresses_of_interest = json.loads(address_file.read())
	
	inputs = parse_args()
	inputs['addresses'] = addresses_of_interest
	syncer = Sync(inputs)

	start_block = int(inputs['start_block'])
	max_block = int(inputs['end_block'])

	if max_block == 0:
		max_block = syncer.get_chain_height()
	print('Starting sync from block {} to block {}'.format(start_block, max_block))
	blocks = syncer.sync(start_block, max_block)

	if inputs['continue_sync']:
		while True:
			highest_synced = syncer.get_highest_synced()
			chain_tip = syncer.get_chain_height()
			blocks = syncer.add_new_blocks(highest_synced, chain_tip)
	else:
		syncer.write_and_exit()
