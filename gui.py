import sys,signal,os,threading
from threading import Thread
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
from PyQt4 import QtGui, QtCore
import time

import server
import chancecoind
from lib import (config, api, util, exceptions, bitcoin, blocks)
from lib import (send, order, btcpay, bet, burn, cancel)

class ChancecoinThread(QtCore.QThread):
    def __init__(self):
        QtCore.QThread.__init__(self)

    def run(self):
        chancecoind.set_options()
        db = util.connect_to_db()
        util.versions_check(db)
        blocks.follow(db)

class ServerThread(QtCore.QThread):
    def __init__(self):
        QtCore.QThread.__init__(self)

    def run(self):
        server.start()

app = QApplication([])
app.setWindowIcon(QtGui.QIcon('./static/images/favicon.ico'))
win = QWidget()
win.resize(1200, 800)
win.setWindowTitle('Chancecoin')
layout = QVBoxLayout()
win.setLayout(layout)

s = ServerThread()
s.start()

c = ChancecoinThread()
c.start()

view = QWebView()
view.setUrl(QUrl("http://0.0.0.0:8080/"))

button = QtGui.QPushButton("Chancecoin Wallet")
button.clicked.connect(lambda: view.setUrl(QUrl("http://0.0.0.0:8080/")))

layout.addWidget(view)
layout.addWidget(button)

win.show()
app.exec_()
