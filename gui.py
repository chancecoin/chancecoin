import sys,signal,os,threading
from threading import Thread
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
from PyQt4.QtNetwork import *
from PyQt4 import QtGui, QtCore
import time

import server
import chancecoind
from lib import (config, util, exceptions, bitcoin, blocks)
from lib import (send, order, btcpay, bet, burn, cancel)

class ChancecoinThread(QtCore.QThread):
    def __init__(self):
        QtCore.QThread.__init__(self)

    def run(self):
        try:
            chancecoind.set_options()
            db = util.connect_to_db()
            blocks.follow(db)
        except:
            pass

class ServerThread(QtCore.QThread):
    def __init__(self):
        QtCore.QThread.__init__(self)

    def run(self):
        server.start()

if getattr(sys, 'frozen', False):
    file_frozen = sys.executable
else:
    file_frozen = __file__

app = QApplication([])
app.setWindowIcon(QtGui.QIcon("./static/images/favicon.ico"))
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
view.setUrl(QUrl("http://127.0.0.1:8080/"))

button = QtGui.QPushButton("Chancecoin Wallet")
button.clicked.connect(lambda: view.setUrl(QUrl("http://127.0.0.1:8080/")))

layout.addWidget(view)
layout.addWidget(button)

win.show()
app.exec_()
