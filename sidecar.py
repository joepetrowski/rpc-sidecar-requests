import requests
import json
import time

class Sidecar:
	# Where is the sidecar.
	def __init__(self, endpoint):
		if endpoint[-1] != '/':
			endpoint = endpoint + '/'
		self.endpoint = endpoint

	# Construct a path to some sidecar info.
	def construct_url(self, path=None, param1=None, param2=None):
		url = self.endpoint
		if path:
			url = url + str(path)
			if param1 or param1 == 0:
				url = url + '/' + str(param1)
				if param2 or param2 == 0:
					url = url + '/' + str(param2)
		return url

	# Request some data from sidecar.
	def sidecar_get(self, endpoint):
		try:
			response = requests.get(endpoint)
		except:
			print('Unable to connect to sidecar.')

		return self.process_response(response)

	# Post some data to the sidecar.
	def sidecar_post(self, endpoint, post_data):
		tx_headers = {'Content-type' : 'application/json'}
		try:
			response = requests.post(
				endpoint,
				data=post_data,
				headers=tx_headers
			)
		except:
			print('Unable to connect to sidecar.')

		return self.process_response(response)

	# Process HTTP response.
	def process_response(self, response):
		data = {}
		if response and response.ok:
			data = json.loads(response.text)
		else:
			error_message = 'Response Error: {}'.format(response.status_code)
			print(error_message)
			data = { 'error' : error_message }
		return data

	def custom(self, route=''):
		path = self.endpoint + route
		return self.sidecar_get(path)

	# v1 paths

	def account_staking_info(self, address, block=None):
		path = '{}accounts/{}/staking-info'.format(self.endpoint, address)
		if block:
			path += '?at={}'.format(block)
		return self.sidecar_get(path)

	def account_staking_payouts(self, address, depth=1, era=None, unclaimed_only=None):
		path = '{}accounts/{}/staking-payouts?depth={}'.format(self.endpoint, address, depth)
		if era:
			path += '&era='.format(era)
		if unclaimed_only:
			path += '&unclaimedOnly='.format(unclaimed_only)
		return self.sidecar_get(path)

	def account_balance_info(self, address, block=None):
		path = '{}accounts/{}/balance-info'.format(self.endpoint, address)
		if block:
			path += '?at={}'.format(block)
		return self.sidecar_get(path)

	def account_vesting_info(self, address, block=None):
		path = '{}accounts/{}/vesting-info'.format(self.endpoint, address)
		if block:
			path += '?at={}'.format(block)
		return self.sidecar_get(path)

	def blocks(self, block='head'):
		path = '{}blocks/{}'.format(self.endpoint, block)
		return self.sidecar_get(path)

	def staking_progress(self, block=None):
		path = '{}pallets/staking/progress'.format(self.endpoint)
		if block:
			path += '?at={}'.format(block)
		return self.sidecar_get(path)

	def node_network(self):
		path = '{}node/network'.format(self.endpoint)
		return self.sidecar_get(path)

	def node_transaction_pool(self):
		path = '{}node/transaction-pool'.format(self.endpoint)
		return self.sidecar_get(path)

	def runtime_spec(self, block=None):
		path = '{}runtime/spec'.format(self.endpoint)
		if block:
			path += '?at={}'.format(block)
		return self.sidecar_get(path)

	def runtime_code(self, block=None):
		path = '{}runtime/code'.format(self.endpoint)
		if block:
			path += '?at={}'.format(block)
		return self.sidecar_get(path)

	def runtime_metadata(self, block=None):
		path = '{}runtime/metadata'.format(self.endpoint)
		if block:
			path += '?at={}'.format(block)
		return self.sidecar_get(path)

	def transaction(self, transaction):
		path = '{}transaction/material'.format(self.endpoint)
		tx_data = '{"tx": "{}"}'.format(transaction)
		return self.sidecar_post(path, tx_data)

	def transaction_material(self, block=None, noMeta=False):
		path = '{}transaction/material'.format(self.endpoint)
		if block and noMeta:
			path += '?at={}&noMeta=true'.format(block)
		elif block:
			path += '?at={}'.format(block)
		elif noMeta:
			path += '?noMeta=true'
		return self.sidecar_get(path)

	def transaction_fee_estimate(self):
		pass

	def transaction_dry_run(self):
		pass

	# v0 paths

	def block(self, block_number=None):
		path = self.construct_url('block', block_number)
		return self.sidecar_get(path)

	def balance(self, address, block_number=None):
		path = self.construct_url('balance', address, block_number)
		return self.sidecar_get(path)

	def payout(self, address, block_number=None):
		path = self.construct_url('payout', address, block_number)
		return self.sidecar_get(path)

	def staking(self, address, block_number=None):
		path = self.construct_url('staking', address, block_number)
		return self.sidecar_get(path)

	def staking_info(self, block_number=None):
		path = self.construct_url('staking-info', block_number)
		return self.sidecar_get(path)

	def vesting(self, address, block_number=None):
		path = self.construct_url('vesting', address, block_number)
		return self.sidecar_get(path)

	def metadata(self, block_number=None):
		path = self.construct_url('metadata', block_number)
		return self.sidecar_get(path)

	def claims(self, address, block_number=None):
		path = self.construct_url('claims', address, block_number)
		return self.sidecar_get(path)

	def artifacts(self, block_number=None):
		path = self.construct_url('tx', 'artifacts', block_number)
		return self.sidecar_get(path)

	def submit_tx(self, tx):
		path = self.construct_url('tx')
		tx_data = '{"tx": "{}"}'.format(tx_data)
		return self.sidecar_post(path, tx_data)

if __name__ == "__main__":
	sidecar = Sidecar('http://127.0.0.1:8080/')
	latest_block = sidecar.block()
	if 'number' in latest_block.keys():
		print('Connected to Sidecar! Current block height is {:,}'
			.format(int(latest_block['number'])))
	else:
		print(latest_block)
