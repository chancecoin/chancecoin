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
        self.render("participate.html")

class CasinoHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        updated = yield tornado.gen.Task(is_updated)
        bets = util.get_bets(db)
        self.render("casino.html", bets = bets, updated = updated, supply = util.cha_supply(db), bankroll = util.bankroll(db))

class WalletHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        updated = yield tornado.gen.Task(is_updated)
        self.render("wallet.html", wallet = None, updated = updated)
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        updated = yield tornado.gen.Task(is_updated)
        wallet = None
        if self.get_argument("form")=="balance":
            address = self.get_argument("address")
            wallet = util.get_address(db, address = address)
        elif self.get_argument("form")=="send":
            source = self.get_argument("source")
            destination = self.get_argument("destination")
            quantity = float(self.get_argument("quantity"))
            unsigned_tx_hex = send.create(db, source, destination, quantity, asset, unsigned=False)
            #bitcoin.transmit(unsigned_tx_hex, ask=False)
            print(unsigned_tx_hex)
        elif self.get_argument("form")=="burn":
            source = self.get_argument("source")
            quantity = float(self.get_argument("quantity"))
            unsigned_tx_hex = burn.create(db, source, quantity, unsigned=False)
            #bitcoin.transmit(unsigned_tx_hex, ask=False)
            print(unsigned_tx_hex)
        self.render("wallet.html", wallet = wallet, updated = updated)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", HomeHandler),
            (r"/wallet", WalletHandler),
            (r"/faq", FAQHandler),
            (r"/resources", ResourcesHandler),
            (r"/participate", ParticipateHandler),
            (r"/casino", CasinoHandler),
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
