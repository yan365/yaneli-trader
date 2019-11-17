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
        'duration':'2 Y',
        'whatToShow':'MIDPOINT',
        'outputfile':'EUR.USD-CASH-IDEALPRO',
        }

dataclient.run(**args)

args = {
        'host':HOST,
        'port':PORT,
        'clientid':CLIENT_ID,
        'symbol':'AUDUSD',
        'symboltype':'Forex',
        'exchange':'IDEALPRO',
        'currency':'USD',
        'timeframe':'1 min',
        'duration':'2 Y',
        'whatToShow':'MIDPOINT',
        'outputfile':'AUD.USD-CASH-IDEALPRO',
        }

dataclient.run(**args)

args = {
        'host':HOST,
        'port':PORT,
        'clientid':CLIENT_ID,
        'symbol':'USDJPY',
        'symboltype':'Forex',
        'exchange':'IDEALPRO',
        'currency':'JPY',
        'timeframe':'1 min',
        'duration':'2 Y',
        'whatToShow':'MIDPOINT',
        'outputfile':'USD.JPY-CASH-IDEALPRO',
        }

dataclient.run(**args)

args = {
        'host':HOST,
        'port':PORT,
        'clientid':CLIENT_ID,
        'symbol':'GBPUSD',
        'symboltype':'Forex',
        'exchange':'IDEALPRO',
        'currency':'USD',
        'timeframe':'1 min',
        'duration':'2 Y',
        'whatToShow':'MIDPOINT',
        'outputfile':'GBP.USD-CASH-IDEALPRO',
        }

dataclient.run(**args)

args = {
        'host':HOST,
        'port':PORT,
        'clientid':CLIENT_ID,
        'symbol':'CADUSD',
        'symboltype':'Forex',
        'exchange':'IDEALPRO',
        'currency':'USD',
        'timeframe':'1 min',
        'duration':'2 Y',
        'whatToShow':'MIDPOINT',
        'outputfile':'CAD.USD-CASH-IDEALPRO',
        }

dataclient.run(**args)

