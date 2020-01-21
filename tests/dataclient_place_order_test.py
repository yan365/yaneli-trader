# -*- coding: utf-8 -*-

import sys
sys.path.append('../source/')

from dataclient import *
from ib_insync import *

HOST = '127.0.0.1'
PORT = 7497
CLIENTID = 1234


PRICE1 = 1.0555
PRICE2 = 1.0444
SIZE = 20

if __name__ == '__main__':

    # create data client
    client = IBDataClient(HOST, PORT, CLIENTID)

    # create contract
    contract = Forex('EURUSD', 'IDEALPRO', 'EUR')

    # place order
    order1, trade1 = client.limit_short(contract, PRICE1, SIZE)

    print('Order: %s' % order1)
    print('Trade: %s' % trade1)

    client.sleep(5)

    # change order price
    order2, trade2 = client.limit_pricechange(contract, order1, PRICE2)

    print('Order: %s' % order2)
    print('Trade: %s' % trade2)
    
    client.sleep(5)

    # cancel order
    trade3 = client.cancelorder(order2)

    print('Trade: %s' % trade3)

    # check open positions
    positions = client.getpositions()

    print('Positions: %s' % positions)

    client.close()

