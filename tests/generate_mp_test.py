#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('../source/')

import dataclient 
import datautils
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
        #Forex('USDEUR','IDEALPRO', 'USD'),
        #Forex('USDGBP','IDEALPRO', 'USD'),
        ]

client = dataclient.IBDataClient(HOST, PORT, CLIENT_ID)

datas = dict()
tick_size = dict()
# Download the Stock data
for stock in STOCKS:
    datas.update({stock.symbol:client.getdata_fromct(stock, timeframe='1 min', duration='2 D')})
    tick_size.update({stock.symbol:client.getticksize(stock)})

# Download the Forex data
for forex in FOREX:
    datas.update({forex.symbol:client.getdata_fromct(forex, timeframe='1 min', duration='2 D')})
    tick_size.update({forex.symbol:client.getticksize(forex)})

# Plot bars 
for key, value in datas.items():
    util.barplot(value.rename(columns={
        'Open':'open',
        'High':'high',
        'Low':'low',
        'Close':'close',
        'datetime':'date',
        }), title=key)
    name = key+'_'+str(value['datetime'].iloc[
        value['datetime'].size-1])+'_'+str(value['datetime'].iloc[0])+'.png'
    name.replace(' ', '_').replace(':', '')

    plt.savefig(name)

# Filter data (1 day) and generate Market Profile
for key, value in datas.items():
    _data = datautils.parsedataframe(value)#TODO from_date, to_date
    datautils.generateprofiles(_data, ticksize=tick_size[key],
            valuearea=0.75, mp_mode='tpo', save_fig=True, name=key)

