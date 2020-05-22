#%%
# Example
import requests
import json
from sidecar import Sidecar

url = 'http://127.0.0.1:8080'
sidecar = Sidecar(url)

artifacts = sidecar.artifacts()

print('\nBlock Number: {}'.format(hex(int(artifacts['at']['height']))))
print('\nBlock Hash:   {}'.format(artifacts['at']['hash']))
print('\nSpec Version: {}'.format(artifacts['specVersion']))
print('\nTx Version:   {}'.format(artifacts['txVersion']))
print('\nGenesis Hash: {}'.format(artifacts['genesisHash']))
