#! /usr/bin/python3

import sys
import os
import threading
import decimal
import time
import json
import logging
from logging import handlers as logging_handlers
D = decimal.Decimal

import apsw
import cherrypy
from cherrypy import wsgiserver
from jsonrpc import JSONRPCResponseManager, dispatcher

from . import (config, exceptions, util, bitcoin)
from . import (send, order, btcpay, bet, burn, cancel)

class APIServer(threading.Thread):

    def __init__ (self):
        threading.Thread.__init__(self)

    def run (self):
        db = util.connect_to_db()

        ######################
        #READ API

        @dispatcher.add_method
        def get_address(address, start_block=None, end_block=None):
            try:
                return util.get_address(db, address=address, start_block=start_block, end_block=end_block)
            except exceptions.InvalidAddressError:
                return None

        @dispatcher.add_method
        def get_balances(filters=None, order_by=None, order_dir=None, filterop="and"):
            return util.get_balances(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                filterop=filterop)

        @dispatcher.add_method
        def get_bets(filters=None, is_valid=True, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_bets(db,
                filters=filters,
                validity='valid' if bool(is_valid) else None,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_bet_matches(filters=None, is_valid=True, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_bet_matches(db,
                filters=filters,
                validity='valid' if bool(is_valid) else None,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_btcpays(filters=None, is_valid=True, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_btcpays(db,
                filters=filters,
                validity='valid' if bool(is_valid) else None,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_burns(filters=None, is_valid=True, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_burns(db,
                filters=filters,
                validity='valid' if bool(is_valid) else None,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_cancels(filters=None, is_valid=True, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_cancels(db,
                filters=filters,
                validity='valid' if bool(is_valid) else None,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_credits (filters=None, order_by=None, order_dir=None, filterop="and"):
            return util.get_credits(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                filterop=filterop)

        @dispatcher.add_method
        def get_debits (filters=None, order_by=None, order_dir=None, filterop="and"):
            return util.get_debits(db,
                filters=filters,
                order_by=order_by,
                order_dir=order_dir,
                filterop=filterop)

        @dispatcher.add_method
        def get_orders (filters=None, is_valid=True, show_expired=True, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_orders(db,
                filters=filters,
                validity='valid' if bool(is_valid) else None,
                show_expired=show_expired,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_order_matches (filters=None, is_valid=True, is_mine=False, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_order_matches(db,
                filters=filters,
                validity='valid' if bool(is_valid) else None,
                is_mine=is_mine,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_sends (filters=None, is_valid=True, order_by=None, order_dir=None, start_block=None, end_block=None, filterop="and"):
            return util.get_sends(db,
                filters=filters,
                validity='valid' if bool(is_valid) else None,
                order_by=order_by,
                order_dir=order_dir,
                start_block=start_block,
                end_block=end_block,
                filterop=filterop)

        @dispatcher.add_method
        def get_messages(block_index):
            cursor = db.cursor()
            cursor.execute('select * from messages where block_index = ? order by message_index asc', (block_index,))
            messages = cursor.fetchall()
            cursor.close()
            return messages

        @dispatcher.add_method
        def cha_supply():
            return util.cha_supply(db)

        @dispatcher.add_method
        def get_block_info(block_index):
            assert isinstance(block_index, int) 
            cursor = db.cursor()
            cursor.execute('''SELECT * FROM blocks WHERE block_index = ?''', (block_index,))
            try:
                block = cursor.fetchall()[0]
            except IndexError:
                raise exceptions.DatabaseError('No blocks found.')
            cursor.close()
            return block
            
        @dispatcher.add_method
        def get_running_info():
            try:
                util.database_check(db)
            except:
                caught_up = False
            else:
                caught_up = True

            try:
                last_block = util.last_block(db)
            except:
                last_block = {'block_index': None, 'block_hash': None, 'block_time': None}
                
            return {
                'db_caught_up': caught_up,
                'last_block': last_block,
                'chancecoind_version': config.CLIENT_VERSION,
                'db_version_major': config.DB_VERSION_MAJOR,
                'db_version_minor': config.DB_VERSION_MINOR,
            }


        ######################
        #WRITE/ACTION API
        @dispatcher.add_method
        def do_bet(source, bet, chance, payout, unsigned=False):
            unsigned_tx_hex = bet.create(db, source, bet, chance, payout, unsigned=unsigned)
            return unsigned_tx_hex if unsigned else bitcoin.transmit(unsigned_tx_hex, ask=False)

        @dispatcher.add_method
        def do_btcpay(order_match_id, unsigned=False):
            unsigned_tx_hex = btcpay.create(db, order_match_id, unsigned=unsigned)
            return unsigned_tx_hex if unsigned else bitcoin.transmit(unsigned_tx_hex, ask=False)

        @dispatcher.add_method
        def do_burn(source, quantity, unsigned=False):
            unsigned_tx_hex = burn.create(db, source, quantity, unsigned=unsigned)
            return unsigned_tx_hex if unsigned else bitcoin.transmit(unsigned_tx_hex, ask=False)

        @dispatcher.add_method
        def do_cancel(offer_hash, unsigned=False):
            unsigned_tx_hex = cancel.create(db, offer_hash, unsigned=unsigned)
            return unsigned_tx_hex if unsigned else bitcoin.transmit(unsigned_tx_hex, ask=False)

        @dispatcher.add_method
        def do_order(source, give_quantity, give_asset, get_quantity, get_asset, expiration, fee_required=0,
                     fee_provided=config.MIN_FEE / config.UNIT, unsigned=False):
            unsigned_tx_hex = order.create(db, source, give_asset,
                                           give_quantity, get_asset,
                                           get_quantity, expiration,
                                           fee_required, fee_provided,
                                           unsigned=unsigned)
            return unsigned_tx_hex if unsigned else bitcoin.transmit(unsigned_tx_hex, ask=False)

        @dispatcher.add_method
        def do_send(source, destination, quantity, asset, unsigned=False):
            unsigned_tx_hex = send.create(db, source, destination, quantity, asset, unsigned=unsigned)
            return unsigned_tx_hex if unsigned else bitcoin.transmit(unsigned_tx_hex, ask=False)


        class API(object):
            @cherrypy.expose
            def index(self):
                cherrypy.response.headers["Content-Type"] = "application/json"
                cherrypy.response.headers["Access-Control-Allow-Origin"] = '*'
                cherrypy.response.headers["Access-Control-Allow-Methods"] = 'POST, GET, OPTIONS'
                cherrypy.response.headers["Access-Control-Allow-Headers"] = 'Origin, X-Requested-With, Content-Type, Accept'

                if cherrypy.request.method == "OPTIONS": #web client will send us this before making a request
                    return

                try:
                    data = cherrypy.request.body.read().decode('utf-8')
                except ValueError:
                    raise cherrypy.HTTPError(400, 'Invalid JSON document')
                response = JSONRPCResponseManager.handle(data, dispatcher)
                return response.json.encode()

        cherrypy.config.update({
            'log.screen': False,
            "environment": "embedded",
            'log.error_log.propagate': False,
            'log.access_log.propagate': False,
            "server.logToScreen" : False
        })
        checkpassword = cherrypy.lib.auth_basic.checkpassword_dict(
            {config.RPC_USER: config.RPC_PASSWORD})
        app_config = {
            '/': {
                'tools.trailing_slash.on': False,
                'tools.auth_basic.on': True,
                'tools.auth_basic.realm': 'chancecoind',
                'tools.auth_basic.checkpassword': checkpassword,
            },
        }
        application = cherrypy.Application(API(), script_name="/jsonrpc/", config=app_config)

        #disable logging of the access and error logs to the screen
        application.log.access_log.propagate = False
        application.log.error_log.propagate = False

        if config.PREFIX != config.UNITTEST_PREFIX:  #skip setting up logs when for the test suite
            #set up a rotating log handler for this application
            # Remove the default FileHandlers if present.
            application.log.error_file = ""
            application.log.access_file = ""
            maxBytes = getattr(application.log, "rot_maxBytes", 10000000)
            backupCount = getattr(application.log, "rot_backupCount", 1000)
            # Make a new RotatingFileHandler for the error log.
            fname = getattr(application.log, "rot_error_file", os.path.join(config.DATA_DIR, config.API_LOG))
            h = logging_handlers.RotatingFileHandler(fname, 'a', maxBytes, backupCount)
            h.setLevel(logging.DEBUG)
            h.setFormatter(cherrypy._cplogging.logfmt)
            application.log.error_log.addHandler(h)
            # Make a new RotatingFileHandler for the access log.
            fname = getattr(application.log, "rot_access_file", os.path.join(config.DATA_DIR, config.API_LOG))
            h = logging_handlers.RotatingFileHandler(fname, 'a', maxBytes, backupCount)
            h.setLevel(logging.DEBUG)
            h.setFormatter(cherrypy._cplogging.logfmt)
            application.log.access_log.addHandler(h)

        #start up the API listener/handler
        server = wsgiserver.CherryPyWSGIServer(
            (config.RPC_HOST, int(config.RPC_PORT)), application)
        #logging.debug("Initializing API interface…")
        try:
            server.start()
        except OSError:
            raise Exception("Cannot start the API subsystem. Is chancecoind"
                " already running, or is something else listening on port %s?" % config.RPC_PORT)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
