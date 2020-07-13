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
