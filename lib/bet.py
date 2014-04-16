#! /usr/bin/python3

"""
All wagers are in CHA.
"""

import struct
import decimal
import re
import json
import urllib3
import math
import datetime
from datetime import *
from dateutil import *
from dateutil.tz import *
D = decimal.Decimal
import logging

from . import (util, config, bitcoin, exceptions, util)

FORMAT = '>Qdd'
LENGTH = 8 + 8 + 8
ID = 40

def validate (db, source, bet, chance, payout):
    problems = []

    if not bet:
        problems.append('zero bet')

    if chance!=100/(payout/(1-config.HOUSE_EDGE)):
        problems.append('chance and payout are not congruent')

    if chance<0 or chance>100:
        problems.append('chance must be between 0 and 100')

    if payout<=1:
        problems.append('payout must be greater than 1')

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

    # Debit bet amount
    if validity == 'valid':
        # The gambler pays the bet
        util.debit(db, tx['block_index'], tx['source'], 'CHA', bet)
        # The bet will be resolved later

    # get CHA supply
    cha_supply = util.cha_supply(db)

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
        'cha_supply': cha_supply,
        'validity': validity,
    }
    sql='insert into bets values(:tx_index, :tx_hash, :block_index, :source, :bet, :chance, :payout, :profit, :cha_supply, :validity)'
    bet_parse_cursor.execute(sql, bindings)

    bet_parse_cursor.close()

def resolve(db):
    def combinations(n,k):
        if k>n:
            return 0
        return math.factorial(n)/math.factorial(k)/math.factorial(n-k)
    cursor = db.cursor()

    # Get unresolved bets
    bets = list(cursor.execute('''SELECT * FROM bets WHERE profit=? and validity=?''', (0,'valid')))
    utc_zone = tz.tzutc()
    local_zone = tz.tzlocal()
    ny_zone = tz.gettz('America/New_York')
    for bet in bets:
        block = util.get_block(db, bet['block_index'])
        block_time = datetime.fromtimestamp(int(block['block_time'])).replace(tzinfo=local_zone)
        block_time_utc = block_time.astimezone(utc_zone)
        block_time_ny = block_time.astimezone(ny_zone)

        if block_time_ny.hour>=23 and block_time_ny.minute>=56:
            search_date = (block_time_ny+timedelta(days=1)).strftime('%d/%m/%Y')
        else:
            search_date = block_time_ny.strftime('%d/%m/%Y')
        http = urllib3.PoolManager()
        lotto = http.request('GET', 'http://nylottery.ny.gov/wps/PA_NYSLNumberCruncher/NumbersServlet?game=quick&action=winningnumbers&startSearchDate='+search_date+'&endSearchDate=&pageNo=&last=&perPage=999&sort=').data
        lotto = lotto.decode("utf-8")
        lotto = json.loads(lotto)
        for draw in lotto['draw']:
            draw_time =  datetime.strptime(draw['date'], '%m/%d/%Y %H:%M').replace(tzinfo=ny_zone)
            if draw_time>block_time_ny:
                numbers = draw['numbersDrawn']
                N = combinations(80,20)
                n = 0
                i = 1
                for number in numbers:
                    n += combinations(number-1,i)
                    i += 1
                roll1 = n/(N-1)
                roll2 = (int(bet['tx_hash'][10:],16) % 1000000000)/1000000000.0
                roll = (roll1 + roll2) % 1
                roll = roll * 100.0
                chance, payout, bet_amount, cha_supply = bet['chance'], bet['payout'], bet['bet'], bet['cha_supply']
                if roll<chance:
                    # the bet is a winner
                    # the gambler wins b*(p*(1-e)-1)*c/(c-b*p*(1-e)) CHA, but we already debited b CHA earlier
                    # also note that the (1-e) is already factored into the payout
                    profit = int(bet_amount*(payout-1)*cha_supply/(cha_supply-bet_amount*payout))
                    credit = profit + bet_amount
                    util.credit(db, bet['block_index'], bet['source'], 'CHA', credit)
                else:
                    # the bet is a loser
                    profit = -bet_amount
                bindings = {
                    'profit': profit,
                    'tx_index': bet['tx_index']
                }
                sql='update bets set profit = :profit where tx_index = :tx_index'
                cursor.execute(sql, bindings)
                break
        roll = 0

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
