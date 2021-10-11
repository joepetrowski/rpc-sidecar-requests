import sys
import json
import os.path
from sidecar import Sidecar
import argparse

class SaveBlocks(Sidecar):
	def __init__(self, inputs):
		# APIs
		super().__init__(inputs['endpoint'])

		# Inputs
		self.start_block = inputs['start_block']
		self.end_block = inputs['end_block']
		self.datadir = inputs['datadir']

		self.network = self.get_chain_spec()
		
		# Create storage directory if it doesn't exist yet
		if not os.path.isdir('{}/{}'.format(self.datadir, self.network)):
			os.makedirs('{}/{}'.format(self.datadir, self.network))

	# Get chain spec name.
	def get_chain_spec(self):
		spec_info = self.runtime_spec()
		return spec_info['specName']

	# Get the block number of the latest finalized block.
	def get_chain_tip(self):
		latest_block = self.blocks()
		chain_height = int(latest_block['number'])
		return chain_height

	def fetch_block(self, block_requested: int):
		fname = '{}/{}/block-{}.json'.format(self.datadir, self.network, block_requested)
		# Just in case we have it already. If we don't, fetch it.
		if not os.path.isfile(fname):
			# fetch the block from sidecar
			block = self.blocks(block_requested)
			if 'error' not in block.keys():
				with open(fname, 'w') as f:
					json.dump(block, f, indent=2)

	def erase_line(self):
		CURSOR_UP_ONE = '\x1b[1A'
		ERASE_LINE = '\x1b[2K'
		sys.stdout.write(CURSOR_UP_ONE)
		sys.stdout.write(ERASE_LINE)

	def look_up_block_range(self):
		# Calculate start block
		if self.start_block >= 0:
			start_block = self.start_block
		else:
			highest = 0
			# Find the last block we have
			for _, _, files in os.walk('{}/{}'.format(self.datadir, self.network)):
				for name in files:
					bn = name[6:]
					bn = bn[:-5]
					highest = max(highest, int(bn))
			start_block = highest
		
		# Calculate end block
		if self.end_block >= 0:
			end_block = self.end_block
		else:
			end_block = self.get_chain_tip()
		
		if end_block < start_block:
			print('End block is lower than start block. Your node is probably not synced.')
			print('Start block: {:,}'.format(start_block))
			print('End block:   {:,}'.format(end_block))
			sys.exit()
		
		print('Collecting info from block {} to {}\n'.format(start_block, end_block))
		return start_block, end_block

	# The main function.
	def sync_blocks(self):
		start, end = self.look_up_block_range()
		for bn in range(start, end):
			self.fetch_block(bn)

			# This can be slow, so tell us that we're actually making progress.
			if bn % 100 == 0:
				print('At block: {:,}'.format(bn))
				self.erase_line()

def parse_args():
	parser = argparse.ArgumentParser()

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
		'--datadir',
		help='Directory in which to save blocks.',
		type=str,
		default='/home/joe/parity/sideprojects/rpc-sidecar-requests/blocks'
	)

	args = parser.parse_args()

	input_args = {
		'start_block': int(args.startblock),
		'end_block': int(args.endblock),
		'endpoint': args.sidecar,
		'datadir' : args.datadir,
	}
	return input_args

if __name__ == '__main__':
	input_args = parse_args()
	p = SaveBlocks(input_args)
	p.sync_blocks()
