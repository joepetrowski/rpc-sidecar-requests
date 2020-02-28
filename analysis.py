#%% 
# Useful functions for dealing with block data.

import json

def import_blocks(fname):
	with open(fname, 'r') as f:
		blocks = json.load(fname)
	return blocks
