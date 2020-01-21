#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.analyzers as analyzer
import datetime as dt
from dataclient import *
from strategies.optparams import TICKSIZE_CONFIGURATION
from ib_insync import *
from dataclient import *
from strategies.multifadesystem import FadeSystemIB

FOREX = {
        'EUR.USD-CASH-IDEALPRO': Forex('EURUSD','IDEALPRO', 'EUR'),
        'AUD.USD-CASH-IDEALPRO': Forex('AUDUSD','IDEALPRO', 'AUD'),
        'USD.JPY-CASH-IDEALPRO': Forex('USDJPY','IDEALPRO', 'USD'),
        'GBP.USD-CASH-IDEALPRO': Forex('GBPUSD','IDEALPRO', 'GBP'),
        }

STOCKS = {}

FUTURES = {}

HOST = '127.0.0.1'
PORT = 7497
CLIENTID_BT = 1234
CLIENTID_DC = 1222

def run_live(args=None, **kwargs):

    print('[ Configuring Cerebro ]')
    cerebro = bt.Cerebro(live= True)

    broker_args = {
            "host":HOST,
            "port":PORT,
            "clientId":CLIENTID_BT,
            "notifyall":True,
            "reconnect":100,
            "timeout":2.0,
            "timerefresh":10,
            "_debug":False,
            }

    ibstore = bt.stores.IBStore(**broker_args)
    cerebro.setbroker(ibstore.getbroker())
    
    dataclient = IBDataClient(HOST, PORT, CLIENTID_DC)

    for dataname, contract in FOREX.items():

        TICKSIZE_CONFIGURATION.update({
            dataname:dataclient.getticksize(contract)})

        data_args = {
                "dataname": dataname,
                "timeframe": bt.TimeFrame.Minutes,
                "compression": 1,
                #"historical":False,
                #"fromdate":dt.datetime(2019,10,1),
                #"todate":dt.datetime(2019,10,7),
                "rtbar":True,
                }
        data = ibstore.getdata(**data_args)
        print("[ Add Data ] %s" % dataname)
        cerebro.adddata(data)
    
    for dataname, contract in STOCKS.items():
        
        TICKSIZE_CONFIGURATION.update({
            dataname:dataclient.getticksize(contract)})
        
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

        TICKSIZE_CONFIGURATION.update({dataname:dataclient.getticksize(contract)})

    for dataname, contract in FUTURES.items():
        
        TICKSIZE_CONFIGURATION.update({
            dataname:dataclient.getticksize(contract)})

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

    strategy_params = {
            "lotconfig": 1,
            "std_threshold": 1,
            "stoploss": 0,
            "takeprofit": 1,
            "minimumchangeprice":1,
            # Indicators
            "ma_period": 8,
            "stddev_period":6,
            "atr_period":14,
            "mp_valuearea": 0.25,
            # Time
            "starttime":dt.time(0, 0, 0),
            "orderfinaltime":dt.time(15,0,0),
            "timetocloseorders":dt.time(16,0,0),
            "timebetweenorders":60 * 5,
            # Position Time
            "positiontimedecay":60*60*2,
            # Data Client Object
            "dataclient":dataclient,
            }


    cerebro.addstrategy(FadeSystemIB, **strategy_params)

    print("[ Running Cerebro ]")
    cerebro.run()
    
    dataclient.close()

    cerebro.plot()

if __name__ == '__main__':
    run_live()

