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
        'USD.JPY-CASH-IDEALPRO',
        'GBP.USD-CASH-IDEALPRO',
        'CAD.USD-CASH-IDEALPRO',
        ]

STOCKS = []

FUTURES = []

HOST = '127.0.0.1'
PORT = 7497
CLIENTID = 1234

STRATEGY_PARAMS = {
        "lotconfig": 1,
        "std_threshold": 1,
        "stoploss": 0,
        "takeprofit": 1,
        "minimumchangeprice":0,
        "mp_ticksize":0,
        # Indicators
        "ma_period": 8,
        "stddev_period":6,
        "atr_period":14,
        "mp_valuearea": 0.25,
        # Time
        "starttime":dt.time(0, 0, 0),
        "orderfinaltime":dt.time(15,0,0),
        "timetocloseorders":dt.time(16,0,0),
        "timebetweenorders":dt.time(0,1,0),
        # Position Time
        "positiontimedecay":60*60*2,
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
            "timeout":2.0,
            "timerefresh":10,
            "_debug":False,
            }

    ibstore = bt.stores.IBStore(**broker_args)
    cerebro.setbroker(ibstore.getbroker())

    for dataname in FOREX:

        data_args = {
                "dataname": dataname,
                "timeframe": bt.TimeFrame.Minutes,
                "compression": 1,
                #"historical":False,
                #"fromdate":dt.datetime(2019,10,1),
                #"todate":dt.datetime(2019,10,7)
                }
        data = ibstore.getdata(**data_args)
        print("[ Add Data ] %s" % dataname)
        cerebro.adddata(data)

    for dataname in STOCKS:
        
        data_args = {
                "dataname": dataname,
                "timeframe": bt.TimeFrame.Minutes,
                "compression": 1,
                #"historical":False,
                #"fromdate":dt.datetime(2019,10,1),
                #"todate":dt.datetime(2019,10,7)
                }
        data = ibstore.getdata(**data_args)
        print("[ Add Data ] %s" % dataname)
        cerebro.adddata(data)

    for dataname in FUTURES:

        data_args = {
                "dataname": dataname,
                "timeframe": bt.TimeFrame.Minutes,
                "compression": 1,
                #"historical":False,
                #"fromdate":dt.datetime(2019,10,1),
                #"todate":dt.datetime(2019,10,7)
                }
        data = ibstore.getdata(**data_args)
        print("[ Add Data ] %s" % dataname)
        cerebro.adddata(data)

    cerebro.addstrategy(FadeSystemIB, **STRATEGY_PARAMS)

    print("[ Running Cerebro ]")
    cerebro.run()

    cerebro.plot()

if __name__ == '__main__':
    run_live()

