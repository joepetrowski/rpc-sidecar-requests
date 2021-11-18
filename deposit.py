import argparse
import sys

class ArgParser():
	def __init__(self) -> None:
		pass

	def parse_args(self):
		parser = argparse.ArgumentParser()
		parser.add_argument(
			'-n', '--network',
			help='Polkadot or Kusama',
			type=str,
			required=True
		)
		parser.add_argument(
			'-i', '--items',
			help='Number of items.',
			type=str,
			required=True
		)
		parser.add_argument(
			'-b', '--bytes',
			help='Number of bytes.',
			type=str,
			required=True
		)
		args = parser.parse_args()

		return {
			'network': args.network,
			'items': int(args.items),
			'bytes': int(args.bytes),
		}

''' POLKADOT
/// Money matters.
pub mod currency {
	use primitives::v0::Balance;

	pub const UNITS: Balance = 10_000_000_000;
	pub const DOLLARS: Balance = UNITS; // 10_000_000_000
	pub const CENTS: Balance = DOLLARS / 100; // 100_000_000
	pub const MILLICENTS: Balance = CENTS / 1_000; // 100_000

	pub const fn deposit(items: u32, bytes: u32) -> Balance {
		items as Balance * 20 * DOLLARS + (bytes as Balance) * 100 * MILLICENTS
	}
}
'''

class Polkadot:
	def __init__(self) -> None:
		self.UNITS: int = 10_000_000_000
		self.DOLLARS: int = self.UNITS
		self.CENTS: int = self.DOLLARS / 100
		self.MILLICENTS: int = self.CENTS / 1_000

	def deposit(self, items: int, bytes: int):
		return int(items * 20 * self.DOLLARS + bytes * 100 * self.MILLICENTS)

''' KUSAMA
/// Money matters.
pub mod currency {
	use primitives::v0::Balance;

	pub const UNITS: Balance = 1_000_000_000_000;
	pub const CENTS: Balance = UNITS / 30_000;
	pub const GRAND: Balance = CENTS * 100_000;
	pub const MILLICENTS: Balance = CENTS / 1_000;

	pub const fn deposit(items: u32, bytes: u32) -> Balance {
		items as Balance * 2_000 * CENTS + (bytes as Balance) * 100 * MILLICENTS
	}
}
'''

class Kusama:
	def __init__(self) -> None:
		self.UNITS: int = 1_000_000_000_000
		self.CENTS: int = self.UNITS / 30_000
		self.GRAND: int = self.CENTS * 100_000
		self.MILLICENTS: int = self.CENTS / 1_000

	def deposit(self, items: int, bytes: int):
		return int(items * 2_000 * self.CENTS + bytes * 100 * self.MILLICENTS)

if __name__ == '__main__':
	input_args = ArgParser().parse_args()
	if input_args['network'] == 'polkadot':
		n = Polkadot()
		decimals = 10
		currency = 'DOT'
	elif input_args['network'] == 'kusama':
		n = Kusama()
		decimals = 12
		currency = 'KSM'
	else:
		print('Network not supported.')
		sys.exit()
	
	deposit = n.deposit(input_args['items'], input_args['bytes']) / (10 ** decimals)
	print('Deposit: {} {}'.format(deposit, currency))
