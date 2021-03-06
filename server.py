#!/usr/bin/env python

import os.path, sys
import tornado.auth
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado import gen
from tornado.web import asynchronous
from threading import Thread
from functools import wraps

import chancecoind
from lib import (config, util, exceptions, bitcoin, blocks)
from lib import (send, order, btcpay, bet, burn, cancel)

db = None
is_bitcoind_connected = True
try:
    chancecoind.set_options()
    db = util.connect_to_db()
except exceptions.ConfigurationError:
    pass

def bet_tuples(bets):
    bets_new = []
    if bets!=None:
        for bet in bets:
            bets_new.append((bet['source'],util.devise(db, bet['bet'], 'CHA', 'output'),bet['chance'],bet['payout'],util.devise(db, bet['profit'], 'CHA', 'output')))
    return bets_new

def balance_tuples(balances):
    balances_new = []
    if balances!=None:
        cha_supply = util.cha_supply(db)
        for balance in balances:
            burns = util.get_burns(db, source = balance['address'], validity='valid')
            burned = sum([burn['burned'] for burn in burns])
            balances_new.append((balance['address'],util.devise(db, balance['amount'], 'CHA', 'output'),util.devise(db, burned, 'BTC', 'output'), balance['amount']/cha_supply*100))
    return balances_new

def order_tuples(orders):
    orders_new = []
    if orders!=None:
        for order in orders:
            if order['get_asset']=='CHA':
                cha_side = 'get_amount'
                btc_side = 'give_amount'
                buysell = 'buy'
            else:
                cha_side = 'give_amount'
                btc_side = 'get_amount'
                buysell = 'sell'
            orders_new.append((util.devise(db, order[cha_side], 'CHA', 'output'),float(util.devise(db, order[btc_side], 'BTC', 'output'))/float(util.devise(db, order[cha_side], 'CHA', 'output')), util.devise(db, order[btc_side], 'BTC', 'output'), buysell, order['tx_hash']))
    return orders_new

def order_match_tuples(order_matches):
    order_matches_new = []
    if order_matches!=None:
        for order_match in order_matches:
            if order_match['forward_asset']=='BTC':
                btc = util.devise(db, order_match['forward_amount'], 'BTC', 'output')
                cha = util.devise(db, order_match['backward_amount'], 'CHA', 'output')
            else:
                btc = util.devise(db, order_match['backward_amount'], 'BTC', 'output')
                cha = util.devise(db, order_match['forward_amount'], 'CHA', 'output')
            order_matches_new.append((btc,cha,order_match['id']))
    return order_matches_new

def run_async(func):
    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target = func, args = args, kwargs = kwargs)
        func_hl.start()
        return func_hl
    return async_func

@run_async
def is_db_updated(callback):
    try:
        util.database_check(db)
    except:
        callback(False)
    callback(True)

@run_async
def is_bitcoin_updated(callback):
    try:
        util.bitcoind_check(db)
    except:
        callback(False)
    callback(True)

@run_async
def is_version_updated(callback):
    try:
        util.versions_check()
    except:
        callback(False)
    callback(True)

@run_async
def get_status(callback):
    block_count_db, block_count_bitcoin = util.get_status(db)
    callback((block_count_db, block_count_bitcoin))

class HomeHandler(tornado.web.RequestHandler):
    def get(self):
        supply = util.devise(db, util.cha_supply(db), 'CHA', 'output')
        self.render("index.html", supply = supply)

class FreebiesHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("freebies.html")

class TechnicalHandler(tornado.web.RequestHandler):
    def get(self):
        max_profit = config.MAX_PROFIT
        house_edge = config.HOUSE_EDGE
        burn_start = config.BURN_START
        burn_end = config.BURN_END
        unspendable = config.UNSPENDABLE
        max_burn = config.MAX_BURN
        multiplier = config.MULTIPLIER
        multiplier_initial = config.MULTIPLIER_INITIAL
        self.render("technical.html", max_profit = max_profit, house_edge = house_edge, burn_start = burn_start, burn_end = burn_end, unspendable = unspendable, max_burn = max_burn, multiplier = multiplier, multiplier_initial = multiplier_initial)

class ErrorHandler(tornado.web.RequestHandler):
    def get(self):
        global is_bitcoind_connected
        error = 'An unknown error has occurred.'
        info = None
        if config.HAS_CONFIG==False:
            error = 'You need to set up a Chancecoin config file at '+config.CONFIG_PATH+'. You can find an example config file <a href="https://raw2.github.com/chancecoin/chancecoin/master/example.conf">here</a>.'
        if is_bitcoind_connected==False:
            error = 'Cannot connect to Bitcoin. Please make sure you have bitcoind or Bitcoin-QT running and that your config file is set correctly at ' + config.CONFIG_PATH + '.'
        self.render("error.html", error = error, info = info)

class ParticipateHandler(tornado.web.RequestHandler):
    def get(self):
        max_profit = config.MAX_PROFIT
        house_edge = config.HOUSE_EDGE
        burn_start = config.BURN_START
        burn_end = config.BURN_END
        unspendable = config.UNSPENDABLE
        max_burn = config.MAX_BURN
        multiplier = config.MULTIPLIER
        multiplier_initial = config.MULTIPLIER_INITIAL
        version = config.CLIENT_VERSION
        self.render("participate.html", max_profit = max_profit, house_edge = house_edge, burn_start = burn_start, burn_end = burn_end, unspendable = unspendable, max_burn = max_burn, multiplier = multiplier, multiplier_initial = multiplier_initial, version = version)

class BalancesHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        db_updated = yield tornado.gen.Task(is_db_updated)
        bitcoin_updated = yield tornado.gen.Task(is_bitcoin_updated)
        version_updated = yield tornado.gen.Task(is_version_updated)
        block_count_db, block_count_bitcoin = yield tornado.gen.Task(get_status)
        info = None
        error = None
        balances = util.get_balances(db, asset = 'CHA', order_by = 'amount', order_dir='desc')
        balances = balance_tuples(balances)
        self.render("balances.html", db_updated = db_updated, bitcoin_updated = bitcoin_updated, version_updated = version_updated, balances = balances, info = info, error = error, block_count_db = block_count_db, block_count_bitcoin = block_count_bitcoin)

class CasinoHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        db_updated = yield tornado.gen.Task(is_db_updated)
        bitcoin_updated = yield tornado.gen.Task(is_bitcoin_updated)
        version_updated = yield tornado.gen.Task(is_version_updated)
        block_count_db, block_count_bitcoin = yield tornado.gen.Task(get_status)
        info = None
        error = None
        bets = util.get_bets(db, order_by='tx_index', validity='valid')
        bets = bet_tuples(bets[:100])
        my_bets = []
        supply = util.devise(db, util.cha_supply(db), 'CHA', 'output')
        max_profit = float(supply)*config.MAX_PROFIT
        self.render("casino.html", db_updated = db_updated, bitcoin_updated = bitcoin_updated, version_updated = version_updated, bets = bets, my_bets = my_bets, supply = supply, house_edge = config.HOUSE_EDGE, max_profit = max_profit, info = info, error = error, block_count_db = block_count_db, block_count_bitcoin = block_count_bitcoin)
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        db_updated = yield tornado.gen.Task(is_db_updated)
        bitcoin_updated = yield tornado.gen.Task(is_bitcoin_updated)
        version_updated = yield tornado.gen.Task(is_version_updated)
        block_count_db, block_count_bitcoin = yield tornado.gen.Task(get_status)
        info = None
        error = None
        bets = util.get_bets(db, order_by='tx_index', validity='valid')
        bets = bet_tuples(bets[:100])
        my_bets = []
        supply = util.devise(db, util.cha_supply(db), 'CHA', 'output')
        max_profit = float(supply)*config.MAX_PROFIT
        if self.get_argument("form")=="roll" and self.get_argument("source") and self.get_argument("bet") and self.get_argument("payout") and self.get_argument("chance"):
            source = self.get_argument("source")
            bet_amount = util.devise(db, self.get_argument("bet"), 'CHA', 'input')
            chance = util.devise(db, self.get_argument("chance"), 'value', 'input')
            payout = util.devise(db, self.get_argument("payout"), 'value', 'input')
            try:
                tx_hex = bet.create(db, source, bet_amount, chance, payout, unsigned=False)
                bitcoin.transmit(tx_hex, ask=False)
                info = "Thanks for betting!"
            except:
                error = sys.exc_info()[1]
        elif self.get_argument("form")=="my_bets" and self.get_argument("address"):
            try:
                my_bets = util.get_bets(db, source = self.get_argument("address"), order_by='tx_index', validity='valid')
                my_bets = bet_tuples(my_bets)
            except:
                my_bets = []
        self.render("casino.html", db_updated = db_updated, bitcoin_updated = bitcoin_updated, version_updated = version_updated, bets = bets, my_bets = my_bets, supply = supply, house_edge = config.HOUSE_EDGE, max_profit = max_profit, info = info, error = error, block_count_db = block_count_db, block_count_bitcoin = block_count_bitcoin)

class WalletHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        db_updated = yield tornado.gen.Task(is_db_updated)
        bitcoin_updated = yield tornado.gen.Task(is_bitcoin_updated)
        version_updated = yield tornado.gen.Task(is_version_updated)
        block_count_db, block_count_bitcoin = yield tornado.gen.Task(get_status)
        info = None
        error = None
        orders_sell = util.get_orders(db, validity='valid', show_empty=False, show_expired=False, filters=[{'field': 'give_asset', 'op': '==', 'value': 'CHA'},{'field': 'get_asset', 'op': '==', 'value': 'BTC'}])
        orders_buy = util.get_orders(db, validity='valid', show_empty=False, show_expired=False, filters=[{'field': 'get_asset', 'op': '==', 'value': 'CHA'},{'field': 'give_asset', 'op': '==', 'value': 'BTC'}])
        orders_sell = sorted(order_tuples(orders_sell), key=lambda tup: tup[1], reverse=True)
        orders_buy = sorted(order_tuples(orders_buy), key=lambda tup: tup[1], reverse=True)
        my_orders = None
        my_order_matches = None
        balance = None
        self.render("wallet.html", db_updated = db_updated, bitcoin_updated = bitcoin_updated, version_updated = version_updated, wallet = None, orders_buy = orders_buy, orders_sell = orders_sell, info = info, error = error, block_count_db = block_count_db, block_count_bitcoin = block_count_bitcoin, balance = balance, my_orders = my_orders, my_order_matches = my_order_matches)
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        db_updated = yield tornado.gen.Task(is_db_updated)
        bitcoin_updated = yield tornado.gen.Task(is_bitcoin_updated)
        version_updated = yield tornado.gen.Task(is_version_updated)
        block_count_db, block_count_bitcoin = yield tornado.gen.Task(get_status)
        info = None
        error = None
        orders_sell = util.get_orders(db, validity='valid', show_empty=False, show_expired=False, filters=[{'field': 'give_asset', 'op': '==', 'value': 'CHA'},{'field': 'get_asset', 'op': '==', 'value': 'BTC'}])
        orders_buy = util.get_orders(db, validity='valid', show_empty=False, show_expired=False, filters=[{'field': 'get_asset', 'op': '==', 'value': 'CHA'},{'field': 'give_asset', 'op': '==', 'value': 'BTC'}])
        orders_sell = sorted(order_tuples(orders_sell), key=lambda tup: tup[1], reverse=True)
        orders_buy = sorted(order_tuples(orders_buy), key=lambda tup: tup[1], reverse=True)
        my_orders = None
        my_order_matches = None
        balance = None
        if self.get_argument("form")=="balance":
            address = self.get_argument("address")
            try:
                wallet = util.get_address(db, address = address)
            except:
                wallet = None
            balance = None
            if wallet != None:
                for balance in wallet['balances']:
                    if balance['asset']=='CHA':
                        balance = util.devise(db, balance['amount'], 'CHA', 'output')
        elif self.get_argument("form")=="my_orders":
            address = self.get_argument("address")
            try:
                my_orders = util.get_orders(db, validity='valid', show_empty=False, show_expired=False, source=address)
                my_orders = order_tuples(my_orders)
                my_order_matches = util.get_order_matches(db, validity='pending', is_mine=True, address=address)
                my_order_matches = order_match_tuples(my_order_matches)
            except:
                my_orders = None
                my_order_matches = None
        elif self.get_argument("form")=="btcpay":
            order_match_id = self.get_argument("order_match_id")
            try:
                tx_hex = btcpay.create(db, order_match_id, unsigned=False)
                bitcoin.transmit(tx_hex, ask=False)
                info = "BTC payment successful"
            except:
                error = sys.exc_info()[1]
        elif self.get_argument("form")=="cancel":
            tx_hash = self.get_argument("tx_hash")
            try:
                tx_hex = cancel.create(db, tx_hash, unsigned=False)
                bitcoin.transmit(tx_hex, ask=False)
                info = "Cancel successful"
            except:
                error = sys.exc_info()[1]
        elif self.get_argument("form")=="send":
            source = self.get_argument("source")
            destination = self.get_argument("destination")
            quantity = util.devise(db, self.get_argument("quantity"), 'CHA', 'input')
            try:
                tx_hex = send.create(db, source, destination, quantity, 'CHA', unsigned=False)
                bitcoin.transmit(tx_hex, ask=False)
                info = "Send successful"
            except:
                error = sys.exc_info()[1]
        elif self.get_argument("form")=="burn":
            source = self.get_argument("source")
            quantity = util.devise(db, self.get_argument("quantity"), 'CHA', 'input')
            try:
                tx_hex = burn.create(db, source, quantity, unsigned=False)
                bitcoin.transmit(tx_hex, ask=False)
                info = "Burn successful"
            except:
                error = sys.exc_info()[1]
        elif self.get_argument("form")=="buy":
            source = self.get_argument("source")
            quantity = util.devise(db, self.get_argument("quantity"), 'CHA', 'input')
            price = util.devise(db, self.get_argument("price"), 'value', 'input')
            pricetimesquantity = float(self.get_argument("quantity"))*float(self.get_argument("price"))
            pricetimesquantity = int(pricetimesquantity*config.UNIT)
            expiration = 6 * 24 #24 hour order
            try:
                tx_hex = order.create(db, source, 'BTC', pricetimesquantity, 'CHA', quantity,
                                           expiration, 0, config.MIN_FEE, unsigned=False)
                bitcoin.transmit(tx_hex, ask=False)
                info = "Buy order successful"
            except:
                error = sys.exc_info()[1]
        elif self.get_argument("form")=="sell":
            source = self.get_argument("source")
            quantity = util.devise(db, self.get_argument("quantity"), 'CHA', 'input')
            price = util.devise(db, self.get_argument("price"), 'value', 'input')
            pricetimesquantity = float(self.get_argument("quantity"))*float(self.get_argument("price"))
            pricetimesquantity = int(pricetimesquantity*config.UNIT)
            expiration = 6 * 24 #24 hour order
            try:
                tx_hex = order.create(db, source, 'CHA', quantity, 'BTC', pricetimesquantity,
                                               expiration, 0, config.MIN_FEE, unsigned=False)
                bitcoin.transmit(tx_hex, ask=False)
                info = "Sell order successful"
            except:
                error = sys.exc_info()[1]
        self.render("wallet.html", db_updated = db_updated, bitcoin_updated = bitcoin_updated, version_updated = version_updated, orders_buy = orders_buy, orders_sell = orders_sell, info = info, error = error, block_count_db = block_count_db, block_count_bitcoin = block_count_bitcoin, balance = balance, my_orders = my_orders, my_order_matches = my_order_matches)

class Application(tornado.web.Application):
    def __init__(self):
        global is_bitcoind_connected
        is_bitcoind_connected = util.is_bitcoind_connected()
        if db==None or is_bitcoind_connected == False:
            handlers = [
                (r"/", ErrorHandler),
                (r"/wallet", ErrorHandler),
                (r"/casino", ErrorHandler),
                (r"/balances", ErrorHandler),
                (r"/participate", ErrorHandler),
                (r"/technical", ErrorHandler),
                (r"/freebies", ErrorHandler),
            ]
        else:
            handlers = [
                (r"/", HomeHandler),
                (r"/wallet", WalletHandler),
                (r"/casino", CasinoHandler),
                (r"/balances", BalancesHandler),
                (r"/participate", ParticipateHandler),
                (r"/technical", TechnicalHandler),
                (r"/freebies", FreebiesHandler),
            ]
        if getattr(sys, 'frozen', False):
            file_frozen = sys.executable
        else:
            file_frozen = __file__
        settings = dict(
            template_path=os.path.join(os.path.dirname(file_frozen), "templates"),
            static_path=os.path.join(os.path.dirname(file_frozen), "static"),
            debug=True
        )
        tornado.web.Application.__init__(self, handlers, **settings)

def start():
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(8080)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    start()
