# Changelog
* v1.0—initial release

# Description
Chancecoin is a protocol for betting on dice rolls in a decentralized, trustless fashion. 
It uses Bitcoin as a transport layer. The contents of this repository, `chancecoind`, 
constitute the reference implementation of the protocol.

The Chancecoin protocol specification may be found at
<https://github.com/chancecoin/chancecoin>.

# Dependencies
* [Python 3](http://python.org)
* Python 3 packages: apsw, requests, appdirs, prettytable, python-dateutil, json-rpc, cherrypy, pycoin, pyzmq(v2.2+), tornado
* Bitcoind

# Installation

*NOTE: This section covers manual installation of chancecoind.

In order for chancecoind to function, it must be able to communicate with a
running instance of Bitcoind or Bitcoin-Qt, which handles many Bitcoin‐specific
matters on its behalf, including all wallet and private key management. For
such interoperability, Bitcoind must be run with the following options:
`-txindex=1` `-server=1`. This may require the setting of a JSON‐RPC password,
which may be saved in Bitcoind’s configuration file.

chancecoind needs to know at least the JSON‐RPC password of the Bitcoind with
which it is supposed to communicate. The simplest way to set this is to
include it in all command‐line invocations of chancecoind, such as
`./chancecoind.py --rpc-password=PASSWORD ACTION`. To make this and other
options persistent across chancecoind sessions, one may store the desired
settings in a configuration file specific to chancecoind.

Note that the syntaxes for the countpartyd and the Bitcoind configuraion
files are not the same. A Bitcoind configuration file looks like this:

	rpcuser=bitcoinrpc
	rpcpassword=PASSWORD
	testnet=1
	txindex=1
	server=1

However, a chancecoind configuration file looks like this:

	[Default]
	bitcoind-rpc-password=PASSWORD

Note the change in hyphenation between ‘rpcpassword’ and ‘rpc-password’.

If and only if chancecoind is to be run on the Bitcoin testnet, with the
`--testnet` CLI option, Bitcoind must be set to do the same (`-testnet=1`).
chancecoind may run with the `--testcoin` option on any blockchain,
however.

The test suite is invoked with `py.test`.

# Usage
The command‐line syntax of chancecoind is generally that of
`./chancecoind.py {OPTIONS} ACTION {ACTION-OPTIONS}`. There is a one action
per message type, which action produces and broadcasts such a message; the
message parameters are specified following the name of the message type. There
are also actions which do not correspond to message types, but rather exist to
provide information about the state of the Chancecoin network, e.g. current
balances or open orders.

For a summary of the command‐line arguments and options, see
`./chancecoind.py --help`.