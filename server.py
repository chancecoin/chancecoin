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

def run_async(func):
    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target = func, args = args, kwargs = kwargs)
        func_hl.start()
        return func_hl
    return async_func

@run_async
def is_updated(callback):
    try:
        util.database_check(db)
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

class HomeHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")

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
        error = 'An unknown error has occurred.'
        info = None
        if config.HAS_CONFIG==False:
            error = 'You need to set up a Chancecoin config file at '+config.CONFIG_PATH+'. You can find an example config file <a href="https://raw2.github.com/chancecoin/chancecoin/master/example.conf">here</a>.'
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
        self.render("participate.html", max_profit = max_profit, house_edge = house_edge, burn_start = burn_start, burn_end = burn_end, unspendable = unspendable, max_burn = max_burn, multiplier = multiplier, multiplier_initial = multiplier_initial)

class CasinoHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        updated = yield tornado.gen.Task(is_updated)
        version_updated = yield tornado.gen.Task(is_version_updated)
        info = None
        error = None
        bets = util.get_bets(db, order_by='tx_index', validity='valid')
        bets = bet_tuples(bets[:100])
        my_bets = []
        supply = util.devise(db, util.cha_supply(db), 'CHA', 'output')
        max_profit = float(supply)*config.MAX_PROFIT
        self.render("casino.html", bets = bets, my_bets = my_bets, updated = updated, version_updated = version_updated, supply = supply, house_edge = config.HOUSE_EDGE, max_profit = max_profit, info = info, error = error)
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        updated = yield tornado.gen.Task(is_updated)
        version_updated = yield tornado.gen.Task(is_version_updated)
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
                unsigned_tx_hex = bet.create(db, source, bet_amount, chance, payout, unsigned=False)
                bitcoin.transmit(unsigned_tx_hex, ask=False)
                info = "Thanks for betting!"
            except:
                error = sys.exc_info()[1]
        elif self.get_argument("form")=="my_bets" and self.get_argument("address"):
            my_bets = util.get_bets(db, source = self.get_argument("address"), order_by='tx_index', validity='valid')
            my_bets = bet_tuples(my_bets)
        self.render("casino.html", bets = bets, my_bets = my_bets, updated = updated, version_updated = version_updated, supply = supply, house_edge = config.HOUSE_EDGE, max_profit = max_profit, info = info, error = error)

class WalletHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        updated = yield tornado.gen.Task(is_updated)
        version_updated = yield tornado.gen.Task(is_version_updated)
        info = None
        error = None
        orders_sell = []
        orders_buy = []
        orders_sell_db = util.get_orders(db, validity='valid', show_empty=False, show_expired=False, filters=[{'field': 'give_asset', 'op': '=', 'value': 'CHA'},{'field': 'get_asset', 'op': '==', 'value': 'BTC'}])
        orders_buy_db = util.get_orders(db, validity='valid', show_empty=False, show_expired=False, filters=[{'field': 'get_asset', 'op': '=', 'value': 'CHA'},{'field': 'give_asset', 'op': '==', 'value': 'BTC'}])
        for order_sell in orders_sell_db:
            orders_sell.append((util.devise(db, order_sell['give_quantity'], 'CHA', 'output'),float(util.devise(db, order_sell['give_quantity'], 'CHA', 'output'))/float(util.devise(db, order_sell['get_quantity'], 'BTC', 'output'))))
        for order_buy in orders_buy_db:
            orders_buy.append((util.devise(db, order_buy['get_quantity'], 'CHA', 'output'),float(util.devise(db, order_buy['get_quantity'], 'CHA', 'output'))/float(util.devise(db, order_buy['give_quantity'], 'BTC', 'output'))))
        self.render("wallet.html", wallet = None, updated = updated, version_updated = version_updated, orders_buy = orders_buy, orders_sell = orders_sell, info = info, error = error)
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        updated = yield tornado.gen.Task(is_updated)
        version_updated = yield tornado.gen.Task(is_version_updated)
        info = None
        error = None
        orders_sell = []
        orders_buy = []
        orders_sell_db = util.get_orders(db, validity='valid', show_empty=False, show_expired=False, filters=[{'field': 'give_asset', 'op': '=', 'value': 'CHA'},{'field': 'get_asset', 'op': '==', 'value': 'BTC'}])
        orders_buy_db = util.get_orders(db, validity='valid', show_empty=False, show_expired=False, filters=[{'field': 'get_asset', 'op': '=', 'value': 'CHA'},{'field': 'give_asset', 'op': '==', 'value': 'BTC'}])
        for order_sell in orders_sell_db:
            orders_sell.append((util.devise(db, order_sell['give_quantity'], 'CHA', 'output'),float(util.devise(db, order_sell['give_quantity'], 'CHA', 'output'))/float(util.devise(db, order_sell['get_quantity'], 'BTC', 'output'))))
        for order_buy in orders_buy_db:
            orders_buy.append((util.devise(db, order_buy['get_quantity'], 'CHA', 'output'),float(util.devise(db, order_buy['get_quantity'], 'CHA', 'output'))/float(util.devise(db, order_buy['give_quantity'], 'BTC', 'output'))))
        if self.get_argument("form")=="balance":
            address = self.get_argument("address")
            wallet = util.get_address(db, address = address)
            balance = None
            for balance in wallet['balances']:
                if balance['asset']=='CHA':
                    balance = util.devise(db, balance['amount'], 'CHA', 'output')
            if balance!=None:
                info = "Your balance is "+balance+" CHA"
        elif self.get_argument("form")=="send":
            source = self.get_argument("source")
            destination = self.get_argument("destination")
            quantity = util.devise(db, self.get_argument("quantity"), 'CHA', 'input')
            try:
                unsigned_tx_hex = send.create(db, source, destination, quantity, 'CHA', unsigned=False)
                bitcoin.transmit(unsigned_tx_hex, ask=False)
                info = "Send successful"
            except:
                error = sys.exc_info()[1]
        elif self.get_argument("form")=="burn":
            source = self.get_argument("source")
            quantity = util.devise(db, self.get_argument("quantity"), 'CHA', 'input')
            try:
                unsigned_tx_hex = burn.create(db, source, quantity, unsigned=False)
                bitcoin.transmit(unsigned_tx_hex, ask=False)
                info = "Burn successful"
            except:
                error = sys.exc_info()[1]
        elif self.get_argument("form")=="buy":
            source = self.get_argument("source")
            quantity = util.devise(db, self.get_argument("quantity"), 'CHA', 'input')
            price = util.devise(db, self.get_argument("price"), 'value', 'input')
            pricetimesquantity = util.devise(db, float(self.get_argument("quantity"))*float(self.get_argument("price")), 'BTC', 'input')
            expiration = 6 * 24 #24 hour order
            try:
                unsigned_tx_hex = order.create(db, source, 'BTC', pricetimesquantity, 'CHA', quantity,
                                           expiration, 0, config.MIN_FEE / config.UNIT, unsigned=False)
                bitcoin.transmit(unsigned_tx_hex, ask=False)
                info = "Buy order successful"
            except:
                error = sys.exc_info()[1]
        elif self.get_argument("form")=="sell":
            source = self.get_argument("source")
            quantity = util.devise(db, self.get_argument("quantity"), 'CHA', 'input')
            price = util.devise(db, self.get_argument("price"), 'value', 'input')
            pricetimesquantity = util.devise(db, float(self.get_argument("quantity"))*float(self.get_argument("price")), 'BTC', 'input')
            expiration = 6 * 24 #24 hour order
            try:
                unsigned_tx_hex = order.create(db, source, 'CHA', quantity, 'BTC', pricetimesquantity,
                                               expiration, 0, config.MIN_FEE / config.UNIT, unsigned=False)
                bitcoin.transmit(unsigned_tx_hex, ask=False)
                info = "Sell order successful"
            except:
                error = sys.exc_info()[1]
        self.render("wallet.html", updated = updated, version_updated = version_updated, orders_buy = orders_buy, orders_sell = orders_sell, info = info, error = error)

class Application(tornado.web.Application):
    def __init__(self):
        if db==None:
            handlers = [
                (r"/", ErrorHandler),
                (r"/wallet", ErrorHandler),
                (r"/casino", ErrorHandler),
                (r"/participate", ErrorHandler),
            ]
        else:
            handlers = [
                (r"/", HomeHandler),
                (r"/wallet", WalletHandler),
                (r"/casino", CasinoHandler),
                (r"/participate", ParticipateHandler),
                (r"/freebies", FreebiesHandler),
                (r"/technical", TechnicalHandler),
            ]
        file_frozen = __file__
        if getattr(sys, 'frozen', False):
            file_frozen = sys.executable
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
