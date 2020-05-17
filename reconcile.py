#%%
import requests
import json

block = 2349757
address = '<enter address here>'
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

def get_fees_paid_in_block(block: dict, address: str):
	total_fees = 0
	for xt in block['extrinsics']:
		if xt['signature'] and xt['signature']['signer'] == address:
			if xt['paysFee']:
				fee = int(xt['info']['partialFee'])
				total_fees += fee
	return total_fees

def value_transferred_in_block(block: dict, address: str):
	value_transferred = 0
	for xt in block['extrinsics']:
		if xt['signature'] and xt['signature']['signer'] == address:
			if xt['method'] == 'balances.transferKeepAlive' or xt['method'] == 'balances.transfer':
				value = int(xt['args'][1])
				value_transferred += value
		value_transferred += value_reaped(xt['events'])
	return value_transferred

def value_reaped(events):
	reaped = 0
	for event in events:
		if event['method'] == 'balances.DustLost':
			reaped += int(event['data'][1])
	return reaped

balances_before_tx = get_balance(sidecar_url, address, block-1)
balances_after_tx = get_balance(sidecar_url, address, block+1)
block_data = get_block(sidecar_url, block)

pre_tx_balance = int(balances_before_tx['free'])
post_tx_balance = int(balances_after_tx['free'])
transfer_value = value_transferred_in_block(block_data, address)
fee = get_fees_paid_in_block(block_data, address)

expected = pre_tx_balance - transfer_value - fee

#%%
print('Actual Balance:   {:>14}'.format(post_tx_balance))
print('Expected Balance: {:>14}'.format(expected))
print('              ------------------')
print('Difference:       {:>14}'.format(post_tx_balance - expected))
