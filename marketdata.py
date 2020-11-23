
#%%
from pycoingecko import CoinGeckoAPI
import numpy as np

cg = CoinGeckoAPI()

coin_id = 'polkadot'

history = cg.get_coin_market_chart_by_id(coin_id, 'USD', 40)

volumes = []
for day in history['total_volumes']:
	volumes.append(day[1])
m = np.mean(volumes)
print('Average Daily Volume: {:,.2f} USD'.format(m))
