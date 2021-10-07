import sys
import time
import json
import os.path
from sidecar import Sidecar
from datetime import datetime
from pycoingecko import CoinGeckoAPI
import argparse

class StakingRewardsLogger(Sidecar):
	def __init__(self, inputs):
		# APIs
		super().__init__(inputs['endpoint'])
		self.cg = CoinGeckoAPI()
		self.last_cg_time = time.time()

		# Inputs
		self.addresses_of_interest = inputs['addresses']
		self.fromdate = inputs['fromdate']
		self.todate = inputs['todate']
		self.store_blocks = inputs['storage']
		self.verbose = inputs['verbose']

		# If we specified some filter, remove addresses that don't match it.
		removelist = []
		if inputs['filter']:
			for a in self.addresses_of_interest:
				if inputs['filter'] not in self.addresses_of_interest[a]:
					removelist.append(a)
		for address in removelist:
			del(self.addresses_of_interest[address])

		# Data structures
		self.last_block_time = 0
		self.rewards = [[], [], [], [], [], [], [], [], [], [], [], []]
		self.monthly_balances = {}
		for a in self.addresses_of_interest:
			self.monthly_balances[a] = []
		self.months = [
			'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
		]

		# Network specific
		self.network = self.get_chain_spec()
		if self.network == 'polkadot':
			self.decimals = 1e10
			self.token = 'DOT'
			self.block_time = 6
		elif self.network == 'kusama':
			self.decimals = 1e12
			self.token = 'KSM'
			self.block_time = 6
		else:
			self.decimals = 1 # just show planks
			self.token = 'DEV'
			self.block_time = 6
		
		# Create storage directory if it doesn't exist yet
		if self.store_blocks and not os.path.isdir('blocks/{}'.format(self.network)):
			os.makedirs('blocks/{}'.format(self.network))

	# Get chain spec name.
	def get_chain_spec(self):
		spec_info = self.runtime_spec()
		return spec_info['specName']

	# Get the block number of the latest finalized block.
	def get_chain_tip(self):
		latest_block = self.blocks()
		chain_height = int(latest_block['number'])
		return chain_height

	# Get the UNIX time of a block.
	def get_block_time(self, block: dict):
		ts = 0
		for xt in block['extrinsics']:
			if xt['method']['pallet'] == 'timestamp' and xt['method']['method'] == 'set':
				# Block timestamp is in _milliseconds_ since epoch
				ts = int(xt['args']['now']) / 1000
				break
		if ts == 0:
			print('No time set for block {}'.format(block['number']))
		return ts

	# If this is the first block of a new month, log it.
	def log_new_month(self, block: dict):
		this_block_time = self.get_block_time(block)
		last_block_date = datetime.utcfromtimestamp(self.last_block_time).strftime('%Y-%m-%d')
		this_block_date = datetime.utcfromtimestamp(this_block_time).strftime('%Y-%m-%d')
		month = int(this_block_date[-5:-3])
		if this_block_date[:-3] > last_block_date[:-3]:
			if self.last_block_time > 0:
				self.compare_monthly_balances(int(block['number']))
				self.month_payout(month - 1)
			print('Block {}: First block of {}'.format(block['number'], this_block_date))
		self.last_block_time = this_block_time
		return this_block_date
	
	# Find the first block to occur on or after a given timestamp.
	# `time`               Desired time of the block, in 'YYYY-mm-ddTHH:MM:SS'
	# `guess_block_number` An estimate if you have a block that's close to the desired time. Usually
	#                      not used in calling the function, but in recursion.
	def find_block_at_time(self, time: str, guess_block_number=None):
		# Convert the input to a UNIX timestamp.
		desired_time = datetime.fromisoformat(time).timestamp()
		if self.verbose: print('\nDesired time:     {}'.format(desired_time))

		# If no guess is provided, start with the chain tip.
		if not guess_block_number:
			guess_block_number = self.get_chain_tip()
			guess_block = self.fetch_block(guess_block_number)
			guess_block_time = self.get_block_time(guess_block)
			assert(guess_block_time >= desired_time)
		else:
			guess_block = self.fetch_block(guess_block_number)
			guess_block_time = self.get_block_time(guess_block)
		
		if self.verbose: print('Guess block time: {}'.format(guess_block_time))

		# Course search.
		if abs(guess_block_time - desired_time) > self.block_time * 5:
			if self.verbose: print('Doing course search')
			new_guess = guess_block_number - int((guess_block_time - desired_time) / self.block_time)
			if self.verbose: print('New guess: {}'.format(new_guess))
			return self.find_block_at_time(time, new_guess)

		# We are close, fine search.
		else:
			if self.verbose: print('Doing fine search')
			if guess_block_time >= desired_time:
				if self.verbose: print('Guess block too high')
				guess_block_parent = self.fetch_block(guess_block_number - 1)
				guess_block_parent_time = self.get_block_time(guess_block_parent)
				if guess_block_parent_time < desired_time:
					# SUCCESS!
					target = int(guess_block_number)
					if self.verbose: print('\nSuccess! Block number: {}'.format(target))
					return target
				else:
					new_guess = guess_block_number - int((guess_block_time - desired_time) / self.block_time)
					if self.verbose: print('New guess: {}'.format(new_guess))
					return self.find_block_at_time(time, new_guess)
			else:
				if self.verbose: print('Guess block too low')
				guess_block_child = self.fetch_block(guess_block_number + 1)
				guess_block_child_time = self.get_block_time(guess_block_child)
				if guess_block_child_time >= desired_time:
					# SUCCESS!
					target = int(guess_block_number + 1)
					if self.verbose: print('\nSuccess! Block number: {}'.format(target))
					return target
				else:
					new_guess = guess_block_number + int((desired_time - guess_block_time) / self.block_time)
					if self.verbose: print('New guess: {}'.format(new_guess))
					return self.find_block_at_time(time, new_guess)

	# Compare balances at start and end of a month.
	def compare_monthly_balances(self, bn: int):
		for a in self.addresses_of_interest:
			# Get the balances of the account
			balances = self.account_balance_info(a, bn)
			free = int(balances['free'])
			reserved = int(balances['reserved'])

			# Add them to the list
			self.monthly_balances[a].append((bn, free, reserved))

			# Compare them to the last balance
			if len(self.monthly_balances[a]) > 1:
				free_diff = self.monthly_balances[a][-1][1] - self.monthly_balances[a][-2][1]
				reserved_diff = self.monthly_balances[a][-1][2] - self.monthly_balances[a][-2][2]
				print(
					'\nAddress: {}\nFree Change:     {}\nReserved Change: {}'
					.format(a, free_diff, reserved_diff)
				)

	# Fetches a block and potentially writes it to disk. Doesn't do any quality assurance on the
	# data.
	def fetch_block(self, block_requested: int):
		fname = 'blocks/{}/block-{}.json'.format(self.network, block_requested)
		# Check if we have the block saved and can read it in.
		if os.path.isfile(fname):
			# read the file
			with open(fname, 'r') as f:
				block = json.loads(f.read())
		else:
			# fetch the block from sidecar
			block = self.blocks(block_requested)
			if self.store_blocks and 'error' not in block.keys():
				# write the file so it's there next time
				with open(fname, 'w') as f:
					json.dump(block, f, indent=2)
		return block

	# Main function for processing blocks.
	def process_block(self, block_requested: int):
		# Get the block
		block = self.fetch_block(block_requested)

		# Make sure there's no error. If there is, note it.
		if 'error' in block.keys():
			print('Error block {}: {}'.format(block_requested, block['error']))
		else:
			# Handle the block.
			bn = int(block['number'])
			date = self.log_new_month(block)

			# Get author address and compare with addresses of interest
			fees = self.check_for_fees(block)

			block_rewards = 0
			for xt in block['extrinsics']:
				if not xt['events']:
					print('Block {}: Error decoding events'.format(bn))
				block_rewards += self.check_for_payouts(xt)
			
			if fees + block_rewards > 0:
				self.add_value_to_totals(date, bn, fees + block_rewards)

	# Use CoinGecko API to get price of token on a specific date.
	def get_price_on_date(self, date):
		date_for_cg = date[-2:] + '-' + date[-5:-3] + '-' + date[0:4] # dd-mm-yyyy
		
		now = time.time()
		# Slows things down, but ensures that we don't hit the rate limit on the CoinGecko API
		if now < (self.last_cg_time + 0.75):
			time.sleep(0.75)
		self.last_cg_time = time.time()

		try:
			prices = self.cg.get_coin_history_by_id(self.network, date_for_cg)
		except:
			print('CoinGecko price API failure.')
			return 0.0

		if 'market_data' in prices:
			price = prices['market_data']['current_price']['usd']
		else:
			# Just assuming here that this date is before trading.
			price = 0.0
		return price

	# Add any rewards to totals.
	def add_value_to_totals(self, date, bn, token_quantity):
		month = int(date[-5:-3])
		p = self.get_price_on_date(date)
		value = round(p * token_quantity / self.decimals, 2)
		print(
			'{} Block {}: Payout of {} {} | {} USD'
			.format(date, bn, token_quantity/self.decimals, self.token, value)
		)
		self.add_to_totals(bn, month, token_quantity, value)

	# In case the stash addresses are validators, check for transaction fees.
	def check_for_fees(self, block):
		fees = 0
		author = block['authorId']
		if author in self.addresses_of_interest:
			print('Authored block! {} by {}'.format(
				block['number'],
				self.addresses_of_interest[author])
			)
			for xt in block['extrinsics']:
				for event in xt['events']:
					if (
						'method' in event
						and event['method']['pallet'] == 'balances'
						and event['method']['method'] == 'Deposit'
						and 'data' in event
						and event['data'][0] == author
					):
						fees += int(event['data'][1])
		return fees

	# Add some addresses that we're interested in and see if they received any staking rewards.
	# Note: does not associate rewards with address. As in, it gives the total rewards of all
	# addresses in aggregate.
	def check_for_payouts(self, xt: dict):
		a = self.addresses_of_interest
		payout = 0
		if 'events' in xt:
			for event in xt['events']:
				if (
					'method' in event
					and event['method']['pallet'] == 'staking'
					and 'Reward' in event['method']['method'] # covers `Reward` and `Rewarded`
					and 'data' in event
					and event['data'][0] in a.keys()
				):
					payout += int(event['data'][1])
		return payout

	# Add payout and value to monthly totals.
	def add_to_totals(self, bn: int, month: int, payout: int, value: float):
		month -= 1
		self.rewards[month].append((bn, payout, value))

	# Calculate total payouts for a month.
	def month_payout(self, month: int):
		month -= 1
		r = self.rewards[month]
		tokens = 0
		dollars = 0.0
		if len(r) > 0:
			total = [sum(p) for p in zip(*r)]
			tokens = total[1] / self.decimals
			dollars = round(total[2], 2)
		print('\n{}: {} {}, {} USD\n'.format(self.months[month], tokens, self.token, dollars))

	# Calculate total payouts for all months.
	def total_payouts(self):
		print('\n')
		for ii in range(len(self.rewards)):
			tokens = 0
			dollars = 0.0
			r = self.rewards[ii]
			if len(r) > 0:
				total = [sum(p) for p in zip(*r)]
				tokens = total[1] / self.decimals
				dollars = round(total[2], 2)
			print('{}: {} {}, {} USD'.format(self.months[ii], tokens, self.token, dollars))

	def print_payout_blocks(self):
		for ii in range(len(self.rewards)):
			r = self.rewards[ii]
			if len(r) > 0:
				reward_blocks = [list(p) for p in zip(*r)][0]
				print('{}: {}'.format(self.months[ii], reward_blocks))

	def erase_line(self):
		CURSOR_UP_ONE = '\x1b[1A'
		ERASE_LINE = '\x1b[2K'
		sys.stdout.write(CURSOR_UP_ONE)
		sys.stdout.write(ERASE_LINE)

	# Get the block that data collection should start at. Some notes:
	#
	# Kusama
	#   - Only valid from block 2_064_961 (runtime v1058 with simple payouts)
	#   - Even better from 2_671_528 (runtime v2005 without legacy lazy payouts)
	#
	# Polkadot
	#   - Staking was enabled in block 325_148
	def get_start_block(self):

		chain_tip = self.get_chain_tip()
		chain_tip_time = self.get_block_time(self.fetch_block(chain_tip))

		if datetime.fromisoformat(self.fromdate).timestamp() > chain_tip_time:
			print('Error: Requested starting from a block in the future. Exiting...')
			sys.exit()
		
		start_block = self.find_block_at_time(self.fromdate)

		if self.network == 'kusama' and start_block < 2671528:
			print(
				'Warning: Starting below block 2,671,528 on Kusama where payout events did not reference stash address.'
			)
		elif self.network == 'polkadot' and start_block < 325148:
			print(
				'Note: Starting search below block 325,148. There will not be any reward events as NPoS was not enabled.'
			)

		return start_block

	# Get the block that data collection should end at.
	def get_end_block(self):

		chain_tip = self.get_chain_tip()
		chain_tip_time = self.get_block_time(self.fetch_block(chain_tip))

		if self.todate.lower() == 'now':
			return chain_tip

		if datetime.fromisoformat(self.todate).timestamp() > chain_tip_time:
			print('Requested ending at a future block. Will end at current chain tip.')
			return chain_tip
		
		end_block = self.find_block_at_time(self.todate)
		return end_block

	# The main function.
	def sync_blocks(self):
		start = self.get_start_block()
		end = self.get_end_block()

		print('\nStarting collection at block: {:,}'.format(start))
		print('Ending collection at block:   {:,}'.format(end))
		for bn in range(start, end):
			self.process_block(bn)

			# This can be slow, so tell us that we're actually making progress.
			if bn % 100 == 0:
				print('At block: {:,}'.format(bn))
				self.erase_line()

		# Total up the payouts at the end.
		self.total_payouts()
		self.print_payout_blocks()

def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument(
		'-s', '--stash',
		help='Either a single stash address for which to find rewards, or path to JSON file keyed by stash.',
		type=str,
		required=True
	)
	parser.add_argument(
		'-f', '--fromdate',
		help='From date or time, inclusive. Format: \'2021-07-20T12:34:56\'',
		type=str,
		required=True
	)
	parser.add_argument(
		'-t', '--todate',
		help='To date or time, exclusive. Format: \'2021-07-20T12:34:56\' or \'now\'',
		type=str,
		default='now'
	)
	parser.add_argument(
		'--sidecar',
		help='Endpoint for Sidecar.',
		type=str,
		default='http://127.0.0.1:8080/'
	)
	parser.add_argument(
		'--no-storage',
		help='Do not store blocks on disk for faster retrieval later.',
		action='store_false'
	)
	parser.add_argument(
		'--filter',
		help='Filter JSON input for addresses values that contain some keyword.',
		type=str,
		default=''
	)
	parser.add_argument(
		'-v','--verbose',
		help='Verbose logging.',
		default=False,
		action='store_true'
	)

	args = parser.parse_args()

	if args.stash[-5:].lower() == '.json':
		with open(args.stash, mode='r') as address_file:
			addresses = json.loads(address_file.read())
	else:
		addresses = { args.stash: 'provided-address' }

	input_args = {
		'addresses': addresses,
		'fromdate': args.fromdate,
		'todate': args.todate,
		'endpoint': args.sidecar,
		'storage': args.no_storage,
		'filter': args.filter,
		'verbose': args.verbose,
	}
	return input_args

if __name__ == '__main__':
	input_args = parse_args()
	p = StakingRewardsLogger(input_args)
	p.sync_blocks()
