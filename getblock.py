#%%
# Example
import requests
import json
from sidecar import Sidecar

url = 'http://127.0.0.1:8080'

sidecar = Sidecar(url)

block = sidecar.block(188889)

# CC1 Interesting Blocks
# 28831 - Sudo setKey (0 -> 1)
# 29231 - sudo.sudoUncheckedWeight (runtime upgrade v2)
# 29242 - sudo.setKey (1 -> 0)
# 29258 - sudo.sudo(forceTransfer)
# 188836 - sudo.sudoUncheckedWeight (runtime upgrade v5)
# 188889 - add proxy for sudo
# 188902 - sudo.sudo(kill account)
