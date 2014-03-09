#! /usr/bin/env python3


import os
import argparse
import json

import decimal
D = decimal.Decimal

import sys
import logging
import requests
from prettytable import PrettyTable
import unicodedata

import time
import dateutil.parser
import calendar
from threading import Thread

import appdirs
import logging
import configparser

# Units
from lib import (config, api, util, exceptions, bitcoin, blocks)
from lib import (send, order, btcpay, bet, burn, cancel)
if os.name == 'nt':
    from lib import util_windows

json_print = lambda x: print(json.dumps(x, sort_keys=True, indent=4))

def set_options (data_dir=None, bitcoind_rpc_connect=None, bitcoind_rpc_port=None,
                 bitcoind_rpc_user=None, bitcoind_rpc_password=None, rpc_host=None, rpc_port=None,
                 rpc_user=None, rpc_password=None, log_file=None, database_file=None, testnet=False, testcoin=False, unittest=False, headless=False):

    # Unittests always run on testnet.
    if unittest and not testnet:
        raise Exception # TODO

    # Data directory
    if not data_dir:
        config.DATA_DIR = appdirs.user_data_dir(appauthor='Chancecoin', appname='chancecoin', roaming=True)
    else:
        config.DATA_DIR = data_dir
    if not os.path.isdir(config.DATA_DIR): os.mkdir(config.DATA_DIR)

    # Configuration file
    configfile = configparser.ConfigParser()
    config_path = os.path.join(config.DATA_DIR, config.CONFIG_FILENAME)
    configfile.read(config_path)
    has_config = 'Default' in configfile
    #logging.debug("Config file: %s; Exists: %s" % (config_path, "Yes" if has_config else "No"))

    # testnet
    if testnet:
        config.TESTNET = testnet
    elif has_config and 'testnet' in configfile['Default']:
        config.TESTNET = configfile['Default'].getboolean('testnet')

    # testcoin
    if testcoin:
        config.TESTCOIN = testcoin
    elif has_config and 'testcoin' in configfile['Default']:
        config.TESTCOIN = configfile['Default'].getboolean('testcoin')

    # Bitcoind RPC host
    if bitcoind_rpc_connect:
        config.BITCOIND_RPC_CONNECT = bitcoind_rpc_connect
    elif has_config and 'bitcoind-rpc-connect' in configfile['Default'] and configfile['Default']['bitcoind-rpc-connect']:
        config.BITCOIND_RPC_CONNECT = configfile['Default']['bitcoind-rpc-connect']

    # Bitcoind RPC port
    if bitcoind_rpc_port:
        config.BITCOIND_RPC_PORT = bitcoind_rpc_port
    elif has_config and 'bitcoind-rpc-port' in configfile['Default'] and configfile['Default']['bitcoind-rpc-port']:
        config.BITCOIND_RPC_PORT = configfile['Default']['bitcoind-rpc-port']
    else:
        if config.TESTNET:
            config.BITCOIND_RPC_PORT = config.BITCOIND_RPC_PORT_TESTNET
        else:
            config.BITCOIND_RPC_PORT = config.BITCOIND_RPC_PORT_LIVE
    try:
        int(config.BITCOIND_RPC_PORT)
        assert int(config.BITCOIND_RPC_PORT) > 1 and int(config.BITCOIND_RPC_PORT) < 65535
    except:
        raise Exception("Please specific a valid port number bitcoind-rpc-port configuration parameter")

    # Bitcoind RPC user
    if bitcoind_rpc_user:
        config.BITCOIND_RPC_USER = bitcoind_rpc_user
    elif has_config and 'bitcoind-rpc-user' in configfile['Default'] and configfile['Default']['bitcoind-rpc-user']:
        config.BITCOIND_RPC_USER = configfile['Default']['bitcoind-rpc-user']

    # Bitcoind RPC password
    if bitcoind_rpc_password:
        config.BITCOIND_RPC_PASSWORD = bitcoind_rpc_password
    elif has_config and 'bitcoind-rpc-password' in configfile['Default'] and configfile['Default']['bitcoind-rpc-password']:
        config.BITCOIND_RPC_PASSWORD = configfile['Default']['bitcoind-rpc-password']
    else:
        raise exceptions.ConfigurationError('bitcoind RPC password not set. (Use configuration file or --bitcoind-rpc-password=PASSWORD)')

    config.BITCOIND_RPC = 'http://' + config.BITCOIND_RPC_USER + ':' + config.BITCOIND_RPC_PASSWORD + '@' + config.BITCOIND_RPC_CONNECT + ':' + str(config.BITCOIND_RPC_PORT)

    # RPC host
    if rpc_host:
        config.RPC_HOST = rpc_host
    elif has_config and 'rpc-host' in configfile['Default'] and configfile['Default']['rpc-host']:
        config.RPC_HOST = configfile['Default']['rpc-host']

    # RPC port
    if rpc_port:
        config.RPC_PORT = rpc_port
    elif has_config and 'rpc-port' in configfile['Default'] and configfile['Default']['rpc-port']:
        config.RPC_PORT = configfile['Default']['rpc-port']
    else:
        if config.TESTNET:
            config.RPC_PORT = config.RPC_PORT_TESTNET
        else:
            config.RPC_PORT = config.RPC_PORT_LIVE
    try:
        int(config.RPC_PORT)
        assert int(config.RPC_PORT) > 1 and int(config.RPC_PORT) < 65535
    except:
        raise Exception("Please specific a valid port number rpc-port configuration parameter")

    # RPC user
    if rpc_user:
        config.RPC_USER = rpc_user
    elif has_config and 'rpc-user' in configfile['Default'] and configfile['Default']['rpc-user']:
        config.RPC_USER = configfile['Default']['rpc-user']

    # RPC password
    if rpc_password:
        config.RPC_PASSWORD = rpc_password
    elif has_config and 'rpc-password' in configfile['Default'] and configfile['Default']['rpc-password']:
        config.RPC_PASSWORD = configfile['Default']['rpc-password']
    else:
        raise exceptions.ConfigurationError('RPC password not set. (Use configuration file or --rpc-password=PASSWORD)')

    # Log
    if log_file:
        config.LOG = log_file
    elif has_config and 'logfile' in configfile['Default']:
        config.LOG = configfile['Default']['logfile']
    else:
        if config.TESTNET:
            config.LOG = os.path.join(config.DATA_DIR, config.DATA_DIR_TESTNET)
        else:
            config.LOG = os.path.join(config.DATA_DIR, config.DATA_DIR_LIVE)

    if not unittest:
        if config.TESTCOIN:
            config.PREFIX = config.PREFIX_TESTCOIN
        else:
            config.PREFIX = config.PREFIX_LIVECOIN
    else:
        config.PREFIX = config.UNITTEST_PREFIX

    # Database
    if config.TESTNET:
        config.DB_VERSION_MAJOR = str(config.DB_VERSION_MAJOR) + '.testnet'
    if database_file:
        config.DATABASE = database_file
    else:
        config.DB_VERSION_MAJOR
        config.DATABASE = os.path.join(config.DATA_DIR, config.DATABASE_NAME_PREFIX + '.' + str(config.DB_VERSION_MAJOR) + '.db')

    # (more) Testnet
    if config.TESTNET:
        if config.TESTCOIN:
            config.ADDRESSVERSION = b'\x6f'
            config.BLOCK_FIRST = 154908
            config.BURN_START = 154908
            config.BURN_END = 4017708
            config.UNSPENDABLE = config.UNSPENDABLE_TESTNET_TESTCOIN
        else:
            config.ADDRESSVERSION = b'\x6f'
            config.BLOCK_FIRST = 154908
            config.BURN_START = 154908
            config.BURN_END = 4017708
            config.UNSPENDABLE = config.UNSPENDABLE_TESTNET_LIVECOIN
    else:
        if config.TESTCOIN:
            config.ADDRESSVERSION = b'\x00'
            config.BLOCK_FIRST = 288270
            config.BURN_START = 288310
            config.BURN_END = 2500000
            config.UNSPENDABLE = config.UNSPENDABLE_LIVE_TESTCOIN
        else:
            config.ADDRESSVERSION = b'\x00'
            config.BLOCK_FIRST = 287270
            config.BURN_START = 288310
            config.BURN_END = 293810
            config.UNSPENDABLE = config.UNSPENDABLE_LIVE_LIVECOIN

    # Headless operation
    config.HEADLESS = headless

def balances (address):
    def get_btc_balance(address):
        r = requests.get("https://blockchain.info/q/addressbalance/" + address)
        # ^any other services that provide this?? (blockexplorer.com doesn't...)
        try:
            assert r.status_code == 200
            return int(r.text) / float(config.UNIT)
        except:
            return "???"

    address_data = util.get_address(db, address=address)

    # Balances.
    balances = address_data['balances']
    table = PrettyTable(['Asset', 'Amount'])
    table.add_row(['BTC', get_btc_balance(address)])  # BTC
    for balance in balances:
        asset = balance['asset']
        amount = util.devise(db, balance['amount'], balance['asset'], 'output')
        table.add_row([asset, amount])
    print('Balances')
    print(table.get_string())

if __name__ == '__main__':
    if os.name == 'nt':
        #patch up cmd.exe's "challenged" (i.e. broken/non-existent) UTF-8 logging
        util_windows.fix_win32_unicode()
    
    # Parse command-line arguments.
    parser = argparse.ArgumentParser(prog='chancecoind', description='the reference implementation of the Chancecoin protocol')
    parser.add_argument('-V', '--version', action='version', version="chancecoind v%s" % config.CLIENT_VERSION)

    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='sets log level to DEBUG instead of WARNING')
    parser.add_argument('--force', action='store_true', help='don\'t check whether Bitcoind is caught up')
    parser.add_argument('--testnet', action='store_true', help='use Bitcoin testnet addresses and block numbers')
    parser.add_argument('--testcoin', action='store_true', help='use the test Chancecoin network on every blockchain')
    parser.add_argument('--unsigned', action='store_true', default=False, help='print out unsigned hex of transaction; do not sign or broadcast')
    parser.add_argument('--headless', action='store_true', default=False, help='assume headless operation, e.g. don’t ask for wallet passhrase')

    parser.add_argument('--data-dir', help='the directory in which to keep the database, config file and log file, by default')
    parser.add_argument('--database-file', help='the location of the SQLite3 database')
    parser.add_argument('--config-file', help='the location of the configuration file')
    parser.add_argument('--log-file', help='the location of the log file')

    parser.add_argument('--bitcoind-rpc-connect', help='the hostname of the Bitcoind JSON-RPC server')
    parser.add_argument('--bitcoind-rpc-port', type=int, help='the port used to communicate with Bitcoind over JSON-RPC')
    parser.add_argument('--bitcoind-rpc-user', help='the username used to communicate with Bitcoind over JSON-RPC')
    parser.add_argument('--bitcoind-rpc-password', help='the password used to communicate with Bitcoind over JSON-RPC')

    parser.add_argument('--rpc-host', help='the host to provide the chancecoind JSON-RPC API')
    parser.add_argument('--rpc-port', type=int, help='port on which to provide the chancecoind JSON-RPC API')
    parser.add_argument('--rpc-user', help='required username to use the chancecoind JSON-RPC API (via HTTP basic auth)')
    parser.add_argument('--rpc-password', help='required password (for rpc-user) to use the chancecoind JSON-RPC API (via HTTP basic auth)')

    subparsers = parser.add_subparsers(dest='action', help='the action to be taken')

    parser_server = subparsers.add_parser('server', help='run the server (WARNING: not thread‐safe)')

    parser_send = subparsers.add_parser('send', help='create and broadcast a *send* message')
    parser_send.add_argument('--source', required=True, help='the source address')
    parser_send.add_argument('--destination', required=True, help='the destination address')
    parser_send.add_argument('--quantity', required=True, help='the quantity of ASSET to send')
    parser_send.add_argument('--asset', required=True, help='the ASSET of which you would like to send QUANTITY')

    parser_order = subparsers.add_parser('order', help='create and broadcast an *order* message')
    parser_order.add_argument('--source', required=True, help='the source address')
    parser_order.add_argument('--get-quantity', required=True, help='the quantity of GET_ASSET that you would like to receive')
    parser_order.add_argument('--get-asset', required=True, help='the asset that you would like to buy')
    parser_order.add_argument('--give-quantity', required=True, help='the quantity of GIVE_ASSET that you are willing to give')
    parser_order.add_argument('--give-asset', required=True, help='the asset that you would like to sell')
    parser_order.add_argument('--expiration', type=int, required=True, help='the number of blocks for which the order should be valid')
    parser_order.add_argument('--fee-required', default=D(config.FEE_REQUIRED_DEFAULT), help='the miners’ fee required for an order to match this one, as a fraction of the BTC to be bought')
    parser_order.add_argument('--fee-provided', default=D(config.FEE_PROVIDED_DEFAULT), help='the miners’ fee provided, as a fraction of the BTC to be sold')

    parser_btcpay= subparsers.add_parser('btcpay', help='create and broadcast a *BTCpay* message, to settle an Order Match for which you owe BTC')
    parser_btcpay.add_argument('--order-match-id', required=True, help='the concatenation of the hashes of the two transactions which compose the order match')

    parser_bet = subparsers.add_parser('bet', help='offer to make a bet on the value of a feed')
    parser_bet.add_argument('--source', required=True, help='the source address')
    parser_bet.add_argument('--feed-address', required=True, help='the address which publishes the feed to bet on')
    parser_bet.add_argument('--bet-type', choices=list(util.BET_TYPE_NAME.values()), required=True, help='choices: {}'.format(list(util.BET_TYPE_NAME.values())))
    parser_bet.add_argument('--deadline', required=True, help='the date and time at which the bet should be decided/settled')
    parser_bet.add_argument('--wager', required=True, help='the quantity of CHA to wager')
    parser_bet.add_argument('--counterwager', required=True, help='the minimum quantity of CHA to be wagered by the user to bet against you, if he were to accept the whole thing')
    parser_bet.add_argument('--target-value', default=0.0, help='target value for Equal/NotEqual bet')
    parser_bet.add_argument('--leverage', type=int, default=5040, help='leverage, as a fraction of 5040')
    parser_bet.add_argument('--expiration', type=int, required=True, help='the number of blocks for which the bet should be valid')

    parser_burn = subparsers.add_parser('burn', help='destroy bitcoins to earn CHA, during an initial period of time')
    parser_burn.add_argument('--source', required=True, help='the source address')
    parser_burn.add_argument('--quantity', required=True, help='quantity of BTC to be destroyed')

    parser_cancel= subparsers.add_parser('cancel', help='cancel an open order or bet you created')
    parser_cancel.add_argument('--offer-hash', required=True, help='the transaction hash of the order or bet')

    parser_address = subparsers.add_parser('balances', help='display the balances of a Chancecoin address')
    parser_address.add_argument('address', help='the address you are interested in')

    parser_wallet = subparsers.add_parser('wallet', help='list the addresses in your Bitcoind wallet along with their balances in all Chancecoin assets')

    parser_reparse = subparsers.add_parser('reparse', help='reparse all transactions in the database (WARNING: not thread‐safe)')

    parser_rollback = subparsers.add_parser('rollback', help='rollback database (WARNING: not thread‐safe)')
    parser_rollback.add_argument('block_index', type=int, help='the index of the last known good block')

    args = parser.parse_args()

    # Configuration
    set_options(data_dir=args.data_dir, bitcoind_rpc_connect=args.bitcoind_rpc_connect, bitcoind_rpc_port=args.bitcoind_rpc_port,
                 bitcoind_rpc_user=args.bitcoind_rpc_user, bitcoind_rpc_password=args.bitcoind_rpc_password, rpc_host=args.rpc_host, rpc_port=args.rpc_port,
                 rpc_user=args.rpc_user, rpc_password=args.rpc_password, log_file=args.log_file, database_file=args.database_file, testnet=args.testnet, testcoin=args.testcoin, unittest=False, headless=args.headless)

    # Database
    db = util.connect_to_db()

    # Logging (to file and console).
    logger = logging.getLogger() #get root logger
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    #Console logging
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    #File logging (rotated)
    max_log_size = 2 * 1024 * 1024 #max log size of 2 MB before rotation (make configurable later)
    if os.name == 'nt':
        fileh = util_windows.SanitizedRotatingFileHandler(config.LOG, maxBytes=max_log_size, backupCount=5)
    else:
        fileh = logging.handlers.RotatingFileHandler(config.LOG, maxBytes=max_log_size, backupCount=5)
    fileh.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(message)s', '%Y-%m-%d-T%H:%M:%S%z')
    fileh.setFormatter(formatter)
    logger.addHandler(fileh)
    #API requests logging (don't show on console in normal operation)
    requests_log = logging.getLogger("requests")
    requests_log.setLevel(logging.DEBUG if args.verbose else logging.WARNING)

    if args.action == None: args.action = 'server'

    # Check versions.
    util.versions_check(db)

    # Check that bitcoind is running, communicable, and caught up with the blockchain.
    # Check that the database has caught up with bitcoind.
    if not args.force:
        util.bitcoind_check(db)
        if args.action not in ('server', 'reparse', 'rollback'):
            util.database_check(db)

    # Do something.
    if args.action == 'send':
        quantity = util.devise(db, args.quantity, args.asset, 'input')
        unsigned_tx_hex = send.create(db, args.source, args.destination,
                                      quantity, args.asset, unsigned=args.unsigned)
        print(unsigned_tx_hex) if args.unsigned else json_print(bitcoin.transmit(unsigned_tx_hex))

    elif args.action == 'order':
        fee_required, fee_provided = D(args.fee_required), D(args.fee_provided)
        give_quantity, get_quantity = D(args.give_quantity), D(args.get_quantity)

        # Fee argument is either fee_required or fee_provided, as necessary.
        if args.give_asset == 'BTC':
            fee_required = 0
            fee_provided = util.devise(db, fee_provided, 'fraction', 'input')
            fee_provided = round(D(fee_provided) * D(give_quantity) * D(config.UNIT))
            if fee_provided < config.MIN_FEE:
                raise exceptions.InputError('Fee provided less than minimum necessary for acceptance in a block.')
        elif args.get_asset == 'BTC':
            fee_provided = config.MIN_FEE
            fee_required = util.devise(db, fee_required, 'fraction', 'input')
            fee_required = round(D(fee_required) * D(get_quantity) * D(config.UNIT))
        else:
            fee_required = 0
            fee_provided = config.MIN_FEE

        give_quantity = util.devise(db, give_quantity, args.give_asset, 'input')
        get_quantity = util.devise(db, get_quantity, args.get_asset, 'input')
        unsigned_tx_hex = order.create(db, args.source, args.give_asset, give_quantity,
                                args.get_asset, get_quantity,
                                args.expiration, fee_required, fee_provided, unsigned=args.unsigned)
        print(unsigned_tx_hex) if args.unsigned else json_print(bitcoin.transmit(unsigned_tx_hex))

    elif args.action == 'btcpay':
        unsigned_tx_hex = btcpay.create(db, args.order_match_id, unsigned=args.unsigned)
        print(unsigned_tx_hex) if args.unsigned else json_print(bitcoin.transmit(unsigned_tx_hex))

    elif args.action == 'bet':
        deadline = calendar.timegm(dateutil.parser.parse(args.deadline).utctimetuple())
        wager = util.devise(db, args.wager, 'CHA', 'input')
        counterwager = util.devise(db, args.counterwager, 'CHA', 'input')
        target_value = util.devise(db, args.target_value, 'value', 'input')
        leverage = util.devise(db, args.leverage, 'leverage', 'input')

        unsigned_tx_hex = bet.create(db, args.source, args.feed_address,
                                     util.BET_TYPE_ID[args.bet_type], deadline,
                                     wager, counterwager, target_value,
                                     leverage, args.expiration, unsigned=args.unsigned)
        print(unsigned_tx_hex) if args.unsigned else json_print(bitcoin.transmit(unsigned_tx_hex))

    elif args.action == 'burn':
        quantity = util.devise(db, args.quantity, 'BTC', 'input')
        unsigned_tx_hex = burn.create(db, args.source, quantity, unsigned=args.unsigned)
        print(unsigned_tx_hex) if args.unsigned else json_print(bitcoin.transmit(unsigned_tx_hex))

    elif args.action == 'cancel':
        unsigned_tx_hex = cancel.create(db, args.offer_hash, unsigned=args.unsigned)
        print(unsigned_tx_hex) if args.unsigned else json_print(bitcoin.transmit(unsigned_tx_hex))

    elif args.action == 'balances':
        try:
            bitcoin.base58_decode(args.address, config.ADDRESSVERSION)
        except Exception:
            raise exceptions.InvalidAddressError('Invalid Bitcoin address:',
                                                  args.address)
        balances(args.address)

    elif args.action == 'asset':
        # TODO: Use API
        if args.asset == 'CHA':
            total = util.devise(db, util.cha_supply(db), args.asset, 'output')
            divisible = True
        elif args.asset == 'BTC':
            total = None
            divisible = True

        asset_id = util.get_asset_id(args.asset)
        print('Asset Name:', args.asset)
        print('Asset ID:', asset_id)
        print('Total Issued:', total)

    elif args.action == 'wallet':
        total_table = PrettyTable(['Asset', 'Balance'])
        totals = {}

        print()
        # TODO: This should be burns minus issuance fees (so it won’t depend on escrowed funds).
        for group in bitcoin.rpc('listaddressgroupings', []):
            for bunch in group:
                address, btc_balance = bunch[:2]
                get_address = util.get_address(db, address=address)
                balances = get_address['balances']
                table = PrettyTable(['Asset', 'Balance'])
                empty = True
                if btc_balance:
                    table.add_row(['BTC', btc_balance])  # BTC
                    if 'BTC' in totals.keys(): totals['BTC'] += btc_balance
                    else: totals['BTC'] = btc_balance
                    empty = False
                for balance in balances:
                    asset = balance['asset']
                    balance = D(util.devise(db, balance['amount'], balance['asset'], 'output'))
                    if balance:
                        if asset in totals.keys(): totals[asset] += balance
                        else: totals[asset] = balance
                        table.add_row([asset, balance])
                        empty = False
                if not empty:
                    print(address)
                    print(table.get_string())
                    print()
        for asset in totals.keys():
            balance = totals[asset]
            total_table.add_row([asset, round(balance, 8)])
        print('TOTAL')
        print(total_table.get_string())
        print()

    elif args.action == 'reparse':
        blocks.reparse(db)

    elif args.action == 'rollback':
        blocks.reparse(db, block_index=args.block_index)

    # elif args.action == 'checksum':
        # print('Asset name:', args.string + checksum.compute(args.string))

    elif args.action == 'server':
        api_server = api.APIServer()
        api_server.daemon = True
        api_server.start()
        blocks.follow(db)

    else:
        parser.print_help()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
