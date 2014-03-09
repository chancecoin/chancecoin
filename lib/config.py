import sys
import os
import hashlib

UNIT = 100000000        # The same across currencies.

UNITTEST_PREFIX = b'TESTXXXX'
BITCOIND_RPC_PORT_LIVE = '8332'
BITCOIND_RPC_PORT_TESTNET = '18332'
RPC_PORT_TESTNET = '14000'
RPC_PORT_LIVE = '4000'
BITCOIND_RPC_CONNECT = 'localhost'
BITCOIND_RPC_USER = 'bitcoinrpc'
RPC_USER = 'rpc'
TESTNET = False
TESTCOIN = False
PREFIX_TESTCOIN = b'CH'
PREFIX_LIVECOIN = b'CHANCECO'
CONFIG_FILENAME = 'chancecoin.conf'
DATA_DIR_TESTNET = 'chancecoind.testnet.log'
DATA_DIR_LIVE = 'chancecoin.log'
DATABASE_NAME_PREFIX = 'chancecoin'
UNSPENDABLE_TESTNET_TESTCOIN = 'mvChancecoinXXXXXXXXXXXXXXXXW24Hef'
UNSPENDABLE_TESTNET_LIVECOIN = 'mvChancecoinXXXXXXXXXXXXXXXXW24Hef'
UNSPENDABLE_LIVE_TESTCOIN = '1CHANCEXXXXXXXXXXXXXXXTbBGJ2'
UNSPENDABLE_LIVE_LIVECOIN = '1CHANCEXXXXXXXXXXXXXXXTbBGJ2'
API_LOG = 'api.error.log'

# Versions
CLIENT_VERSION_MAJOR = 6
CLIENT_VERSION_MINOR = 0
CLIENT_VERSION = float(str(CLIENT_VERSION_MAJOR) + '.' + str(CLIENT_VERSION_MINOR))
DB_VERSION_MAJOR = 7        # Major version changes the blocks or transactions table.
DB_VERSION_MINOR = 0        # Minor version changes just the parsing.
DB_VERSION = float(str(DB_VERSION_MAJOR) + '.' + str(DB_VERSION_MINOR))

# Bitcoin protocol
# DUST_SIZE = 5430      # OP_RETURN
DUST_SIZE = 5430 * 2    # Multi‐sig (TODO: This is just a guess.)
MIN_FEE = 10000         # Chancecoin transactions are all under 1KB in size.
DATA_VALUE = 0

# Chancecoin protocol
TXTYPE_FORMAT = '>I'

TWO_WEEKS = 2 * 7 * 24 * 3600
MAX_EXPIRATION = 4 * 2016   # Two months

# SQLite3
MAX_INT = 2**63 - 1

# Order fees
FEE_REQUIRED_DEFAULT = .01   # 1%
FEE_PROVIDED_DEFAULT = .01   # 1%