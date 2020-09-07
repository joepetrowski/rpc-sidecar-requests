#%%
from sidecar import Sidecar

decimals = 1e10
url = 'http://127.0.0.1:8080'
s = Sidecar(url)

address = ''
bal = s.balance(address)
free = int(bal['free'])
reserved = int(bal['reserved'])
spendable = free - max(int(bal['feeFrozen']), int(bal['miscFrozen']))
print('\nAddress: {}'.format(address))
print('Block: {}'.format(bal['at']['height']))
print('Free: {:,}'.format(free / decimals))
print('Reserved: {:,}'.format(reserved / decimals))
print('Spendable: {:,}'.format(spendable / decimals))
