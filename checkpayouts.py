#%%
from sidecar import Sidecar
import json

url = 'http://127.0.0.1:8080'
s = Sidecar(url)

depth = 7 # supports up to 84

# Must provide a file named 'addresses_stash.json' with addresses as keys and a value that includes
# the spec name. E.g.:
# {
#   "address 1": "kusama-stash",
#   "address 2": "polkadot-stash"
# }

def get_chain_info():
	chain_info = s.runtime_spec()
	chain = chain_info['specName']
	if chain == 'polkadot':
		token = 'DOT'
		decimals = 1e10
	elif chain == 'kusama':
		token = 'KSM'
		decimals = 1e12
	return chain, token, decimals

def process_eras(payouts, decimals):
	payout = 0
	for era in payouts['erasPayouts']:
		if era['payouts']:
			for p in era['payouts']:
				if not p['claimed']:
					nom_payout = int(p['nominatorStakingPayout'])
					payout += nom_payout
					print('Era {}: {} unclaimed'.format(era['era'], nom_payout/decimals))
	return payout

def get_addresses(addresses, chain):
	# Only check addresses from the right chain.
	addresses_to_check = []
	for address in addresses:
		if chain in addresses[address]:
			addresses_to_check.append(address)
	return addresses_to_check

def process_addresses(addresses, decimals, token):
	for a in addresses:
		payouts = s.account_staking_payouts(a, depth)
		payout = process_eras(payouts, decimals)
		print('Total unclaimed for {}: {} {}'.format(a, payout / decimals, token))

def main():
	with open('./addresses_stash.json', mode='r') as address_file:
		all_addresses = json.loads(address_file.read())
	chain, token, decimals = get_chain_info()
	addresses = get_addresses(all_addresses, chain)
	process_addresses(addresses, decimals, token)

main()
