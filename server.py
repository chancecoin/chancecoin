#!/usr/bin/env python

import os.path
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
from lib import (config, api, util, exceptions, bitcoin, blocks)
from lib import (send, order, btcpay, bet, burn, cancel)

chancecoind.set_options()
db = util.connect_to_db()

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

class FAQHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("faq.html")

class ResourcesHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("resources.html")

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
        bets = util.get_bets(db)
        supply = util.devise(db, util.cha_supply(db), 'CHA', 'output')
        bankroll = util.devise(db, util.bankroll(db), 'CHA', 'output')
        max_profit = float(bankroll)*config.MAX_PROFIT
        self.render("casino.html", bets = bets, updated = updated, version_updated = version_updated, supply = supply, bankroll = bankroll, house_edge = config.HOUSE_EDGE, max_profit = max_profit)
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        if self.get_argument("source") and self.get_argument("bet") and self.get_argument("payout") and self.get_argument("chance"):
            updated = yield tornado.gen.Task(is_updated)
            version_updated = yield tornado.gen.Task(is_version_updated)
            bets = util.get_bets(db)
            supply = util.devise(db, util.cha_supply(db), 'CHA', 'output')
            bankroll = util.devise(db, util.bankroll(db), 'CHA', 'output')
            max_profit = float(bankroll)*config.MAX_PROFIT
            source = self.get_argument("source")
            bet = util.devise(db, self.get_argument("bet"), 'CHA', 'input')
            chance = util.devise(db, self.get_argument("chance"), 'value', 'input')
            payout = util.devise(db, self.get_argument("payout"), 'value', 'input')
            unsigned_tx_hex = bet.create(db, args.source, bet, chance, payout, unsigned=False)
            #bitcoin.transmit(unsigned_tx_hex, ask=False)
            self.render("casino.html", bets = bets, updated = updated, version_updated = version_updated, supply = supply, bankroll = bankroll, house_edge = config.HOUSE_EDGE, max_profit = max_profit)

class WalletHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        updated = yield tornado.gen.Task(is_updated)
        version_updated = yield tornado.gen.Task(is_version_updated)
        self.render("wallet.html", wallet = None, updated = updated, version_updated = version_updated)
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        updated = yield tornado.gen.Task(is_updated)
        version_updated = yield tornado.gen.Task(is_version_updated)
        wallet = None
        if self.get_argument("form")=="balance":
            address = self.get_argument("address")
            wallet = util.get_address(db, address = address)
        elif self.get_argument("form")=="send":
            source = self.get_argument("source")
            destination = self.get_argument("destination")
            quantity = util.devise(db, self.get_argument("quantity"), 'CHA', 'input')
            unsigned_tx_hex = send.create(db, source, destination, quantity, 'CHA', unsigned=False)
            #bitcoin.transmit(unsigned_tx_hex, ask=False)
            print(unsigned_tx_hex)
        elif self.get_argument("form")=="burn":
            source = self.get_argument("source")
            quantity = util.devise(db, self.get_argument("quantity"), 'CHA', 'input')
            unsigned_tx_hex = burn.create(db, source, quantity, unsigned=False)
            #bitcoin.transmit(unsigned_tx_hex, ask=False)
            print(unsigned_tx_hex)
        elif self.get_argument("form")=="buy":
            source = self.get_argument("source")
            quantity = util.devise(db, self.get_argument("quantity"), 'CHA', 'input')
            price = util.devise(db, self.get_argument("price"), 'value', 'input')
            pricetimesquantity = util.devise(db, float(self.get_argument("quantity"))*float(self.get_argument("price")), 'BTC', 'input')
            expiration = 6 * 24 #24 hour order
            unsigned_tx_hex = order.create(db, source, 'BTC', pricetimesquantity, 'CHA', quantity,
                                           expiration, 0, config.MIN_FEE / config.UNIT, unsigned=False)
            #bitcoin.transmit(unsigned_tx_hex, ask=False)
            print(unsigned_tx_hex)
        elif self.get_argument("form")=="sell":
            source = self.get_argument("source")
            quantity = util.devise(db, self.get_argument("quantity"), 'CHA', 'input')
            price = util.devise(db, self.get_argument("price"), 'value', 'input')
            pricetimesquantity = util.devise(db, float(self.get_argument("quantity"))*float(self.get_argument("price")), 'BTC', 'input')
            expiration = 6 * 24 #24 hour order
            unsigned_tx_hex = order.create(db, source, 'CHA', quantity, 'BTC', pricetimesquantity,
                                           expiration, 0, config.MIN_FEE / config.UNIT, unsigned=False)
            #bitcoin.transmit(unsigned_tx_hex, ask=False)
            print(unsigned_tx_hex)
        self.render("wallet.html", wallet = wallet, updated = updated, version_updated = version_updated)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", HomeHandler),
            (r"/wallet", WalletHandler),
            (r"/casino", CasinoHandler),
            (r"/faq", FAQHandler),
            (r"/resources", ResourcesHandler),
            (r"/participate", ParticipateHandler),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            debug=True
        )
        tornado.web.Application.__init__(self, handlers, **settings)

def start():
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(8080)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    start()
