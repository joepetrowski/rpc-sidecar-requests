#%%
from sidecar import Sidecar

url = 'http://127.0.0.1:8080'

s = Sidecar(url)

staker = s.account_staking_info('14Kaq4ZBY3Rc1HUz9aoi897si9GnKsufXRTRH8je5x4wCwgb')

# staking = s.staking_progress()
# print('At: {}'.format(staking['at']['height']))
# print('Next Session: {}'.format(staking['nextSessionEstimate']))
# print('Next ActiveEra: {}'.format(staking['nextActiveEraEstimate']))
# print('Election Status: {}\n'.format(staking['electionStatus']))
