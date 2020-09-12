#%%
# Example
from sidecar import Sidecar

url = 'http://127.0.0.1:8080'
s = Sidecar(url)

artifacts = s.transaction_material()

print('\nBlock Number: {}'.format(int(artifacts['at']['height'])))
print('\nBlock Hash:   {}'.format(artifacts['at']['hash']))
print('\nSpec Version: {}'.format(artifacts['specVersion']))
print('\nTx Version:   {}'.format(artifacts['txVersion']))
print('\nGenesis Hash: {}'.format(artifacts['genesisHash']))
