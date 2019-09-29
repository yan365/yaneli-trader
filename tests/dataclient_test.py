#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('../source/')

import dataclient
import datetime as dt

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
        'currency':'USD',
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
print('\nForex Test:')
print(data.head())

args = {
        'symbol':'AUDUSD',
        'symboltype':'Forex',
        'exchange':'IDEALPRO',
        'currency':'USD',
        'timeframe':'1 hour',
        'fromdate':dt.datetime(2019,9,23),
        'todate':dt.datetime(2019,9,24)
        }

data2 = client.getdata_dt(**args)
print(data2.head())
print(data2.tail())


args = {
        'symbol':'AMD',
        'conId':'4391',
        'symboltype':'Stock',
        'exchange':'SMART',
        'currency':'USD',
        'primaryExchange':'NASDAQ',
        'localSymbol':'AMD',
        'tradingClass':'SCM',
        'timeframe':'1 hour',
        'fromdate':dt.datetime(2019,9,23),
        'todate':dt.datetime(2019,9,24)
        }

data3 = client.getdata_dt(**args)
print('\nStock test:')
print(data3.head())
print(data3.tail())

args = {
        'symbol':'SPX',
        'conId':'350155156',
        'symboltype':'Option',
        'exchange':'SMART',
        'currency':'USD',
        'lastTradeDateOrContractMonth':'20191001',
        'right':'P',
        'multiplier':'100',
        'tradingClass':'SPX',
        'localSymbol':'SPX   190418P02890000',
        'strike':'2890.0',
        'timeframe':'1 hour',
        'fromdate':dt.datetime(2019,9,23),
        'todate':dt.datetime(2019,9,24)
        }

data4 = client.getdata_dt(**args)
print('\nOption test:')
print(data4.head())
print(data4.tail())

client.close()

