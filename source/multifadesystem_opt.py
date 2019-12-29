#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.analyzers as analyzer
import argparse
from strategies.multifadesystem import FadeSystemIB
from dataclient import *
import datautils
from strategies.optparams import * 


HOST='127.0.0.1'
PORT = 7497
CLIENTID = 1234

DOWNLOAD_DATA = True # Download the data before optimization
DATA_DURATION = '10 D'
DATA_TIMEFRAME = '1 min'


INITIAL_CASH = 10000.
COMMISSION = 0.002

# Data Parameter
DATAFILES = {
        'EURUSD':Forex('EURUSD', 'IDEALPRO','EUR'),
        'AUDUSD':Forex('AUDUSD', 'IDEALPRO','AUD'),
        'USDJPY':Forex('USDJPY', 'IDEALPRO','USD'),
        'GBPUSD':Forex('GBDUSD', 'IDEALPRO','GBP'),
        }

# Strategy Parameters
OPTIMIZE_MA_PERIOD = True
OPTIMIZE_STDDEV_PERIOD = True
OPTIMIZE_STD_THRESHOLD = True
OPTIMIZE_ATR_PERIOD = False
OPTIMIZE_MP_VALUEAREA = True
OPTIMIZE_STOPLOSS = True
OPTIMIZE_TAKEPROFIT = True
OPTIMIZE_POSITIONTIMEDECAY = True
OPTIMIZE_MINIMUMPRICECHANGE = True


MINIMUMPRICECHANGE = [ 0 ]
STD_THRESHOLD = [ 0, 1, 2 ]
STOPLOSS_RANGE = [0]
TAKEPROFIT_RANGE = [ 0, 1, 2 ]
MA_PERIOD = [6, 8]
STDDEV_PERIOD = [6, 8]
ATR_PERIOD = [5]
MP_VALUEAREA_RANGE = [0.25, 0.3, 0.4]
POSITIONTIMEDECAY = [60*60*2, 60*60*3]


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


def optimization_params(ticksize=dict()):
    args = dict()

    if OPTIMIZE_MA_PERIOD:
        args.update({'ma_period': MA_PERIOD})

    if OPTIMIZE_STDDEV_PERIOD:
        args.update({ 'stddev_period': STDDEV_PERIOD})

    if OPTIMIZE_STD_THRESHOLD:
        args.update({'std_threshold': STD_THRESHOLD})

    if OPTIMIZE_ATR_PERIOD:
        args.update({'atr_period': ATR_PERIOD})

    if OPTIMIZE_MP_VALUEAREA:
        args.update({ 'mp_valuearea': MP_VALUEAREA_RANGE })

    if OPTIMIZE_STOPLOSS:
        args.update({ 'stoploss': STOPLOSS_RANGE })

    if OPTIMIZE_TAKEPROFIT:
        args.update({ 'takeprofit': TAKEPROFIT_RANGE })

    if OPTIMIZE_POSITIONTIMEDECAY:
        args.update({ 'positiontimedecay': POSITIONTIMEDECAY})

    if OPTIMIZE_MINIMUMPRICECHANGE:
        args.update({ 'minimumchangeprice': MINIMUMPRICECHANGE})

    args.update(ticksize)

    return args


def run_optimization(args=None, **kwargs):

    print('[ Get Tick Size]')

    dc = IBDataClient(HOST, PORT, CLIENTID)
    for symbol, contract in DATAFILES.items():
        TICKSIZE_CONFIGURATION.update({symbol:dc.getticksize(contract)})

    datas = dict()
    if DOWNLOAD_DATA:
        for symbol, contract in DATAFILES.items():
            print('[ Downloading Data %s ]' % symbol)
            data = dc.getdata_fromct(
                    contract,
                    DATA_TIMEFRAME,
                    DATA_DURATION)
            datautils.save_data(data, output_filename=symbol)
            datas.update({symbol:data})
    dc.close()

    print('[ Configuring Cerebro ]')
    params = optimization_params(TICKSIZE_CONFIGURATION)
    
    cerebro = bt.Cerebro(maxcpus=1)
    cerebro.broker.set_cash(INITIAL_CASH)
    cerebro.broker.setcommission(COMMISSION)
    
    for symbol, datas in DATAFILES.items():
        _data = btfeeds.GenericCSVData(
                dataname = symbol,
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
    
        cerebro.adddata(_data)

    strategies = cerebro.optstrategy(
            FadeSystemIB,
            **params)

    cerebro.addanalyzer(analyzer.DrawDown, _name='drawdown')
    #cerebro.addanalyzer(analyzer.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Weeks)
    #cerebro.addanalyzer(analyzer.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(AcctStats)

    print('[ Initializing ]')
    results = cerebro.run()

    df_results = pd.DataFrame()
    for result in results:
        for it in result:
            df_results = df_results.append({
                'Lot Config':it.params.lotconfig,
                'Stop Loss':it.params.stoploss,
                'Take Profit':it.params.takeprofit,
                'Std Threshold':it.params.std_threshold,
                'Minimum Price Change':it.params.minimumchangeprice,
                'MA Period':it.params.ma_period,
                'Std Period':it.params.stddev_period,
                'ATR Period':it.params.atr_period,
                'MP Value Area':it.params.mp_valuearea,
                'MP Tick Size':it.params.mp_ticksize,
                'Order Start Time':it.params.starttime,
                'Order Final Time':it.params.orderfinaltime,
                'Time to Close Orders':it.params.timetocloseorders,
                'Time Between Orders':it.params.timebetweenorders,
                'Position Time Decay':it.params.positiontimedecay,
                'Return':it.analyzers.acctstats.get_analysis()['return'],
                'End':it.analyzers.acctstats.get_analysis()['end'],
                'Growth':it.analyzers.acctstats.get_analysis()['growth'],
                'Drawdown':it.analyzers.drawdown.get_analysis(),
                }, ignore_index=True)

    '''df_results = pd.DataFrame({
        r[0].params: 
        r[0].analyzers.acctstats.get_analysis() for r in results}
        ).T.loc[:, ['end', 'growth', 'return']]


    print(df_results.head())
    '''

    sorted_values = df_results.sort_values('return', ascending= False)
    sorted_values.to_csv(OUTPUT_FILENAME, FILE_DELIMITER)

    print(tabulate(sorted_values, headers='keys'))

if __name__ == '__main__':
    run_optimization()

