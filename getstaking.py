#%%
from sidecar import Sidecar

url = 'http://127.0.0.1:8080'

sidecar = Sidecar(url)

# staker = sidecar.staking('')

staking = sidecar.staking_info()
print('At: {}'.format(staking['at']['height']))
print('Next Session: {}'.format(staking['nextSessionEstimate']))
print('Next ActiveEra: {}'.format(staking['nextActiveEraEstimate']))
print('Election Status: {}\n'.format(staking['electionStatus']))
