#!/usr/bin/env python

import os.path
import tornado.auth
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

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

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", HomeHandler),
            (r"/faq", FAQHandler),
            (r"/resources", ResourcesHandler),
            (r"/participate", ParticipateHandler),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
        )
        tornado.web.Application.__init__(self, handlers, **settings)


http_server = tornado.httpserver.HTTPServer(Application())
http_server.listen('8080')
tornado.ioloop.IOLoop.instance().start()
