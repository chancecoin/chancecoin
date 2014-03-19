import time
from datetime import datetime
from dateutil.tz import tzlocal
import decimal
D = decimal.Decimal
import sys
import json
import logging
import operator
from operator import itemgetter
import apsw
import collections
import inspect
import requests

from . import (config, exceptions, bitcoin)

b26_digits = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# Obsolete in Python 3.4, with enum module.
DO_FILTER_OPERATORS = {
    '==': operator.eq,
    '!=': operator.ne,
    '<': operator.lt,
    '>': operator.gt,
    '<=': operator.le,
    '>=': operator.ge,
}

def price (numerator, denominator):
    numerator = D(numerator)
    denominator = D(denominator)
    return D(numerator / denominator)

def log (db, command, category, bindings):

    def output (amount, asset):
        try:
            if asset not in ('price', 'fee_multiplier', 'odds'):
                return str(devise(db, amount, asset, 'output')) + ' ' + asset
            else:
                return str(devise(db, amount, asset, 'output'))
        except exceptions.AssetError:
            return '<AssetError>'
        except decimal.DivisionByZero:
            return '<DivisionByZero>'

    if command == 'update':
        if category == 'order':
            logging.debug('Database: set validity of order {} to {}.'.format(bindings['tx_hash'], bindings['validity']))
        elif category == 'bet':
            logging.debug('Database: set validity of bet {} to {}.'.format(bindings['tx_hash'], bindings['validity']))
        elif category == 'order_matches':
            logging.debug('Database: set validity of order_match {} to {}.'.format(bindings['order_match_id'], bindings['validity']))
        elif category == 'bet_matches':
            logging.debug('Database: set validity of bet_match {} to {}.'.format(bindings['bet_match_id'], bindings['validity']))
        # TODO: elif category == 'balances':
            # logging.debug('Database: set balance of {} in {} to {}.'.format(bindings['address'], bindings['asset'], output(bindings['amount'], bindings['asset']).split(' ')[0]))

    elif command == 'insert':  # TODO

        if category == 'credits':
            logging.debug('Credit: {} to {} #{}# <{}>'.format(output(bindings['amount'], bindings['asset']), bindings['address'], bindings['calling_function'], bindings['event']))

        elif category == 'debits':
            logging.debug('Debit: {} from {} #{}# <{}>'.format(output(bindings['amount'], bindings['asset']), bindings['address'], bindings['calling_function'], bindings['event']))

        elif category == 'sends':
            logging.info('Send: {} from {} to {} ({}) [{}]'.format(output(bindings['amount'], bindings['asset']), bindings['source'], bindings['destination'], bindings['tx_hash'], bindings['validity']))

        elif category == 'orders':
            give_asset = bindings['give_asset']
            get_asset = bindings['get_asset']

            give_amount = output(bindings['give_amount'], bindings['give_asset']).split(' ')[0]
            get_amount = output(bindings['get_amount'], bindings['get_asset']).split(' ')[0]

            # Consistent ordering for currency pairs. (Partial DUPE.)
            if get_asset < give_asset:
                try:
                    price = output(D(get_amount) / D(give_amount), 'price')
                except (decimal.DivisionByZero, decimal.InvalidOperation):
                    price = '??'
                price_assets = get_asset + '/' + give_asset
                action = 'sell {} {}'.format(give_amount, give_asset)
            else:
                try:
                    price = output(D(give_amount) / D(get_amount), 'price')
                except (decimal.DivisionByZero, decimal.InvalidOperation):
                    price = '??'
                price_assets = give_asset + '/' + get_asset
                action = 'buy {} {}'.format(get_amount, get_asset)

            logging.info('Order: {} at {} {} in {} blocks, with a provided fee of {} BTC and a required fee of {} BTC ({}) [{}]'.format(action, price, price_assets, bindings['expiration'], bindings['fee_provided'] / config.UNIT, bindings['fee_required'] / config.UNIT, bindings['tx_hash'], bindings['validity']))

        elif category == 'order_matches':
            forward_amount = bindings['forward_amount']
            backward_amount = bindings['backward_amount']
            forward_asset = bindings['forward_asset']
            backward_asset = bindings['backward_asset']

            # This can't be gotten rid of!
            forward_print = output(forward_amount, forward_asset)
            backward_print = output(backward_amount, backward_asset)

            # Consistent ordering for currency pairs. (Partial DUPE.)
            if forward_asset < backward_asset:
                try:
                    price = output(D(forward_amount) / D(backward_amount), 'price')
                except (decimal.DivisionByZero, decimal.InvalidOperation):
                    price = None
                price_assets = forward_asset + '/' + backward_asset
                foobar = '{} for {}'.format(forward_print, backward_print)
            else:
                try:
                    price = output(D(backward_amount) / D(forward_amount), 'price')
                except (decimal.DivisionByZero, decimal.InvalidOperation):
                    price = None
                price_assets = backward_asset + '/' + forward_asset
                foobar = '{} for {}'.format(backward_print, forward_print)

            logging.info('Order Match: {} at {} {} ({}) [{}]'.format(foobar, price, price_assets, bindings['id'], bindings['validity']))

        elif category == 'btcpays':
            logging.info('BTC Payment: {} paid {} to {} for order match {} ({}) [{}]'.format(bindings['source'], output(bindings['btc_amount'], 'BTC'), bindings['destination'], bindings['order_match_id'], bindings['tx_hash'], bindings['validity']))

        elif category == 'bets':
            logging.info('Bet: {} bet {} with chance {} and payout {} [{}]'.format(bindings['source'], output(bindings['bet'], 'CHA'), bindings['chance'], bindings['payout'], bindings['validity']))

        elif category == 'burns':
            logging.info('Burn: {} burned {} for {} ({}) [{}]'.format(bindings['source'], output(bindings['burned'], 'BTC'), output(bindings['earned'], 'CHA'), bindings['tx_hash'], bindings['validity']))

        elif category == 'cancels':
            logging.info('Cancel: {} ({}) [{}]'.format(bindings['offer_hash'], bindings['tx_hash'], bindings['validity']))

        elif category == 'order_expirations':
            logging.info('Expired order: {}'.format(bindings['order_hash']))

        elif category == 'order_match_expirations':
            logging.info('Expired Order Match awaiting payment: {}'.format(bindings['order_match_id']))

def rowtracer(cursor, sql):
    """Converts fetched SQL data into dict-style"""
    dictionary = {}
    for index, (name, type_) in enumerate(cursor.getdescription()):
        dictionary[name] = sql[index]
    return dictionary

def exectracer(cursor, sql, bindings):
    # This means that all changes to database must use a very simple syntax.
        # TODO: Need sanity checks here.
    sql = sql.lower()

    # Parse SQL.
    array = sql.split('(')[0].split(' ')
    if 'insert' in sql:
        command, category = array[0], array[2]
    elif 'update' in sql:
        command, category = array[0], array[1]
    else:
        return True

    db = cursor.getconnection()
    dictionary = {'command': command, 'category': category, 'bindings': bindings}

    # Skip blocks, transactions.
    if 'blocks' in sql or 'transactions' in sql: return True

    # Record alteration in database.
    if not category in ('balances', 'messages'):
        cursor = db.cursor()

        # Get last message index.
        cursor.execute('''SELECT * FROM messages WHERE message_index = (SELECT MAX(message_index) from messages)''')
        try:
            message_index = cursor.fetchall()[0]['message_index'] + 1
        except IndexError:
            message_index = 0

        # Get current block.
        # Hackish
        try:
            block_index = bindings['block_index']
        except KeyError:
            try:
                block_index = bindings['tx1_block_index']
            except KeyError:
                block_index = 0 # TODO

        bindings_string = json.dumps(collections.OrderedDict(sorted(bindings.items())))
        cursor.execute('insert into messages values(:message_index, :block_index, :command, :category, :bindings)',
                       (message_index, block_index, command, category, bindings_string))

        message_index += 1
        cursor.close()

    # Log.
    log(db, command, category, bindings)

    return True

def connect_to_db():
    """Connects to the SQLite database, returning a db Connection object"""
    db = apsw.Connection(config.DATABASE)
    cursor = db.cursor()
    cursor.execute('''PRAGMA count_changes = OFF''')
    cursor.close()
    db.setrowtrace(rowtracer)
    db.setexectrace(exectracer)
    return db

def versions_check (db):
    try:
        host = 'https://raw2.github.com/chancecoin/chancecoin/master/versions.json'
        response = requests.get(host, headers={'cache-control': 'no-cache'})
        versions = json.loads(response.text)
    except Exception as e:
        raise exceptions.DatabaseVersionError('Unable to check client, database versions. How’s your Internet access?')

    # Check client version (for important UI changes).
    if config.CLIENT_VERSION < versions['minimum_client_version']:
        raise exceptions.ClientVersionError('Please upgrade chancecoind to the latest version.')

    # Check the database version when past the block at which the protocol change
    # comes into effect.
    try:
        block_index = last_block(db)['block_index']
    except apsw.SQLError:
        logging.debug('Status: Version checks passed.') # DUPE
        return
    for protocol_change in versions['protocol_changes']:
        if block_index >= protocol_change['block_index']:
            if config.DB_VERSION < protocol_change['minimum_database_version']:
                raise exceptions.DatabaseVersionError('Please upgrade chancecoind to the latest version.')

    logging.debug('Status: Version checks passed.')
    return

def bitcoind_check (db):
    """Checks blocktime of last block to see if Bitcoind is running behind."""
    block_count = bitcoin.rpc('getblockcount', [])
    block_hash = bitcoin.rpc('getblockhash', [block_count])
    block = bitcoin.rpc('getblock', [block_hash])
    time_behind = time.time() - block['time']   # How reliable is the block time?!
    if time_behind > 60 * 60 * 2:   # Two hours.
        raise exceptions.BitcoindError('Bitcoind is running about {} seconds behind.'.format(round(time_behind)))

def database_check (db):
    """Checks Chancecoin database to see if the chancecoind server has caught up with Bitcoind."""
    cursor = db.cursor()
    block_index = last_block(db)['block_index']
    if block_index == bitcoin.rpc('getblockcount', []):
        cursor.close()
        return
    print('Database not up to date.')
    raise exceptions.DatabaseError('Chancecoin database is behind Bitcoind. Is the chancecoind server running?')

def do_filter(results, filters, filterop):
    """Filters results based on a filter data structure (as used by the API)"""
    if not len(results) or not filters: #empty results, or not filtering
        return results
    if isinstance(filters, dict): #single filter entry, convert to a one entry list
        filters = [filters,]
    #validate filter(s)
    required_fields = ['field', 'op', 'value']
    for filter in filters:
        for field in required_fields: #should have all fields
            if field not in filter:
                raise Exception("A specified filter is missing the '%s' field" % field)
        if filterop not in ('and', 'or'):
            raise Exception("Invalid filterop setting. Must be either 'and' or 'or'.")
        if filter['op'] not in DO_FILTER_OPERATORS.keys():
            raise Exception("A specified filter op is invalid or not recognized: '%s'" % filter['op'])
        if filter['field'] == 'block_index':
            raise Exception("For performance reasons, please use the start_block and end_block API arguments to do block_index filtering")
        if filter['field'] not in results[0]:
            raise Exception("A specified filter field is invalid or not recognized for the given object type: '%s'" % filter['field'])
        if type(filter['value']) not in (str, int, float, bool):
            raise Exception("Value specified for filter field '%s' is not one of the supported value types (str, int, float, bool)" % (
                filter['field']))
        if results[0][filter['field']] != None and filter['value'] != None and type(filter['value']) != type(results[0][filter['field']]):
            # field is None when it does not matter.
            raise Exception("Value specified for filter field '%s' does not match the data type of that field (value: %s, field: %s) and neither is None" % (
                filter['field'], type(filter['value']), type(results[0][filter['field']])))
    #filter data
    if filterop == 'and':
        for filter in filters:
            results = [e for e in results if DO_FILTER_OPERATORS[filter['op']](e[filter['field']], filter['value'])]
        return results
    else: #or
        combined_results = []
        for filter in filters:
            combined_results += [e for e in results if DO_FILTER_OPERATORS[filter['op']](e[filter['field']], filter['value'])]
        return combined_results

def do_order_by(results, order_by, order_dir):
    if not len(results) or not order_by: #empty results, or not ordering
        return results
    assert isinstance(results, list) and isinstance(results[0], dict)

    if order_by not in results[0]:
        raise KeyError("Specified order_by property '%s' does not exist in returned data" % order_by)
    if order_dir not in ('asc', 'desc'):
        raise Exception("Invalid order_dir: '%s'. Must be 'asc' or 'desc'" % order_dir)
    return sorted(results, key=itemgetter(order_by), reverse=order_dir=='desc')

def get_limit_to_blocks(start_block, end_block, col_names=['block_index',]):
    if    (start_block is not None and not isinstance(start_block, int)) \
       or (end_block is not None and not isinstance(end_block, int)):
        raise ValueError("start_block and end_block must be either an integer, or None")
    assert isinstance(col_names, list) and len(col_names) in [1, 2]

    if start_block is None and end_block is None:
        return ''
    elif len(col_names) == 1:
        col_name = col_names[0]
        if start_block and end_block:
            block_limit_clause = " WHERE %s >= %s AND %s <= %s" % (col_name, start_block, col_name, end_block)
        elif start_block:
            block_limit_clause = " WHERE %s >= %s" % (col_name, start_block)
        elif end_block:
            block_limit_clause = " WHERE %s <= %s" % (col_name, end_block)
    else: #length of 2
        if start_block and end_block:
            block_limit_clause = " WHERE (%s >= %s OR %s >= %s) AND (%s <= %s OR %s <= %s)" % (
                col_name[0], start_block, col_name[1], start_block,
                col_name[0], end_block, col_name[1], end_block)
        elif start_block:
            block_limit_clause = " WHERE %s >= %s OR %s >= %s" % (
                col_name[0], start_block, col_name[1], start_block)
        elif end_block:
            block_limit_clause = " WHERE %s >= %s OR %s >= %s" % (
                col_name[0], end_block, col_name[1], end_block)
    return block_limit_clause

def isodt (epoch_time):
    return datetime.fromtimestamp(epoch_time, tzlocal()).isoformat()

def cha_supply (db):
    cursor = db.cursor()

    # Add burns.
    cursor.execute('''SELECT * FROM burns \
                      WHERE validity = ?''', ('valid',))
    burn_total = sum([burn['earned'] for burn in cursor.fetchall()])

    cursor.close()
    return burn_total

def bankroll (db):
    cursor = db.cursor()

    cursor.execute('''SELECT * FROM balances \
                      WHERE asset = ? and bankroll = ?''', ('CHA',1))
    bankroll_total = sum([balance['amount'] for balance in cursor.fetchall()])

    cursor.close()
    return bankroll_total

def last_block (db):
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM blocks WHERE block_index = (SELECT MAX(block_index) from blocks)''')
    try:
        last_block = cursor.fetchall()[0]
    except IndexError:
        raise exceptions.DatabaseError('No blocks found.')
    cursor.close()
    return last_block

def get_block (db, block_index):
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM blocks WHERE block_index = ?''', (block_index))
    try:
        block = cursor.fetchall()[0]
    except IndexError:
        raise exceptions.DatabaseError('No blocks found.')
    cursor.close()
    return block

def get_asset_id (asset):
    # Special cases.
    if asset == 'BTC': return 0
    elif asset == 'CHA': return 1
    if asset[0] == 'A': raise exceptions.AssetNameError('starts with ‘A’')

    # Checksum
    """
    if not checksum.verify(asset):
        raise exceptions.AssetNameError('invalid checksum')
    else:
        asset = asset[:-1]  # Strip checksum character.
    """

    # Convert the Base 26 string to an integer.
    n = 0
    for c in asset:
        n *= 26
        if c not in b26_digits:
            raise exceptions.AssetNameError('invalid character:', c)
        digit = b26_digits.index(c)
        n += digit

    if not n > 26**3:
        raise exceptions.AssetNameError('too short')

    return n

def get_asset_name (asset_id):
    if asset_id == 0: return 'BTC'
    elif asset_id == 1: return 'CHA'

    if not asset_id > 26**3:
        raise exceptions.AssetIDError('too low')

    # Divide that integer into Base 26 string.
    res = []
    n = asset_id
    while n > 0:
        n, r = divmod (n, 26)
        res.append(b26_digits[r])
    asset_name = ''.join(res[::-1])

    """
    return asset_name + checksum.compute(asset_name)
    """
    return asset_name


def debit (db, block_index, address, asset, amount, event=None):

    # Get calling function.
    parent = inspect.stack()[1]
    frame, filename, lineno, function, code_context, index = parent
    parent_name = inspect.getmodulename(filename)
    calling_function = (parent_name + '.' + function)

    debit_cursor = db.cursor()
    assert asset != 'BTC' # Never BTC.
    assert type(amount) == int
    if asset == 'BTC':
        raise exceptions.BalanceError('Cannot debit bitcoins from a Chancecoin address!')

    debit_cursor.execute('''SELECT * FROM balances \
                            WHERE (address = ? AND asset = ?)''', (address, asset))
    balances = debit_cursor.fetchall()
    if not len(balances) == 1: old_balance = 0
    else: old_balance = balances[0]['amount']

    if old_balance < amount:
        raise exceptions.BalanceError('Insufficient funds.')

    balance = round(old_balance - amount)
    balance = min(balance, config.MAX_INT)

    bindings = {
        'amount': balance,
        'address': address,
        'asset': asset
    }
    sql='update balances set amount = :amount where (address = :address and asset = :asset)'
    debit_cursor.execute(sql, bindings)

    # Record debit.
    bindings = {
        'block_index': block_index,
        'address': address,
        'asset': asset,
        'amount': amount,
        'calling_function': calling_function,
        'event': event
    }
    sql='insert into debits values(:block_index, :address, :asset, :amount, :calling_function, :event)'
    debit_cursor.execute(sql, bindings)

    debit_cursor.close()

def credit (db, block_index, address, asset, amount, event=None):
    # Get calling function. DUPE
    parent = inspect.stack()[1]
    frame, filename, lineno, function, code_context, index = parent
    parent_name = inspect.getmodulename(filename)
    calling_function = (parent_name + '.' + function)

    credit_cursor = db.cursor()
    assert asset != 'BTC' # Never BTC.
    assert type(amount) == int

    credit_cursor.execute('''SELECT * FROM balances \
                             WHERE (address = ? AND asset = ?)''', (address, asset))
    balances = credit_cursor.fetchall()
    if len(balances) == 0:
        assert balances == []

        #update balances table with new balance
        bindings = {
            'address': address,
            'asset': asset,
            'amount': amount,
            'bankroll': 1
        }
        sql='insert into balances values(:address, :asset, :amount, :bankroll)'
        credit_cursor.execute(sql, bindings)
    elif len(balances) > 1:
        raise Exception
    else:
        old_balance = balances[0]['amount']
        assert type(old_balance) == int
        balance = round(old_balance + amount)
        balance = min(balance, config.MAX_INT)

        bindings = {
            'amount': balance,
            'address': address,
            'asset': asset
        }
        sql='update balances set amount = :amount where (address = :address and asset = :asset)'
        credit_cursor.execute(sql, bindings)

    # Record credit.
    bindings = {
        'block_index': block_index,
        'address': address,
        'asset': asset,
        'amount': amount,
        'calling_function': calling_function,
        'event': event
    }
    sql='insert into credits values(:block_index, :address, :asset, :amount, :calling_function, :event)'
    credit_cursor.execute(sql, bindings)
    credit_cursor.close()

def devise (db, quantity, asset, dest, divisible=None):
    # For output only.
    def norm(num, places):
        # Round only if necessary.
        num = round(num, places)

        fmt = '{:.' + str(places) + 'f}'
        num = fmt.format(num)
        return num.rstrip('0')+'0' if num.rstrip('0')[-1] == '.' else num.rstrip('0')

    if asset in ('leverage', 'price', 'odds', 'value', 'fraction'):
        if dest == 'output':
            return norm(quantity, 6)
        elif dest == 'input':
            # Hackish
            if asset == 'leverage':
                return round(quantity)
            else:
                return float(quantity)  # TODO: Float?!

    if asset in ('fee_multiplier',):
        return norm(D(quantity) / D(1e8), 6)

    if divisible == None:
        if asset in ('BTC', 'CHA'):
            divisible = True
        else:
            cursor = db.cursor()
            cursor.execute('''SELECT * FROM issuances \
                              WHERE (validity = ? AND asset = ?)''', ('valid', asset))
            issuances = cursor.fetchall()
            cursor.close()
            if not issuances: raise exceptions.AssetError('No such asset: {}'.format(asset))
            divisible = issuances[0]['divisible']

    if divisible:
        if dest == 'output':
            quantity = D(quantity) / D(config.UNIT)
            if quantity == quantity.to_integral():
                return str(quantity) + '.0'  # For divisible assets, display the decimal point.
            else:
                return norm(quantity, 8)
        elif dest == 'input':
            quantity = D(quantity) * D(config.UNIT)
            if quantity == quantity.to_integral():
                return int(quantity)
            else:
                raise exceptions.QuantityError('Divisible assets have only eight decimal places of precision.')
        else:
            return quantity
    else:
        if quantity != round(quantity):
            raise exceptions.QuantityError('Fractional quantities of indivisible assets.')
        return round(quantity)

def get_debits (db, address=None, asset=None, filters=None, order_by=None, order_dir='asc', start_block=None, end_block=None, filterop='and'):
    """This does not include BTC."""
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if address: filters.append({'field': 'address', 'op': '==', 'value': address})
    if asset: filters.append({'field': 'asset', 'op': '==', 'value': asset})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM debits%s'''
        % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_credits (db, address=None, asset=None, filters=None, order_by=None, order_dir='asc', start_block=None, end_block=None, filterop='and'):
    """This does not include BTC."""
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if address: filters.append({'field': 'address', 'op': '==', 'value': address})
    if asset: filters.append({'field': 'asset', 'op': '==', 'value': asset})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM credits%s'''
        % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_balances (db, address=None, asset=None, filters=None, order_by=None, order_dir='asc', filterop='and'):
    """This should never be used to check Bitcoin balances."""
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if address: filters.append({'field': 'address', 'op': '==', 'value': address})
    if asset: filters.append({'field': 'asset', 'op': '==', 'value': asset})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM balances''')
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_sends (db, validity=None, source=None, destination=None, filters=None, order_by='tx_index', order_dir='asc', start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if validity: filters.append({'field': 'validity', 'op': '==', 'value': validity})
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    if destination: filters.append({'field': 'destination', 'op': '==', 'value': destination})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM sends%s'''
        % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_orders (db, validity=None, source=None, show_empty=True, show_expired=True, filters=None, order_by=None, order_dir='asc', start_block=None, end_block=None, filterop='and'):
    def filter_expired(e):
        #Ignore BTC orders one block early. (This is why we need show_expired.)
        #function returns True if the element is NOT expired
        time_left = e['expire_index'] - last_block(db)['block_index']
        if e['give_asset'] == 'BTC': time_left -= 1
        return False if time_left < 0 else True

    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if validity: filters.append({'field': 'validity', 'op': '==', 'value': validity})
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    if not show_empty: filters.append({'field': 'give_remaining', 'op': '!=', 'value': 0})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM orders%s'''
        % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    if not show_expired: results = [e for e in results if filter_expired(e)]
    return do_order_by(results, order_by, order_dir)

def get_order_matches (db, validity=None, is_mine=False, address=None, tx0_hash=None, tx1_hash=None, filters=None, order_by='tx1_index', order_dir='asc', start_block=None, end_block=None, filterop='and'):
    def filter_is_mine(e):
        if (    (not bitcoin.rpc('validateaddress', [e['tx0_address']])['ismine'] or
                 e['forward_asset'] != 'BTC')
            and (not bitcoin.rpc('validateaddress', [e['tx1_address']])['ismine'] or
                 e['backward_asset'] != 'BTC')):
            return False #is not mine
        return True #is mine
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if validity: filters.append({'field': 'validity', 'op': '==', 'value': validity})
    if tx0_hash: filters.append({'field': 'tx0_hash', 'op': '==', 'value': tx0_hash})
    if tx1_hash: filters.append({'field': 'tx1_hash', 'op': '==', 'value': tx1_hash})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM order_matches%s'''
        % get_limit_to_blocks(start_block, end_block,
            col_names=['tx0_block_index', 'tx1_block_index']))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    if is_mine: results = [e for e in results if filter_is_mine(e)]
    if address: results = [e for e in results if e['tx0_address'] == address or e['tx1_address'] == address]
    return do_order_by(results, order_by, order_dir)

def get_btcpays (db, validity=None, filters=None, order_by='tx_index', order_dir='asc', start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if validity: filters.append({'field': 'validity', 'op': '==', 'value': validity})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM btcpays%s'''
        % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_bets (db, validity=None, source=None, show_empty=True, filters=None, order_by=None, order_dir='desc', start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if validity: filters.append({'field': 'validity', 'op': '==', 'value': validity})
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    if not show_empty: filters.append({'field': 'wager_remaining', 'op': '==', 'value': 0})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM bets%s'''
        % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_burns (db, validity=True, source=None, filters=None, order_by='tx_index', order_dir='asc', start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if validity: filters.append({'field': 'validity', 'op': '==', 'value': validity})
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM burns%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_cancels (db, validity=True, source=None, filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if validity: filters.append({'field': 'validity', 'op': '==', 'value': validity})
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM cancels%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_order_expirations (db, source=None, filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    if source: filters.append({'field': 'source', 'op': '==', 'value': source})
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM order_expirations%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    return do_order_by(results, order_by, order_dir)

def get_order_match_expirations (db, address=None, filters=None, order_by=None, order_dir=None, start_block=None, end_block=None, filterop='and'):
    if filters is None: filters = list()
    if filters and not isinstance(filters, list): filters = [filters,]
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM order_match_expirations%s'''
         % get_limit_to_blocks(start_block, end_block))
    results = do_filter(cursor.fetchall(), filters, filterop)
    cursor.close()
    if address: results = [e for e in results if e['tx0_address'] == address or e['tx1_address'] == address]
    return do_order_by(results, order_by, order_dir)

def get_address (db, address, start_block=None, end_block=None):
    if not bitcoin.base58_decode(address, config.ADDRESSVERSION):
        raise exceptions.InvalidAddressError('Not a valid Bitcoin address:',
                                             address)
    address_dict = {}
    address_dict['balances'] = get_balances(db, address=address)

    address_dict['debits'] = get_debits(db, address=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['credits'] = get_credits(db, address=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['burns'] = get_burns(db, validity='valid', source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['sends'] = get_sends(db, validity='valid', source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block, filterop='or')
    #^ with filterop == 'or', we get all sends where this address was the source OR destination

    address_dict['orders'] = get_orders(db, validity='valid', source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['order_matches'] = get_order_matches(db, validity='valid', address=address,
        order_by='tx0_block_index', order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['btcpays'] = get_btcpays(db, validity='valid', order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['bets'] = get_bets(db, validity='valid', source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['cancels'] = get_cancels(db, validity='valid', source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['order_expirations'] = get_order_expirations(db, source=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    address_dict['order_match_expirations'] = get_order_match_expirations(db, address=address, order_by='block_index',
        order_dir='asc', start_block=start_block, end_block=end_block)

    return address_dict

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
