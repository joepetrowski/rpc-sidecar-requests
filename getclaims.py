#%%
# Example
import requests
import json
from sidecar import Sidecar

url = 'http://127.0.0.1:8080'

sidecar = Sidecar(url)

claims = sidecar.claims('')
