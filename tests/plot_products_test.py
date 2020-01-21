#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('../source/')

import dataclient
import datetime as dt
from tabulate import tabulate
from ib_insync import *
import matplotlib.pyplot as plt
import datautils as du

HOST = '127.0.0.1'
PORT = 7497
CLIENT_ID = 1234

forex_products = [
        'EURUSD',
        'GBPUSD',
        'AUDUSD',
        ]

def parsedata(data):
    #TODO
    return data

client = dataclient.IBDataClient(HOST, PORT, CLIENT_ID)

data = dict()

for product in forex_products:
    args = {
            'symbol':product,
            'symboltype':'Forex',
            'currency':'USD',
            'exchange':'IDEALPRO',
            'timeframe':'1 hour',
            'durationStr':'1 D',
            }
    _data = client.getdata(**args)
    data.update({product:_data})

i = 1 
for key, value in data.items():
    plt.subplot(2, int(len(data)/2)+1, i)
    plt.plot(value['datetime'], value['Close'])
    plt.title(key)
    plt.grid(True)
    i += 1
    
plt.tight_layout()
plt.show()

i= 0
for key, value in data.items():
    _data = du.parsedataframe(value)
    contract = dataclient.getcontract(forex_products[i], 'Forex')
    # Get Tick Size for Generating Market Profiles
    _ticksize = client.getticksize(contract)
    du.generateprofiles(_data, ticksize = _ticksize, valuearea = 0.7,
            mp_mode='tpo', save_fig=True, name=key)
    i += 1

