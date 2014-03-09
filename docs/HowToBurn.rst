How to Burn Bitcoin (to generate CHA)
======================================

.. warning::

   This document is valid only between Bitcoin blocks 278310 and 283810.
   Do not try burning after this period has ended. 


Using chancecoind
----------------------

``chancecoind`` is the preferred way to "burn" BTC to generate CHA. To burn BTC, configure ``bitcoind`` and
install ``chancecoind``.

Once done, you can open up a command prompt, then, just run the command like::

    chancecoind burn --source=<ADDRESS> --quantity=<QUANTITY>
    #under Linux
    
    C:\python33\python.exe C:\chancecoind_build\run.py burn --source=<ADDRESS> --quantity=<QUANTITY>
    #under Windows
    
Full examples::

    chancecoind burn --source=1J6Sb7BbhCQKRTwmt8yKxXAAQByeNsED7P --quantity=0.5
    #under Linux
    
    C:\python33\python.exe C:\chancecoind_build\run.py burn --source=1J6Sb7BbhCQKRTwmt8yKxXAAQByeNsED7P --quantity=0.005
    #under Windows
 

Without using chancecoind
-------------------------------------------

.. warning::

    **DISCLAIMER:** The format of a Chancecoin transaction is very specific, and we can’t guarantee that a
    transaction constructed by any other software will work (and if it doesn’t, you’ll lose your BTC).

    You may make multiple sends from a single address to the Chancecoin burn address, **as long as the
    total amount of BTC sent from that address is not greater than 1 BTC**.

The requirements for a successful "burn":

- All of the input addresses are identical.
- The address of the **first** output is the unspendable address.
- The total number of BTC burned by the source address is less than or equal to 1.

