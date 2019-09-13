#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('../source/')

import dataclient

HOST = '127.0.0.1'
PORT = 7497
CLIENT_ID = 1234

args = {
        'host':HOST,
        'port':PORT,
        'clientid':CLIENT_ID,
        'symbol':'EURUSD',
        'symboltype':'Forex',
        'exchange':'IDEALPRO',
        'currency':'EUR',
        'timeframe':'1 min',
        'duration':'10 D',
        'whatToShow':'MIDPOINT',
        'outputfile':'eurusd.csv',
        }

dataclient.run(**args)


client = dataclient.IBDataClient(HOST, PORT, CLIENT_ID)
oldbar = client.earliestbar(
        symbol= 'EURUSD', 
        symboltype='Forex',
        exchange='IDEALPRO',
        )
print('Earliest Bar: ' % (oldbar))

args = {
        'symbol':'EURUSD',
        'symboltype':'Forex',
        'exchange':'IDEALPRO',
        'currency':'USD',
        'timeframe':'1 day',
        'duration':'100 D',
        }

data = client.getdata(**args)
data.head()
client.close()

