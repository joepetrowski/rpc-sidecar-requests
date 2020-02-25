#%% Imports
import requests
import json

responses = []
max_block = 775_001

base_url = 'http://127.0.0.1:8080'
path = 'block'

for block in range(0, max_block):
	response = requests.get(base_url + '/' + path + '/' + str(block))
	if response.ok:
		response_text = response.text
		response_json = json.loads(response_text)
		
		assert(response_json['number'] == block)
		responses.append(response_json)

		if response_json['number'] % 1000 == 0:
			print(
				'Block {:>9,} has state root {}'
				.format(response_json['number'], response_json['stateRoot'])
			)
	else:
		print('Error: {}'.format(response.status_code))
