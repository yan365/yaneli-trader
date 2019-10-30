#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append('../source/')

import backtrader as bt
import datetime as dt
from strategies.multifadesystem import FadeSystemIB

SYMBOLS = [
        'EUR.USD-CASH-IDEALPRO',
        'AUD.USD-CASH-IDEALPRO',
        'GBP.USD-CASH-IDEALPRO',
        ]

HOST = '127.0.0.1'
PORT = 7497
CLIENTID = 1234


def run(*args, **kwargs):
    cerebro = bt.Cerebro(live= True)

    broker_args = {
            "host":HOST,
            "port":PORT,
            "clientId":CLIENTID,
            "notifyall":True,
            "reconnect":100,
            "timeout":2.0,
            "timerefresh":10,
            "_debug":False,
            }

    ibstore = bt.stores.IBStore(**broker_args)
    cerebro.setbroker(ibstore.getbroker())

    for dataname in SYMBOLS:

        data_args = {
                "dataname": dataname,
                "timeframe": bt.TimeFrame.Minutes,
                "compression": 1,
                #"historical":True,
                #"fromdate":dt.datetime(2019,10,10),
                #"todate":dt.datetime(2019,10,14)
                }

        data = ibstore.getdata(**data_args)
        print("[ Add Data ] %s" % dataname)
        cerebro.adddata(data)

    strategy_params = {
            # Parameters with index
            'lotconfig':0,
            'std_threshold':1,
            'stoploss':1,
            'takeprofit':1,
            'mp_ticksize':1,
            'minimumchangeprice':1,
            # Indicators
            'ma_period':8,
            'stddev_period':6,
            'atr_period':14,
            # Market Profile
            'mp_valuearea':0.6,
            # Date and Time parameters
            'starttime':dt.time(0,0,0),
            'orderfinaltime':dt.time(15,0,0),
            'timetocloseorders':dt.time(15,50,0),
            'timebetweenorders':dt.time(0,0,15),
            # Position Time Decay
            'positiontimedecay':60*15,
            }

    cerebro.addstrategy(FadeSystemIB, **strategy_params)

    cerebro.run()

if __name__ == '__main__':
    run()
