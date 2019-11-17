#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.analyzers as analyzer
import argparse
from strategies.multifadesystem import FadeSystemIB
from dataclient import *
from strategies.optparams import *
import datautils

HOST='127.0.0.1'
PORT = 7497
CLIENTID = 1234

# Download the data used in backtest
DOWNLOAD_DATA = True
DATA_DURATION = '100 D'
DATA_TIMEFRAME = '1 min'

# Broker configuration
INITIAL_CASH = 10000.
COMMISSION = 0.002

# Data Parameter
DATAFILES = {
        #'AMD': Stock('AMD', 'SMART', 'USD'),
        #'ES': Future('ES', '20200501', 'GLOBEX'),
        #'SPX': Option('SPX', '20200401', strike='2890.0',
        #    right='P',exchange='SMART')
        'EURUSD': Forex('EURUSD', 'IDEALPRO','EUR'),
        #'AUDUSD': Forex('AUDUSD', 'IDEALPRO','AUD'),
        #'USDJPY': Forex('USDJPY', 'IDEALPRO','USD'),
        #'GBPUSD': Forex('GBDUSD', 'IDEALPRO','GBP'),
        }

## Strategy Parameters
# Parameters based on index
MINIMUMPRICECHANGE = 0
STD_THRESHOLD = 0
STOPLOSS_RANGE = 0
TAKEPROFIT_RANGE = 0
# Indicators parameters
MA_PERIOD = 6
STDDEV_PERIOD = 6
ATR_PERIOD = 5
# Market Profile Parameter
MP_VALUEAREA_RANGE = 0.75
# Position parameter
POSITIONTIMEDECAY = 60*60*2

class AcctStats(bt.Analyzer):
    
    def __init__(self):
        self.start_val = self.strategy.broker.get_value()
        self.end_val = None

    def stop(self):
        self.end_val = self.strategy.broker.get_value()

    def get_analysis(self):
        return { "start":self.start_val, 
                "end": self.end_val,
                "growth": self.end_val - self.start_val,
                "return": self.end_val/self.start_val}


def run_backtest(args=None, **kwargs):

    dataclient = IBDataClient(HOST, PORT, CLIENTID)

    print('[ Get Tick Size ]')
    for symbol, contract in DATAFILES.items():

        TICKSIZE_CONFIGURATION.update({symbol:dataclient.getticksize(contract)})

    if DOWNLOAD_DATA:

        for symbol, contract in DATAFILES.items():
            print('[ Downloading Data %s ] ' % symbol)
            data = dataclient.getdata_fromct(contract, 
                    DATA_TIMEFRAME,
                    DATA_DURATION)
            datautils.save_data(data, output_filename=symbol)
            print('[ Download Finished: %s ]' % symbol)

    dataclient.close()


    print('[ Configuring Cerebro ]')
    strategy_args = {
            'ma_period': MA_PERIOD,
            'stddev_period': STDDEV_PERIOD,
            'std_threshold': STD_THRESHOLD,
            'atr_period': ATR_PERIOD,
            'mp_valuearea': MP_VALUEAREA_RANGE, 
            'stoploss': STOPLOSS_RANGE,
            'takeprofit': TAKEPROFIT_RANGE,
            'positiontimedecay': POSITIONTIMEDECAY,
            'minimumchangeprice': MINIMUMPRICECHANGE,}

    strategy_args.update(**kwargs)
    
    cerebro = bt.Cerebro(maxcpus=1)
    cerebro.broker.set_cash(INITIAL_CASH)
    cerebro.broker.setcommission(COMMISSION)
    
    for datafile in DATAFILES:
        data = btfeeds.GenericCSVData(
                dataname = datafile,
                nullvalue = 0., 
                dtformat = ('%Y-%m-%d %H:%M:%S'),
                date = 0,
                open = 1,
                high = 2,
                low = 3,
                close = 4,
                volume = 5,
                timeframe = bt.TimeFrame.Minutes,
                )
    
        cerebro.adddata(data)

    strategies = cerebro.addstrategy(
            FadeSystemIB,
            **strategy_args)

    cerebro.addanalyzer(analyzer.DrawDown, _name='drawdown')
    cerebro.addanalyzer(analyzer.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Weeks)
    cerebro.addanalyzer(analyzer.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(AcctStats)

    print('[ Initializing ]')
    results = cerebro.run()

    dd = results[0].analyzers.drawdown.get_analysis()
    sr = results[0].analyzers.sharpe.get_analysis()
    sr_result = 0. if sr['sharperatio'] is None else sr['sharperatio']
    pf = results[0].analyzers.pyfolio.get_pf_items()
    stats = results[0].analyzers.acctstats.get_analysis()

    print('DrawDown: %s' % dd)
    print('Sharpe Ratio: %.2f' % sr_result)
    print('Cash: %.2f' % cerebro.broker.getcash())
    print('Return: %.2f' % stats['return'])

    print('[ Ploting ]')

    cerebro.plot(
            volume=True,
            stdstats=True,
            style='candles')

if __name__ == '__main__':
    run_backtest()

