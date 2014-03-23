# Changelog
* v1.0—initial release

# Chancecoin - Participate

## Description

Chancecoin is a protocol and coin (CHA) used to bet on dice rolls in a decentralized casino. Owners of the coin may gamble on dice rolls, with randomness provided by Bitcoin block hashes. Owners of the coin are automatically invested in the house bankroll. The protocol, which is based on Counterparty (XCP), is built on top of the Bitcoin blockchain. Coins are created by burning Bitcoins.

## Burn information

  * **Maximum coins burned**: 1,000,000
  * **Burn period**: Bitcoin blocks 291860 to 296180
  * **Coins burned in first block**: 1,500 CHA per 1 BTC
  * **Coins burned in last block**: 1,000 CHA per 1 BTC (coins per block scaled linearly in between these blocks)
  * **BTC burn address**: [1ChancecoinXXXXXXXXXXXXXXXXXZELUFD][1]

## Casino information

  * **House edge**: 2.0%
  * **Maximum win**: 1.0% of bankroll

## Wallet software

## Resources

## How do I buy CHA?

During the burn period, all you need to do is send BTC to 1ChancecoinXXXXXXXXXXXXXXXXXZELUFD. You can do this using Bitcoin wallet software, or using the standard Chancecoin wallet or command line interface.

After the burn period, you can still trade CHA for BTC on the decentralized exchange using the standard Chancecoin wallet or command line interface.

## How do I gamble?

You can gamble using the standard Chancecoin wallet or command line interface. Choose the amount of CHA you want to bet, and the desired payout or odds of winning.

## How do I bankroll the house?

By owning CHA, you are automatically bankrolling the house. As people make bets, your balance will fluctuate. On average, you can expect to earn the house edge of 2.0% per bet.

## Donations

Donations to 1BckY64TE6VrjVcGMizYBE7gt22axnq6CM are welcome.

## Developers

[Magician][2] and [Venetian][3]

## Installation instructions

### Prerequisites

  * Install bitcoind or a Bitcoin client with RPC capability (such as Bitcoin-Qt). The txindex option must be enabled.

### From binary

  * Download and run one of the precompiled Chancecoin wallet binaries.
  * When you load the program for the first time, it will tell you where you need to create your configuration file, and it will also show you an example of a valid configuration file. Create this file and fill it in with the details of your Bitcoin RPC server.
  * Restart the Chancecoin wallet and you should be good to go.

### From source

  * Git fetch https://github.com/chancecoin/chancecoin.git.
  * Install python3 and the following prerequisites: apsw, requests, appdirs, prettytable, python-dateutil, json-rpc, cherrypy, pycoin, pyzmq(v2.2%2B), tornado.
  * You can run the GUI via gui.py, or the command line interface via chancecoind.py.
  * Either way, you need to create a configuration file first. When you first run the program, it will tell you where you need to create your configuration file. Example.conf is an example of a valid configuration file. Create this file and fill it in with the details of your Bitcoin RPC server.
  * Restart the Chancecoin wallet and you should be good to go.

   [1]: http://blockchain.info/address/1ChancecoinXXXXXXXXXXXXXXXXXZELUFD
   [2]: https://bitcointalk.org/index.php?action=profile;u=252066
   [3]: https://bitcointalk.org/index.php?action=profile;u=272243
