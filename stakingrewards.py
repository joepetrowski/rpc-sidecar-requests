import sys
import time
import json
from sidecar import Sidecar
from datetime import datetime
from pycoingecko import CoinGeckoAPI

class StakingRewardsLogger(Sidecar):
	def __init__(self, addresses):
		super().__init__('http://127.0.0.1:8080')
		self.cg = CoinGeckoAPI()
		self.addresses_of_interest = addresses
		self.last_block_time = 0
		self.rewards = [
			[], [], [], [], [], [], [], [], [], [], [], []
		]
		self.payout_blocks = [
			[], [], [], [], [], [], [], [], [], [], [], []
		]
		self.monthly_balances = {}
		self.network = self.get_chain_spec()
		if self.network == 'polkadot':
			self.decimals = 1e10
			self.token = 'DOT'
		elif self.network == 'kusama':
			self.decimals = 1e12
			self.token = 'KSM'
		else:
			self.decimals = 1e12
			self.token = 'DEV'
		for a in self.addresses_of_interest:
			self.monthly_balances[a] = []

	# Get chain spec name.
	def get_chain_spec(self):
		artifacts = self.artifacts()
		return artifacts['specName']

	# Get the block number of the latest finalized block.
	def get_chain_tip(self):
		latest_block = self.block()
		chain_height = int(latest_block['number'])
		return chain_height

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
	def log_new_month(self, block: dict):
		this_block_time = self.get_block_time(block)
		last_block_date = datetime.utcfromtimestamp(self.last_block_time).strftime('%Y-%m-%d')
		this_block_date = datetime.utcfromtimestamp(this_block_time).strftime('%Y-%m-%d')
		self.last_block_time = this_block_time
		month = int(this_block_date[-5:-3])
		if this_block_date[:-3] > last_block_date[:-3]:
			self.compare_monthly_balances(int(block['number']))
			self.month_payout(month - 1)
			print('Block {}: First block of {}'.format(block['number'], this_block_date))
		return this_block_date

	# Compare balances at start and end of a month.
	def compare_monthly_balances(self, bn: int):
		for a in self.addresses_of_interest:
			# Get the balances of the account
			balances = self.balance(a, bn)
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

	# Main function for processing blocks.
	def process_block(self, block_requested: int):
		# Get the block
		block = self.block(block_requested)

		# Make sure there's no error. If there is, try again.
		while 'error' in block.keys():
			print('Error block {}: {}'.format(block_requested, block['error']))
			time.sleep(60)
			block = self.block(block_requested)

		# Handle the block.
		bn = int(block['number'])
		date = self.log_new_month(block)
		
		month = int(date[-5:-3])
		payout_calls = [
			'staking.payoutStakers',
			'utility.batch',
			'staking.payoutNominators',
			'staking.payoutValidators'
		]
		for xt in block['extrinsics']:
			if xt['method'] in payout_calls:
				if not xt['events']:
					print('Block {}: Error decoding events'.format(bn))
				payout = self.check_for_payouts(xt)
				if payout > 0:
					p = self.get_price_on_date(date)
					value = round(p * payout / self.decimals, 2)
					print(
						'{} Block {}: Staking payout! {} {} | {} USD'
						.format(date, bn, payout/self.decimals, self.token, value)
					)
					self.add_to_totals(bn, month, payout, value)

	# Use CoinGecko API to get price of token on a specific date.
	def get_price_on_date(self, date):
		date_for_cg = date[-2:] + '-' + date[-5:-3] + '-' + date[0:4] # dd-mm-yyyy
		prices = self.cg.get_coin_history_by_id(self.network, date_for_cg)
		if 'market_data' in prices:
			price = prices['market_data']['current_price']['usd']
		else:
			print('No price data available on {}'.format(date))
			price = 0.0
		return price

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

	# Add payout and value to monthly totals.
	def add_to_totals(self, bn: int, month: int, payout: int, value: float):
		month -= 1
		self.rewards[month].append((bn, payout, value))
		self.payout_blocks[month].append(bn)

	# Calculate total payouts for a month.
	def month_payout(self, month: int):
		months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
		month -= 1
		m = months[month]
		r = self.rewards[month]
		tokens = 0
		dollars = 0.0
		if len(r) > 0:
			total = [sum(p) for p in zip(*r)]
			tokens = total[1] / self.decimals
			dollars = round(total[2], 2)
		print('\n{}: {} {}, {} USD\n'.format(m, tokens, self.token, dollars))

	# Calculate total payouts for all months.
	def total_payouts(self):
		months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
		print('\n')
		for ii in range(len(self.rewards)):
			m = months[ii]
			tokens = 0
			dollars = 0.0
			r = self.rewards[ii]
			if len(r) > 0:
				total = [sum(p) for p in zip(*r)]
				tokens = total[1] / self.decimals
				dollars = round(total[2], 2)
			print('{}: {} {}, {} USD'.format(m, tokens, self.token, dollars))

	def erase_line(self):
		CURSOR_UP_ONE = '\x1b[1A'
		ERASE_LINE = '\x1b[2K'
		sys.stdout.write(CURSOR_UP_ONE)
		sys.stdout.write(ERASE_LINE)

	# The main function.
	def sync_blocks(self):
		# To do: implement binary search to take `month` as an argument and find the first and last
		# block of that month.
		for bn in range(3414260, 3851275):
			self.process_block(bn)

			# This can be slow, so tell us that we're actually making progress.
			if bn % 100 == 0:
				print('At block: {:,}'.format(bn))
				self.erase_line()

			# Every 3 days worth of blocks, log all the block numbers with payouts. This makes the
			# console a bit messy, but Sidecar/Kusama node has a bug causing it to fail sometimes
			# in certain ranges of blocks and requires a restart. Having regular updates helps you
			# bypass the time consuming searching of every block.
			if bn % (14400*3) == 0:
				print('Payout blocks: {}'.format(self.payout_blocks))

		# Total up the payouts at the end.
		self.total_payouts()

if __name__ == '__main__':
	# Load in addresses that we care about.
	# Must be a file with addresses as keys and a value that includes the spec name. E.g.:
	# {
	#   "address 1": "kusama-stash",
	#   "address 2": "polkadot-stash",
	#   "address 3": "polkadot-controller"
	# }
	with open('./addresses_stash.json', mode='r') as address_file:
		addresses = json.loads(address_file.read())
	
	p = StakingRewardsLogger(addresses)
	p.sync_blocks()
