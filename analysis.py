#%% 
# Useful functions for dealing with block data.

import json

# Write blocks with duplicate extrinsics to files.
write = False

# Import blocks from a data file.
def import_blocks(fname):
	with open(fname, 'r') as f:
		blocks = json.load(f)
	return blocks

# Check a single block that has two copies of the same extrinsic.
# Will write an output file of the entire block in JSON format.
def check_for_double_xt(block_info: dict, write: bool):
	assert(type(block_info) == dict)
	doubles = []
	if 'extrinsics' in block_info.keys():
		xts = block_info['extrinsics']
		assert(type(xts) == list)
		xt_len = len(xts)
		for ii in range(0, xt_len):
			for jj in range(0, ii):
				if xts[ii]['hash'] == xts[jj]['hash'] \
				and (xts[ii]['hash'], block_info['number']) not in doubles \
				and ii != jj:
					print(
						'Warn! Block {} has duplicate extrinsics. Hash: {}'.format(
							block_info['number'],
							xts[ii]['hash']
						)
					)
					doubles.append((xts[ii]['hash'], block_info['number']))
					if write:
						write_block_to_file(block_info, 'duplicate-xt', xts[ii]['hash'])
	else:
		print('Block {} has no extrinsics.'.format(block_info['number']))
	return doubles

# Check a list of blocks for duplicate extrinsics.
# Returns a list of tuples, (transaction_hash, block_number).
def check_blocks_for_double_xt(blocks: list, write: bool):
	doubles= []
	for block in blocks:
		block_doubles = check_for_double_xt(block, write)
		doubles.extend(block_doubles)
	return doubles

# Write a single block to an output file in JSON format.
def write_block_to_file(block: dict, reason='info', txhash='0x00'):
	fname = 'blocks/block-{}-{}-{}.json'.format(
		block['number'],
		reason,
		str(txhash)
	)
	with open(fname, 'w') as f:
		json.dump(block, f, indent=4)

# Checks a list of transactions that have shown up as duplicates to see if these
# transactions also show up as duplicates in other blocks. Expects a list of tuples
# of the form (transaction_hash, block_number).
#
# Will return a dictionary with transaction hash as the keys and, for each one, a
# list of blocks in which this transaction was included multiple times.
#
# Note: Only finds transactions that were duplicated in multiple blocks. As in, if
# a transaction was duplicated in block 100 and appeared again only once in block
# 105, it will not find that.
def duplicates_in_many_blocks(doubles: list):
	length_doubles = len(doubles)
	many_block_txs = {}
	for ii in range(0, length_doubles):
		for jj in range(0, ii):
			if doubles[ii][0] == doubles[jj][0] and ii != jj:
				if doubles[ii][0] not in many_block_txs.keys():
					many_block_txs[doubles[ii][0]] = [doubles[ii][1], doubles[ii][1]]
				else:
					if doubles[jj][1] not in many_block_txs[doubles[ii][0]]:
						many_block_txs[doubles[ii][0]].append(doubles[jj][1])
					if doubles[ii][1] not in many_block_txs[doubles[ii][0]]:
						many_block_txs[doubles[ii][0]].append(doubles[ii][1])
		if ii % 1000 == 0:
			print('At list item {}'.format(ii))
	return many_block_txs

if __name__ == "__main__":
	blocks = import_blocks('blocks.data')
	doubles = check_blocks_for_double_xt(blocks, write) # List of (txHash, blockNumber)

	check_block_duplicates = input(
		'Do you want to check for duplicates in multiple blocks? Warning, this takes a long time. (y/N) '
	)

	if check_block_duplicates.lower() == 'y':
		many_block_txs = duplicates_in_many_blocks(doubles)
