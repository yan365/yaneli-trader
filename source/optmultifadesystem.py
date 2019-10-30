#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.analyzers as analyzer
import argparse
from strategies.multifadesystem import FadeSystemIB

INITIAL_CASH = 10000.
COMMISSION = 0.002

# Data Parameter
DATAFILES = [
        'EUR.USD-CASH-IDEALPRO',
        'AUD.USD-CASH-IDEALPRO',
        'USD.JPY-CASH-IDEALPRO',
        'GBP.USD-CASH-IDEALPRO',
        'CAD.USD-CASH-IDEALPRO',
        ]

# Strategy Parameters
OPTIMIZE_MA_PERIOD = True
OPTIMIZE_STDDEV_PERIOD = True
OPTIMIZE_STD_THRESHOLD = True
OPTIMIZE_ATR_PERIOD = False
OPTIMIZE_MP_VALUEAREA = True
OPTIMIZE_MP_TICKSIZE = True
OPTIMIZE_STOPLOSS = True
OPTIMIZE_TAKEPROFIT = True
OPTIMIZE_POSITIONTIMEDECAY = True
OPTIMIZE_MINIMUMPRICECHANGE = True


MINIMUMPRICECHANGE = [ 0 ]
STD_THRESHOLD = [ 0, 1, 2 ]
MP_TICKSIZE_RANGE = [ 0, 1 ]
STOPLOSS_RANGE = [0]
TAKEPROFIT_RANGE = [ 0, 1, 2 ]
MA_PERIOD = [6, 8]
STDDEV_PERIOD = [6, 8]
ATR_PERIOD = [5]
MP_VALUEAREA_RANGE = [0.25, 0.3, 0.4]
POSITIONTIMEDECAY = [60*60*2, 60*60*3]


def optimization_params():
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

    if OPTIMIZE_MP_TICKSIZE:
        args.update({ 'mp_ticksize': MP_TICKSIZE_RANGE })

    if OPTIMIZE_STOPLOSS:
        args.update({ 'stoploss': STOPLOSS_RANGE })

    if OPTIMIZE_TAKEPROFIT:
        args.update({ 'takeprofit': TAKEPROFIT_RANGE })

    if OPTIMIZE_POSITIONTIMEDECAY:
        args.update({ 'positiontimedecay': POSITIONTIMEDECAY})

    if OPTIMIZE_MINIMUMPRICECHANGE:
        args.update({ 'minimumchangeprice': MINIMUMPRICECHANGE})

    return args


def run_optimization(args=None, **kwargs):

    print('[ Configuring Cerebro ]')
    params = optimization_params()
    
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
                timeframe = bt.TimeFrame.Ticks,
                )
    
        cerebro.adddata(data)

    strategies = cerebro.optstrategy(
            FadeSystemIB,
            **params)

    cerebro.addanalyzer(analyzer.DrawDown, _name='drawdown')
    cerebro.addanalyzer(analyzer.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Weeks)
    cerebro.addanalyzer(analyzer.PyFolio, _name='pyfolio')

    print('[ Initializing ]')
    results = cerebro.run()

    df_results = pd.DataFrame({
        r[0].params: 
        r[0].analyzers.acctstats.get_analysis() for r in results}
        ).T.loc[:, ['end', 'growth', 'return']]

    print(df_results.head())

    sorted_values = df_results.sort_values('return', ascending= False)
    sorted_values.to_csv(OUTPUT_FILENAME, FILE_DELIMITER)

    print(tabulate(sorted_values))

if __name__ == '__main__':
    run_optimization()

