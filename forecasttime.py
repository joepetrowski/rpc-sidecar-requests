#%%
from sidecar import Sidecar
from datetime import datetime

transfers = 1_205_128
redenom = 1_248_328
block_to_forecast = 1405683

s = Sidecar('http://127.0.0.1:8080')

latest_block = s.block()

# Get the UNIX time of a block.
def get_block_time(block: dict):
	ts = 0
	for xt in block['extrinsics']:
		if xt['method'] == 'timestamp.set':
			# Block timestamp is in _milliseconds_ since epoch
			ts = int(xt['args']['now']) / 1000
			break
	if ts == 0:
		print('No time set for block {}'.format(block['number']))
	return ts

latest_block_number = int(latest_block['number'])
latest_block_unixt = get_block_time(latest_block)

block_time = 6
block_time_slip = block_time * 1.004 # about 0.4% of slots are missed

earliest_block_time = (block_to_forecast - latest_block_number) * block_time + latest_block_unixt
earliest_block_time_formatted = datetime.utcfromtimestamp(earliest_block_time).strftime('%Y-%m-%d %H:%M:%S')
print('Earliest Time: {}'.format(earliest_block_time_formatted))

estimated_block_time = (block_to_forecast - latest_block_number) * block_time_slip + latest_block_unixt
estimated_block_time_formatted = datetime.utcfromtimestamp(estimated_block_time).strftime('%Y-%m-%d %H:%M:%S')
print('Estimated Time: {}'.format(estimated_block_time_formatted))
