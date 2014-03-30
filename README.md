# Changelog
* v1.2 - burns from multiple inputs are credited to first input, other minor changes
* v1.1 - new bet resolve logic using NY Lottery Quick Draw
* v1.0 — initial release

# Chancecoin - Participate

## Description

Chancecoin (CHA) is a protocol, coin, and client used to bet on dice rolls in a decentralized casino. Owners of the coin may gamble on dice rolls, with randomness provided by published NY Lottery Quick Draw numbers. Owners of the coin are automatically invested in the house bankroll. The protocol, which is based on Counterparty (XCP), is built on top of the Bitcoin blockchain. Coins are created by burning Bitcoins.

## Burn information

  * **Maximum coins burned**: 1,000,000
  * **Burn period**: Bitcoin blocks 291860 to 298340
  * **Coins burned in first block**: 1,500 CHA per 1 BTC
  * **Coins burned in last block**: 1,000 CHA per 1 BTC (coins per block scaled linearly in between these blocks)
  * **BTC burn address**: [1ChancecoinXXXXXXXXXXXXXXXXXZELUFD][1]
  * **Maximum coins burned per address**: unlimited

## Casino information

  * **House edge**: 2.0%
  * **Maximum win**: 1.0% of bankroll

## Wallet software

## Resources

## How do I buy CHA?

During the burn period, you can burn BTC into CHA using the standard Chancecoin wallet or command line interface. You can also burn BTC into CHA by sending BTC to 1ChancecoinXXXXXXXXXXXXXXXXXZELUFD using a Bitcoin client or Blockchain.info. After the burn period, you can still trade CHA for BTC on the decentralized exchange using the standard Chancecoin wallet or command line interface.

### Burning with the Chancecoin wallet

Open the wallet software and click on "Wallet." Under the "Burn" section, fill in your address and desired quantity to burn. Then click "Burn."

### Burning with the command line interface

Run "python chancecoind.py burn --source SOURCE --quantity QUANTITY"

### Burning with a Bitcoin client

To burn with a Bitcoin client, simply send the amount of BTC you want to burn to 1ChancecoinXXXXXXXXXXXXXXXXXZELUFD. As long as one of the outputs is 1ChancecoinXXXXXXXXXXXXXXXXXZELUFD, the burn will be credited to the first input address.

### Burning with Blockchain.info

To burn using a Blockchain.info wallet, do the following:

  1. Log in to your wallet.
  2. Click "Send Money."
  3. Choose "Quick Send" under "Transaction Type."
  5. Enter 1ChancecoinXXXXXXXXXXXXXXXXXZELUFD for the "To" address.
  6. Enter the amount of BTC you want to burn.
  9. Click "Send Payment."

Note that when you use multiple input addresses, the CHA is credited to the first input address.

## How do I gamble?

You can gamble using the standard Chancecoin wallet or command line interface.

### Gambling with the Chancecoin wallet

Open the wallet software and click on "Casino." Choose the amount of CHA you want to bet, and the desired payout or odds of winning (one will determine the other). Then click "Roll the Dice."

### Gambling with the command line interface

Run "python chancecoind.py bet --source SOURCE --bet BET --chance CHANCE --payout PAYOUT." Note that the chance of winning and the payout must be congruent. This is best illustrated with an example: if the chance of winning is 50 (meaning 50%), then the payout is 1/0.5*(1-0.02)=1.96, where 0.02 is the house edge.

## How do I bankroll the house?

By owning CHA, you are automatically bankrolling the house. On average, you can expect to earn the house edge of 2.0% per bet.

## Donations

Donations to 1BckY64TE6VrjVcGMizYBE7gt22axnq6CM are welcome.

## Developers

[Magician][2] and [Venetian][3]

## Installation instructions

### Prerequisites

  * Install bitcoind or a Bitcoin client with RPC capability (such as Bitcoin-Qt). The txindex option must be enabled.

### From binary

  * Download and run a precompiled Chancecoin wallet binary.
  * When you load the program for the first time, it will tell you where you need to create your configuration file, and it will also show you an example of a valid configuration file. Create this file and fill it in with the details of your Bitcoin RPC server.
  * Restart the Chancecoin wallet and you should be good to go.

### From source

  * Git fetch https://github.com/chancecoin/chancecoin.git.
  * Install python3 and the following prerequisites: urllib3, apsw, requests, appdirs, prettytable, python-dateutil, json-rpc, cherrypy, pycoin, pyzmq(v2.2%2B), tornado.
  * You can run the GUI via gui.py, or the command line interface via chancecoind.py.
  * Either way, you need to create a configuration file first. When you first run the program, it will tell you where you need to create your configuration file. Example.conf is an example of a valid configuration file. Create this file and fill it in with the details of your Bitcoin RPC server.
  * Restart the Chancecoin wallet and you should be good to go.

   [1]: http://blockchain.info/address/1ChancecoinXXXXXXXXXXXXXXXXXZELUFD
   [2]: https://bitcointalk.org/index.php?action=profile;u=252066
   [3]: https://bitcointalk.org/index.php?action=profile;u=272243
