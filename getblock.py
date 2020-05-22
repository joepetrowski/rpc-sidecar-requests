#%%
# Example
import requests
import json
from sidecar import Sidecar

url = 'http://127.0.0.1:8080'
# url = 'https://cb-runtime-wk8yx7pds0ag.paritytech.net/block/540'

sidecar = Sidecar(url)

block = sidecar.block(1184728)
