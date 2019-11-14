#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.analyzers as analyzer
import argparse
from strategies.multifadesystem import FadeSystemIB
from dataclient import *
from strategies.optparams import *

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
        'EURUSD': Forex('EURUSD', 'IDEALPRO','EUR'),
        'AUDUSD': Forex('AUDUSD', 'IDEALPRO','AUD'),
        'USDJPY': Forex('USDJPY', 'IDEALPRO','USD'),
        'GBPUSD': Forex('GBDUSD', 'IDEALPRO','GBP'),
        }

# Strategy Parameters
MINIMUMPRICECHANGE = [ 0 ]
STD_THRESHOLD = [ 0, 1, 2 ]
STOPLOSS_RANGE = [0]
TAKEPROFIT_RANGE = [ 0, 1, 2 ]
MA_PERIOD = [6, 8]
STDDEV_PERIOD = [6, 8]
ATR_PERIOD = [5]
MP_VALUEAREA_RANGE = [0.25, 0.3, 0.4]
POSITIONTIMEDECAY = [60*60*2, 60*60*3]


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
                timeframe = bt.TimeFrame.Ticks,
                )
    
        cerebro.adddata(data)

    strategies = cerebro.addstrategy(
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
    run_backtest()

