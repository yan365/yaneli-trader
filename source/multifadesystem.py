#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.analyzers as analyzer
import datetime as dt

from strategies.multifadesystem import FadeSystemIB

FOREX = [
        'EUR.USD-CASH-IDEALPRO', 
        'AUD.USD-CASH-IDEALPRO',
        ]

STOCKS = [
        'AAPL-STK-SMART-USD',
        'TWTR-STK-SMART', 
        ]


HOST = '127.0.0.1'
PORT = 7497
CLIENTID = 1234

STRATEGY_PARAMS = {
        "lotsize":[1, 2, 3, 1, 2, 3],
        "ma_period": 8,
        "stddev_period":6,
        "atr_period":14,
        "mp_valuearea": 0.6,
        "mp_ticksize":0.0002,
        "stoploss":0.005,
        "takeprofit":0.005,
        "starttime":dt.time(0, 0, 0),
        "orderfinaltime":dt.time(15,0,0),
        "timetocloseorders":dt.time(16,0,0),
        "timebetweenorders":dt.time(0,1,0),
        "positiontimedecay":60*60*2,
        "minimumchangeprice":0.0003
        }


def run_live(args=None, **kwargs):
    print('[ Configuring Cerebro ]')
    
    cerebro = bt.Cerebro(live= True)

    broker_args = {
            "host":HOST,
            "port":PORT,
            "clientId":CLIENTID,
            "notifyall":True,
            "reconnect":100,
            "timeout":2.0
            }

    ibstore = bt.stores.IBStore(**broker_args)
    cerebro.setbroker(ibstore.getbroker())

    for dataname in FOREX:

        data_args = {
                "dataname": dataname,
                "timeframe": bt.TimeFrame.Minutes,
                "compression": 1,
                }
        data = ibstore.getdata(**data_args)
        print("[ Add Data ] %s" % dataname)
        cerebro.adddata(data)

    for dataname in STOCKS:
        
        data_args = {
                "dataname": dataname,
                "timeframe": bt.TimeFrame.Minutes,
                "compression": 5,
                }

    cerebro.addstrategy(FadeSystemIB, **STRATEGY_PARAMS)

    cerebro.run()

    cerebro.plot()

