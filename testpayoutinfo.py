#%%
from sidecar import Sidecar

s = Sidecar('http://127.0.0.1:8080')

# Stash address of interest. Can be nominator or validator.
stash = '1A2ATy1FEu5yQ9ZzghPLsRckPQ7XLmq5MJQYcTvGnxGvCho'
# Era to check payout for.
era = 82
# Known Polkadot block with payout_stakers where era was paid out.
bn = 1287330

payout_info = s.custom(
	'accounts/' + \
	stash + \
	'/staking-payouts?era=' + \
	str(era) + \
	'&depth=1&unclaimedOnly=false'
)

# Calculate payouts for an `address` from an array of `events`.
def calc_payouts(events, address):
	total_payout = 0
	for event in events:
		if event['method'] == 'staking.Reward' and event['data'][0] == stash:
			total_payout += int(event['data'][1])
	return total_payout

# Fetch and calculate the total amount of payouts for an address in a particular block.
payout_block = s.block(bn)
for xt in payout_block['extrinsics']:
	if xt['method'] == 'staking.payoutStakers' and xt['args']['validator_stash'] == stash:
		print('Validator Stash: {}'.format(xt['args']['validator_stash']))
		print('Era: {}'.format(xt['args']['era']))
		total_payout = calc_payouts(xt['events'], stash)
	if xt['method'] == 'utility.batch':
		for call in xt['args']['calls']:
			if call['method'] == 'staking.payoutStakers' and call['args']['validator_stash'] == stash:
				print('Validator Stash: {}'.format(call['args']['validator_stash']))
				print('Era: {}'.format(call['args']['era']))
		total_payout = calc_payouts(xt['events'], stash)

# Isolate and retrieve the estimated payout for `stash` in `era`.
total_estimated_payout = 0
for e in payout_info['erasPayouts']:
	this_era = int(e['era'])
	print('Era: {}'.format(this_era))
	for payout in e['payouts']:
		this_reward = int(payout['nominatorStakingPayout'])
		print('Reward Estimate: {}'.format(this_reward))
		total_estimated_payout += this_reward

print('Total Paid Out:   {}'.format(total_payout))

# Check if the estimate (from `payout-info`) matches the actual (from the block).
diff = total_payout - total_estimated_payout
print('Difference: {}'.format(diff))
