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
		self.month = inputs['month']
		self.start_block = inputs['start_block']
		self.end_block = inputs['end_block']
		self.store_blocks = inputs['storage']

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
		elif self.network == 'kusama':
			self.decimals = 1e12
			self.token = 'KSM'
		else:
			self.decimals = 1 # just show planks
			self.token = 'DEV'
		
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
					and event['method']['method'] == 'Reward'
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

	# Hardcoded lookup table of blocks on Polkadot and Kusama.
	def look_up_monthly_blocks(self, month: str):
		if self.network == 'kusama':
			start_block = 2671528
			# Only valid from 2064961 (v1058 with simple payouts)
			# Even better from 2671528 (v2005 without legacy lazy payouts)
			blocks_by_month = {
				'2020' : {
					'03' : 1255489,
					'04' : 1692602,
					'05' : 2111318,
					'06' : 2553304,
					'07' : 2978427,
					'08' : 3414276,
					'09' : 3851274,
					'10' : 4279102,
					'11' : 4720924,
					'12' : 5142315,
				},
				'2021' : {
					'01' : 5578732,
					'02' : 6015486,
					'03' : 6410849,
					'04' : 6849733,
					'05' : 7275920,
					'06' : 7717129,
					'07' : 8146902,
				},
			}
		elif self.network == 'polkadot':
			start_block = 325148
			blocks_by_month = {
				'2020' : {
					'05' : 0,
					'06' : 325148, # Note: actual first block of June is 77028, but staking was not enabled until 325148.
					'07' : 507735,
					'08' : 952103,
					'09' : 1396338,
					'10' : 1826891,
					'11' : 2270711,
					'12' : 2700565,
				},
				'2021' : {
					'01' : 3144988,
					'02' : 3589593,
					'03' : 3991450,
					'04' : 4434979,
					'05' : 4866038,
					'06' : 5308563,
					'07' : 5738775,
				},
			}
		else:
			start_block = 0
			blocks_by_month = { '1900' : { '00' : 0 } }
		
		if month == 'all':
			if self.network == 'kusama':
				print('Returning all data from June 2020 to present due to historical incompatibility.')
				return blocks_by_month['2020']['06'], self.get_chain_tip()
			elif self.network == 'polkadot':
				print('Returning all data from June 2020 when staking was enabled.')
				return 325148, self.get_chain_tip()
			else:
				return 0, self.get_chain_tip()
		elif month == 'blockrange':
			if self.end_block == -1:
				end_block = self.get_chain_tip()
			elif self.end_block < self.start_block:
				print('End block must be greater than start block. Going to chain tip.')
				end_block = self.get_chain_tip()
			else:
				end_block = self.end_block
			return self.start_block, end_block

		y = month[:4]
		m = month[-2:]

		if y in blocks_by_month and m in blocks_by_month[y]:
			start_block = blocks_by_month[y][m]

		if self.network == 'kusama' and start_block < 2671528:
			print(
				'Warning: Starting below block 2,671,528 on Kusama where payout events did not reference stash address.'
			)
		elif self.network == 'polkadot' and start_block < 325148:
			print(
				'Note: Starting search below block 325,148. There will not be any reward events as NPoS was not enabled.'
			)

		if int(m) == 12: # New Year
			y = str(int(y) + 1)
			m = '01'
		else:
			m = str(int(m) + 1)
			m = m.zfill(2)

		if y in blocks_by_month and m in blocks_by_month[y]:
			end_block = blocks_by_month[y][m] + 1
		else:
			print('No block in registry for end of month. Forecasting...')
			potential_end_block = 31 * 14400 + start_block
			chain_height = self.get_chain_tip()
			if potential_end_block > chain_height:
				print('Still in the requested month. Collecting data up to present.')
				end_block = chain_height
			else:
				end_block = potential_end_block
		print('Collecting info for {} from block {} to {}\n'.format(month, start_block, end_block))
		return start_block, end_block

	# The main function.
	def sync_blocks(self):
		start, end = self.look_up_monthly_blocks(self.month)
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
		'-m', '--month',
		help='The month in which to look up rewards. Format \'yyyy-mm\', \'blockrange\', or \'all\'',
		type=str,
		required=True
	)
	parser.add_argument(
		'--startblock',
		help='Block on which to start collection.',
		type=str,
		default='-1'
	)
	parser.add_argument(
		'--endblock',
		help='Block on which to end collection. If none is provided, it will collect until the chain tip.',
		type=str,
		default='-1'
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

	args = parser.parse_args()

	if args.stash[-5:].lower() == '.json':
		with open(args.stash, mode='r') as address_file:
			addresses = json.loads(address_file.read())
	else:
		addresses = { args.stash: 'provided-address' }

	if args.month == 'blockrange':
		assert(int(args.startblock) >= 0)

	input_args = {
		'addresses': addresses,
		'month': args.month,
		'start_block': int(args.startblock),
		'end_block': int(args.endblock),
		'endpoint': args.sidecar,
		'storage': args.no_storage,
		'filter': args.filter
	}
	return input_args

if __name__ == '__main__':
	input_args = parse_args()
	p = StakingRewardsLogger(input_args)
	p.sync_blocks()
