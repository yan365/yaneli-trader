#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('../source/')

import dataclient 
import datetime as dt
from ib_insync import *
import matplotlib.pyplot as plt

HOST = '127.0.0.1'
PORT = 7497
CLIENT_ID = 1234

STOCKS = [
        Stock('AMD', 'SMART', 'USD'),
        Stock('TSLA', 'SMART', 'USD'),
        Stock('TWTR', 'SMART', 'USD'),
        ]

FOREX = [
        Forex('EURUSD','IDEALPRO', 'EUR'),
        Forex('GBPUSD','IDEALPRO', 'GBP'),
        ]

client = dataclient.IBDataClient(HOST, PORT, CLIENT_ID)

datas = dict()
# Download the Stock data
for stock in STOCKS:
    datas.update({stock.symbol+'_1m':client.getdata_fromct(stock, timeframe='1 min', duration='1 D')})
    datas.update({stock.symbol+'_1h':client.getdata_fromct(stock, timeframe='1 hour', duration='1 W')})
    datas.update({stock.symbol+'_1d':client.getdata_fromct(stock, timeframe='1 day', duration='1 M')})

# Download the Forex data
for forex in FOREX:
    datas.update({forex.symbol+'_1m':client.getdata_fromct(forex, timeframe='1 min', duration='1 D')})
    datas.update({forex.symbol+'_1h':client.getdata_fromct(forex, timeframe='1 hour', duration='1 W')})
    datas.update({forex.symbol+'_1d':client.getdata_fromct(forex, timeframe='1 day', duration='1 M')})

# Plot data
i=1
for key, value in datas.items():
    plt.subplot(2, int(len(datas)/2)+1, i)
    plt.plot(value['datetime'], value['Close'])
    plt.title(key)
    plt.grid(True)
    i += 1

plt.tight_layout()
plt.show()

