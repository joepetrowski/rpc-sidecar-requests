#%%
import requests
import json

block = 2621327
address = 'GTUi6r2LEsf71zEQDnBvBvKskQcWvK66KRqcRbdmcczaadr'
sidecar_url = 'http://127.0.0.1:8080/'

def get_block(sidecar: str, block: int):
	block_data = {}
	url = sidecar + 'block/' + str(block)
	response = requests.get(url)
	if response.ok:
		block_data = json.loads(response.text)
	return block_data

def get_balance(sidecar: str, address: str, block: int):
	balance = {}
	url = sidecar + 'balance/' + address + '/' + str(block)
	response = requests.get(url)
	if response.ok:
		balance = json.loads(response.text)
	return balance

def is_signed_by(signature, address):
	return signature and signature['signer'] == address

def get_fees_paid_in_block(block: dict, address: str):
	total_fees = 0
	for xt in block['extrinsics']:
		if is_signed_by(xt['signature'], address):
			if xt['paysFee']:
				fee = int(xt['info']['partialFee'])
				total_fees += fee
	return total_fees

def value_deducted_in_block(block: dict, address: str):
	transfer_methods = [
		'balances.transfer',
		'balances.transferKeepAlive',
		'vesting.vestedTransfer'
	]
	value_transferred = 0
	for xt in block['extrinsics']:
		if is_signed_by(xt['signature'], address):
			if xt['method'] in transfer_methods:
				value = int(xt['args'][1])
				value_transferred += value
		value_transferred += value_reaped(xt['events'])
	return value_transferred

# Add function for value received.
def value_credited_in_block(block: dict, address: str):
	credit = 0
	for xt in block['extrinsics']:
		for event in xt['events']:
			if event['method'] == 'balances.Deposit' and event['data'][0] == address:
				credit += int(event['data'][1])
	return credit

def value_reaped(events):
	reaped = 0
	for event in events:
		# Add check to make sure it's the address we're concerned with.
		if event['method'] == 'balances.DustLost':
			reaped += int(event['data'][1])
	return reaped

balances_before_tx = get_balance(sidecar_url, address, block-1)
balances_after_tx = get_balance(sidecar_url, address, block)
block_data = get_block(sidecar_url, block)

pre_tx_free_balance = int(balances_before_tx['free'])
pre_tx_reserved_balance = int(balances_before_tx['reserved'])
pre_tx_total_balance = pre_tx_free_balance + pre_tx_reserved_balance
post_tx_free_balance = int(balances_after_tx['free'])
post_tx_reserved_balance = int(balances_after_tx['reserved'])
post_tx_total_balance = post_tx_free_balance + post_tx_reserved_balance

transfer_value = value_deducted_in_block(block_data, address)
credit = value_credited_in_block(block_data, address)
fee = get_fees_paid_in_block(block_data, address)

expected = pre_tx_total_balance - transfer_value - fee + credit

print('Block {}'.format(block))
print('Address: {}'.format(address))
print('Actual Balance:   {:>14}'.format(post_tx_total_balance))
print('Expected Balance: {:>14}'.format(expected))
print('              ------------------')
print('Difference:       {:>14}'.format(post_tx_total_balance - expected))
