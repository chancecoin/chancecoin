#! /usr/bin/python3

"""
All wagers are in CHA.
"""

import struct
import decimal
D = decimal.Decimal

from . import (util, config, bitcoin, exceptions, util)

FORMAT = '>HIQQdII'
LENGTH = 2 + 4 + 8 + 8 + 8 + 4 + 4
ID = 40

def validate (db, source, bet, chance, payout):
    problems = []

    if not bet:
        problems.append('zero bet')

    if 1/chance!=payout*(1-config.HOUSE_EDGE):
        problems.append('chance and payout are not congruent')

    if (payout-1)*bet > config.MAX_PROFIT*util.cha_supply(db):
        problems.append('maximum payout exceeded')

    # For SQLite3
    if bet > config.MAX_INT:
        problems.append('maximum integer size exceeded')

    return problems

def create (db, source, bet, chance, payout, unsigned=False):

    # Check for sufficient funds.
    balances = util.get_balances(db, address=source, asset='CHA')
    if not balances or balances[0]['amount'] < bet:
        raise exceptions.BetError('insufficient funds')

    problems = validate(db, source, bet, chance, payout)
    if problems: raise exceptions.BetError(problems)

    data = config.PREFIX + struct.pack(config.TXTYPE_FORMAT, ID)
    data += struct.pack(FORMAT, bet, chance, payout)
    return bitcoin.transaction(source, source, config.DUST_SIZE,
                               config.MIN_FEE, data, unsigned=unsigned)

def parse (db, tx, message):
    bet_parse_cursor = db.cursor()

    # Unpack message.
    try:
        assert len(message) == LENGTH
        (bet, chance, payout) = struct.unpack(FORMAT, message)
        validity = 'valid'
    except struct.error as e:
        (bet, chance, payout) = None, None, None
        validity = 'invalid: could not unpack'

    if validity == 'valid':
        balances = util.get_balances(db, address=tx['source'], asset='CHA')
        if not balances: bet = 0
        elif balances[0]['amount'] < bet:
            bet = min(round(balances[0]['amount']), bet)
        #... = tx['destination']
        problems = validate(db, tx['source'], bet, chance, payout)
        if problems: validity = 'invalid: ' + ';'.join(problems)

    if bet == 0.0:
        # The way to get out of being part of the bankroll is by betting 0 CHA. 
        # This will permanently turn the address off as a part of the bankroll.
        bindings = {
            'address': tx['source'],
            'asset': 'CHA'
        }
        sql='update balances set bankroll = 0 where (address = :address and asset = :asset)'
        bet_parse_cursor.execute(sql, bindings)

    # Debit bet amount
    if validity == 'valid':
        # Determine if bet is a winner
        block = util.get_block(db, tx['block_index'])
        block_hash = block['block_hash']
        roll = (int(block_hash,16) % 1000000000)/1000000000.0
        balances = util.get_balances(db, asset='CHA', filters=[{'field': 'bankroll', 'op': '==', 'value': 1},{'field': 'address', 'op': '!=', 'value': tx['source']}])
        bankroll = util.bankroll(db)
        if roll<chance:
            #The bet is a winning bet
            util.credit(db, tx['block_index'], tx['source'], 'CHA', (payout-1.0)*bet)
            for balance in balances:
                util.debit(db, tx['block_index'], tx['source'], 'CHA', (payout-1.0)*bet*(balance['amount']/bankroll))                
        else:
            #The bet is a losing bet
            util.debit(db, tx['block_index'], tx['source'], 'CHA', bet)
            for balance in balances:
                util.credit(db, tx['block_index'], tx['source'], 'CHA', bet*(balance['amount']/bankroll))                

    # Add parsed transaction to message-type–specific table.
    bindings = {
        'tx_index': tx['tx_index'],
        'tx_hash': tx['tx_hash'],
        'block_index': tx['block_index'],
        'source': tx['source'],
        'bet': bet,
        'chance': chance,
        'payout': payout,
        'profit': 0,
        'validity': validity,
    }
    sql='insert into bets values(:tx_index, :tx_hash, :block_index, :source, :bet, :chance, :payout, :profit, :validity)'
    bet_parse_cursor.execute(sql, bindings)

    # Match.
    match(db, tx)

    bet_parse_cursor.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
