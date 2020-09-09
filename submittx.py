#%%
from sidecar import Sidecar

url = 'http://127.0.0.1:8080'
s = Sidecar(url)

tx = '0xc0ffee...'

tx_response = s.transaction(tx)
print(tx_response)
