import sys
import os
import hashlib

UNIT = 100000000        # The same across currencies.

UNITTEST_PREFIX = b'TESTXXXX'

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

ISSUANCE_FEE = 5
TWO_WEEKS = 2 * 7 * 24 * 3600
MAX_EXPIRATION = 4 * 2016   # Two months

# SQLite3
MAX_INT = 2**63 - 1

# Order fees
FEE_REQUIRED_DEFAULT = .01   # 1%
FEE_PROVIDED_DEFAULT = .01   # 1%
