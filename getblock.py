#%%
# Example
from sidecar import Sidecar
import numpy as np

url = 'http://127.0.0.1:8080'
s = Sidecar(url)

block = s.blocks(1948992)

# xts = [0]
# idx = 0
# for bn in range(2000000-144000, 2000000):
# 	block = s.blocks(bn)
# 	if bn % 600 == 0:
# 		idx += 1
# 		xts.append(0)
# 		print('{} txs in last hour... now at block {}'.format(xts[-2], bn))
# 	if 'extrinsics' in block:
# 		xts[idx] += len(block['extrinsics'])

# average_per_hour = np.mean(xts[1:-2])
# print('\nAverage Transactions per Hour: {}\n'.format(average_per_hour))
