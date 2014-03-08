#! /usr/bin/python3

"""
Datastreams are identified by the address that publishes them, and referenced
in transaction outputs.

For CFD leverage, 1x = 5040, 2x = 10080, etc.: 5040 is a superior highly
composite number and a colossally abundant number, and has 1-10, 12 as factors.

All wagers are in CHA.
"""

import struct
import decimal
D = decimal.Decimal

from . import (util, config, bitcoin, exceptions, util)

FORMAT = '>HIQQdII'
LENGTH = 2 + 4 + 8 + 8 + 8 + 4 + 4
ID = 40


def get_fee_multiplier (db, feed_address):
    '''Get fee_multiplier from the last broadcast from the feed_address address.
    '''
    broadcasts = util.get_broadcasts(db, source=feed_address)
    if broadcasts:
        last_broadcast = broadcasts[-1]
        fee_fraction_int = last_broadcast['fee_fraction_int']
        if fee_fraction_int: return fee_fraction_int / 1e8
        else: return 0
    else:
        return 0

def validate (db, source, feed_address, bet_type, deadline, wager_amount,
              counterwager_amount, target_value, leverage, expiration):
    problems = []

    # Look at feed to be bet on.
    broadcasts = util.get_broadcasts(db, validity='valid', source=feed_address)
    if not broadcasts:
        problems.append('feed doesn’t exist')
    elif not broadcasts[-1]['text']:
        problems.append('feed is locked')
    elif broadcasts[-1]['timestamp'] >= deadline:
        problems.append('deadline in that feed’s past')

    # Valid leverage level?
    if leverage != 5040 and bet_type in (2,3):   # Equal, NotEqual
        problems.append('leverage cannot be used with bet types Equal and NotEqual')
    if leverage < 5040:
        problems.append('leverage level too low (less than 5040, which is 1:1)')

    if not wager_amount or not counterwager_amount:
        problems.append('zero wager or counterwager')

    if target_value and bet_type in (0,1):   # BullCFD, BearCFD
        problems.append('CFDs have no target value')

    if not target_value and bet_type in (4,5,6,7): # Call, Put
        problems.append('target value (strike) required for Calls and Puts')

    if expiration > config.MAX_EXPIRATION:
        problems.append('maximum expiration time exceeded')

    # For SQLite3
    if wager_amount > config.MAX_INT or counterwager_amount > config.MAX_INT or bet_type > config.MAX_INT or deadline > config.MAX_INT or leverage > config.MAX_INT:
        problems.append('maximum integer size exceeded')

    return problems

def create (db, source, feed_address, bet_type, deadline, wager_amount,
            counterwager_amount, target_value, leverage, expiration, unsigned=False):

    # Check for sufficient funds.
    fee_multiplier = get_fee_multiplier(db, feed_address)
    balances = util.get_balances(db, address=source, asset='CHA')
    if not balances or balances[0]['amount']/(1 + fee_multiplier / 1e8) < wager_amount :
        raise exceptions.BetError('insufficient funds to both make wager and pay feed fee (in CHA)')

    problems = validate(db, source, feed_address, bet_type, deadline, wager_amount,
                        counterwager_amount, target_value, leverage, expiration)
    if problems: raise exceptions.BetError(problems)

    data = config.PREFIX + struct.pack(config.TXTYPE_FORMAT, ID)
    data += struct.pack(FORMAT, bet_type, deadline,
                        wager_amount, counterwager_amount, target_value,
                        leverage, expiration)
    return bitcoin.transaction(source, feed_address, config.DUST_SIZE,
                               config.MIN_FEE, data, unsigned=unsigned)

def parse (db, tx, message):
    bet_parse_cursor = db.cursor()

    # Unpack message.
    try:
        assert len(message) == LENGTH
        (bet_type, deadline, wager_amount,
         counterwager_amount, target_value, leverage,
         expiration) = struct.unpack(FORMAT, message)
        validity = 'valid'
    except struct.error as e:
        (bet_type, deadline, wager_amount,
         counterwager_amount, target_value, leverage,
         expiration) = None, None, None, None, None, None, None
        validity = 'invalid: could not unpack'

    fee_multiplier = 0
    odds = 0
    if validity == 'valid':
        try: odds = D(wager_amount) / D(counterwager_amount)
        except: pass

        # Overbet
        balances = util.get_balances(db, address=tx['source'], asset='CHA')
        if not balances: wager_amount = 0
        elif balances[0]['amount']/(1 + fee_multiplier / 1e8) < wager_amount:
            wager_amount = min(round(balances[0]['amount']/(1 + fee_multiplier / 1e8)), wager_amount)
            counterwager_amount = int(D(wager_amount) / odds)

        feed_address = tx['destination']
        problems = validate(db, tx['source'], feed_address, bet_type, deadline, wager_amount,
                            counterwager_amount, target_value, leverage, expiration)
        if problems: validity = 'invalid: ' + ';'.join(problems)

    # Debit amount wagered and fee.
    if validity == 'valid':
        fee_multiplier = get_fee_multiplier(db, feed_address)
        fee = round(wager_amount * fee_multiplier / 1e8)    # round?!
        util.debit(db, tx['block_index'], tx['source'], 'CHA', wager_amount)
        util.debit(db, tx['block_index'], tx['source'], 'CHA', fee)

    # Add parsed transaction to message-type–specific table.
    bindings = {
        'tx_index': tx['tx_index'],
        'tx_hash': tx['tx_hash'],
        'block_index': tx['block_index'],
        'source': tx['source'],
        'feed_address': feed_address,
        'bet_type': bet_type,
        'deadline': deadline,
        'wager_amount': wager_amount,
        'wager_remaining': wager_amount,
        'counterwager_amount': counterwager_amount,
        'counterwager_remaining': counterwager_amount,
        'target_value': target_value,
        'leverage': leverage,
        'expiration': expiration,
        'expire_index': tx['block_index'] + expiration,
        'fee_multiplier': fee_multiplier,
        'validity': validity,
    }
    sql='insert into bets values(:tx_index, :tx_hash, :block_index, :source, :feed_address, :bet_type, :deadline, :wager_amount, :wager_remaining, :counterwager_amount, :counterwager_remaining, :target_value, :leverage, :expiration, :expire_index, :fee_multiplier, :validity)'
    bet_parse_cursor.execute(sql, bindings)

    # Match.
    match(db, tx)

    bet_parse_cursor.close()

def match (db, tx):
    cursor = db.cursor()

    # Get bet in question.
    cursor.execute('''SELECT * FROM bets\
                                WHERE tx_index=?''', (tx['tx_index'],))
    tx1 = cursor.fetchall()[0]

    # Get counterbet_type.
    if tx1['bet_type'] % 2: counterbet_type = tx1['bet_type'] - 1
    else: counterbet_type = tx1['bet_type'] + 1

    feed_address = tx1['feed_address']

    cursor.execute('''SELECT * FROM bets\
                             WHERE (feed_address=? AND validity=? AND bet_type=?)''',
                             (tx1['feed_address'], 'valid', counterbet_type))
    tx1_wager_remaining = tx1['wager_remaining']
    tx1_counterwager_remaining = tx1['counterwager_remaining']
    bet_matches = cursor.fetchall()
    if tx['block_index'] > 284500:  # For backwards‐compatibility (no sorting before this block).
        sorted(bet_matches, key=lambda x: x['tx_index'])                                        # Sort by tx index second.
        sorted(bet_matches, key=lambda x: D(x['wager_amount']) / D(x['counterwager_amount']))   # Sort by price first.
    for tx0 in bet_matches:

        # Bet types must be opposite.
        if not counterbet_type == tx0['bet_type']: continue
        if tx0['leverage'] == tx1['leverage']:
            leverage = tx0['leverage']
        else:
            continue

        # Target values must agree exactly.
        if tx0['target_value'] == tx1['target_value']:
            target_value = tx0['target_value']
        else:
            continue

        # Fee multipliers must agree exactly.
        if tx0['fee_multiplier'] != tx1['fee_multiplier']:
            continue
        else:
            fee_multiplier = tx0['fee_multiplier']

        # Deadlines must agree exactly.
        if tx0['deadline'] != tx1['deadline']:
            continue

        # Make sure that that both bets still have funds remaining [to be wagered].
        if tx0['wager_remaining'] <= 0 or tx1_wager_remaining <= 0: continue

        # If the odds agree, make the trade. The found order sets the odds,
        # and they trade as much as they can.
        tx0_odds = util.price(tx0['wager_amount'], tx0['counterwager_amount'])
        tx0_inverse_odds = util.price(tx0['counterwager_amount'], tx0['wager_amount'])
        tx1_odds = util.price(tx1['wager_amount'], tx1['counterwager_amount'])

        # NOTE: Old protocol.
        if tx['block_index'] < 286000: tx0_inverse_odds = D(1) / tx0_odds

        if counterbet_type in (4,5,6,7): #wager and counterwager must match exactly for Calls and Puts
            if tx0['wager_amount']!=tx1['counterwager_amount'] or tx1['wager_amount']!=tx0['counterwager_amount']:
                continue

        if tx0_inverse_odds <= tx1_odds:
            forward_amount = int(min(D(tx0['wager_remaining']), D(tx1_wager_remaining) / tx1_odds))
            backward_amount = round(D(forward_amount) / tx0_odds)

            if not forward_amount: continue
            if tx1['block_index'] >= 286500:    # Protocol change.
                if not backward_amount: continue

            bet_match_id = tx0['tx_hash'] + tx1['tx_hash']

            # Debit the order.
            # Counterwager remainings may be negative.
            tx0_wager_remaining = tx0['wager_remaining'] - forward_amount
            tx0_counterwager_remaining = tx0['counterwager_remaining'] - backward_amount
            tx1_wager_remaining = tx1_wager_remaining - backward_amount
            tx1_counterwager_remaining = tx1_counterwager_remaining - forward_amount

            # tx0
            bindings = {
                'wager_remaining': tx0_wager_remaining,
                'counterwager_remaining': tx0_counterwager_remaining,
                'tx_index': tx0['tx_index']
            }
            sql='update bets set wager_remaining = :wager_remaining, counterwager_remaining = :counterwager_remaining where tx_index = :tx_index'
            cursor.execute(sql, bindings)

            # tx1
            bindings = {
                'wager_remaining': tx1_wager_remaining,
                'counterwager_remaining': tx1_counterwager_remaining,
                'tx_index': tx1['tx_index']
            }
            sql='update bets set wager_remaining = :wager_remaining, counterwager_remaining = :counterwager_remaining where tx_index = :tx_index'
            cursor.execute(sql, bindings)


            # Get last value of feed.
            initial_value = util.get_broadcasts(db, validity='valid', source=tx1['feed_address'])[-1]['value']

            # Record bet fulfillment.
            bindings = {
                'id': tx0['tx_hash'] + tx['tx_hash'],
                'tx0_index': tx0['tx_index'],
                'tx0_hash': tx0['tx_hash'],
                'tx0_address': tx0['source'],
                'tx1_index': tx1['tx_index'],
                'tx1_hash': tx1['tx_hash'],
                'tx1_address': tx1['source'],
                'tx0_bet_type': tx0['bet_type'],
                'tx1_bet_type': tx1['bet_type'],
                'feed_address': tx1['feed_address'],
                'initial_value': initial_value,
                'deadline': tx1['deadline'],
                'target_value': tx1['target_value'],
                'leverage': tx1['leverage'],
                'forward_amount': forward_amount,
                'backward_amount': backward_amount,
                'tx0_block_index': tx0['block_index'],
                'tx1_block_index': tx1['block_index'],
                'tx0_expiration': tx0['expiration'],
                'tx1_expiration': tx1['expiration'],
                'match_expire_index': min(tx0['expire_index'], tx1['expire_index']),
                'fee_multiplier': fee_multiplier,
                'validity': 'valid',
            }
            sql='insert into bet_matches values(:id, :tx0_index, :tx0_hash, :tx0_address, :tx1_index, :tx1_hash, :tx1_address, :tx0_bet_type, :tx1_bet_type, :feed_address, :initial_value, :deadline, :target_value, :leverage, :forward_amount, :backward_amount, :tx0_block_index, :tx1_block_index, :tx0_expiration, :tx1_expiration, :match_expire_index, :fee_multiplier, :validity)'
            cursor.execute(sql, bindings)

    cursor.close()

def expire (db, block_index, block_time):
    cursor = db.cursor()

    # Expire bets and give refunds for the amount wager_remaining.
    cursor.execute('''SELECT * FROM bets \
                      WHERE (validity = ? AND expire_index < ?)''', ('valid', block_index))
    for bet in cursor.fetchall():

        # Update validity of bet.
        bindings = {
            'validity': 'invalid: expired',
            'tx_index': bet['tx_index']
        }
        sql='update bets set validity = :validity where tx_index = :tx_index'
        cursor.execute(sql, bindings)

        util.credit(db, block_index, bet['source'], 'CHA', round(bet['wager_remaining'] * (1 + bet['fee_multiplier'] / 1e8)))

        # Record bet expiration.
        bindings = {
            'bet_index': bet['tx_index'],
            'bet_hash': bet['tx_hash'],
            'source': bet['source'],
            'block_index': block_index
        }
        sql='insert into bet_expirations values(:bet_index, :bet_hash, :source, :block_index)'
        cursor.execute(sql, bindings)

    # Expire bet matches whose deadline is more than two weeks before the current block time.
    cursor.execute('''SELECT * FROM bet_matches \
                      WHERE (validity = ? AND deadline < ?)''', ('valid', block_time - config.TWO_WEEKS))
    for bet_match in cursor.fetchall():
        util.credit(db, block_index, bet_match['tx0_address'], 'CHA',
                    round(bet_match['forward_amount'] * (1 + bet_match['fee_multiplier'] / 1e8)))
        util.credit(db, block_index, bet_match['tx1_address'], 'CHA',
                    round(bet_match['backward_amount'] * (1 + bet_match['fee_multiplier'] / 1e8)))

        # Update validity of bet match.
        bindings = {
            'validity': 'invalid: expired awaiting broadcast',
            'bet_match_id': bet_match['id']
        }
        sql='update bet_matches set validity = :validity where id = :bet_match_id'
        cursor.execute(sql, bindings)

        # Record bet match expiration.
        bindings = {
            'block_index': block_index,
            'tx0_address': bet_match['tx0_address'],
            'tx1_address': bet_match['tx1_address'],
            'bet_match_id': bet_match['tx0_hash'] + bet_match['tx1_hash']
        }
        sql='insert into bet_match_expirations values(:block_index, :tx0_address, :tx1_address, :bet_match_id)'
        cursor.execute(sql, bindings)

    cursor.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
