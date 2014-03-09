Interacting with the API
=========================

.. warning::

    This API documentation is still in an early state. It contains errors, omissions, etc., and could change drastically at any time.
    

Overview
----------

``chancecoind`` features a full-fledged JSON RPC 2.0-based API, which allows
third-party applications to perform functions on the Chancecoin network
without having to deal with the low‐level details of the protocol such as
transaction encoding and state management.


Connecting to the API
----------------------

By default, ``chancecoind`` will listen on port ``4000`` (if on mainnet) or port ``14000`` (on testnet) for API
requests. API requests are made via a HTTP POST request to ``/jsonrpc/``, with JSON-encoded
data passed as the POST body. For more information on JSON RPC, please see the `JSON RPC 2.0 specification <http://www.jsonrpc.org/specification>`__.

.. _examples:

Python Example
^^^^^^^^^^^^^^^

.. code-block:: python

    import json
    import requests
    from requests.auth import HTTPBasicAuth
    
    url = "http://localhost:4000/jsonrpc/"
    headers = {'content-type': 'application/json'}
    auth = HTTPBasicAuth('rpcuser', 'rpcpassword')
    
    #Fetch all balances for a specific address, using keyword-based arguments
    payload = {
      "method": "get_balances",
      "params": {"filters": {'field': 'address', 'op': '==', 'value': "14qqz8xpzzEtj6zLs3M1iASP7T4mj687yq"}},
      "jsonrpc": "2.0",
      "id": 0,
    }
    response = requests.post(
      url, data=json.dumps(payload), headers=headers, auth=auth).json()
    print("GET_BALANCES RESULT: ", response)

