#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.analyzers as analyzer
import argparse
from strategies.fadesystem import FadeSystemIB
import datautils
from dataclient import *
from ib_insync import *

# IB Parameters
HOST = '127.0.0.1'
PORT = 7497
CLIENTID = 1234

# CSV data file name
DATANAME = 'EURUSD'

# Data Parameters
DOWNLOAD_DATA = False
CONTRACT = Forex('EURUSD', 'IDEALPRO', 'EUR') 
DATA_TIMEFRAME = '1 min'
DATA_DURATION = '20 D'

# Strategy Default Parameters
MA_PERIOD = 5
STD_PERIOD = 8
STD_THRESHOLD = 0.00008
STOPLOSS = 3000
TAKEPROFIT = 3000
MP_VALUEAREA = 0.75
POSITION_TIME_DECAY = 60*60
MINIMUM_PRICE_CHANGE = 0.0001

def parse_args(pargs=None):
    parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description='IB Strategy')

    parser.add_argument(
            '--ma_period', '-ma',
            required=False,
            default=MA_PERIOD,
            action='store',
            type=int,
            help='Moving Average period'
            )

    parser.add_argument(
            '--std_period', '-std',
            required=False,
            default=STD_PERIOD,
            action='store',
            type=int,
            help='Standard Deviation period'
            )
    
    parser.add_argument(
            '--std_threshold', '-thr',
            required=False,
            default=STD_THRESHOLD,
            action='store',
            type=float,
            help='Standard Deviation THRESHOLD'
            )

    parser.add_argument(
            '--stoploss', '-stop',
            required=False,
            default=STOPLOSS,
            action='store',
            type=float,
            help='Stop Loss'
            )
    
    parser.add_argument(
            '--takeprofit', '-take',
            required=False,
            default=TAKEPROFIT,
            action='store',
            type=float,
            help='Take Profit'
            )
    
    parser.add_argument(
            '--value_area', '-va',
            required=False,
            default=MP_VALUEAREA,
            action='store',
            type=float,
            help='Market Profile Value Area'
            )
    
    parser.add_argument(
            '--time_decay', '-td',
            required=False,
            default=POSITION_TIME_DECAY,
            action='store',
            type=int,
            help='Time Decay of the position'
            )
    
    parser.add_argument(
            '--minimum_price', '-mp',
            required=False,
            default=MINIMUM_PRICE_CHANGE,
            action='store',
            type=int,
            help='Minimum price change for opening a new order'
            )

    if pargs is not None:
        return parser.parse_args(pargs)
    return parser.parse_args()


def run_strategy(args=None, **kwargs):

    print('[ Configuring Cerebro ]')
    args = parse_args(args)

    dataclient = IBDataClient(HOST, PORT, CLIENTID)
    
    ticksize = dataclient.getticksize(CONTRACT)
    if DOWNLOAD_DATA:
        print('[ Downloading Data ]')
        data = dataclient.getdata_fromct(
                contract=CONTRACT,
                timeframe=DATA_TIMEFRAME,
                duration=DATA_DURATION)

        datautils.save_data(data, output_filename=DATANAME)

    dataclient.close()
    
    cerebro = bt.Cerebro()
    
    data = btfeeds.GenericCSVData(
            dataname = DATANAME,
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

    cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=5)

    strategy_args = {
            'ma_period':args.ma_period,
            'stddev_period':args.std_period,
            'std_threshold':args.std_threshold,
            'mp_valuearea':args.value_area,
            'mp_ticksize':ticksize,
            'stoploss':args.stoploss,
            'takeprofit':args.takeprofit,
            'positiontimedecay':args.time_decay,
            'minimumchangeprice':args.minimum_price, 
            }

    cerebro.addstrategy(FadeSystemIB, **strategy_args)

    cerebro.addanalyzer(analyzer.DrawDown, _name='drawdown')
    cerebro.addanalyzer(analyzer.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Weeks)
    cerebro.addanalyzer(analyzer.PyFolio, _name='pyfolio')

    print('[ Initializing ]')
    result = cerebro.run()

    dd = result[0].analyzers.drawdown.get_analysis()
    sr = result[0].analyzers.sharpe.get_analysis()
    sr_result = 0. if sr['sharperatio'] is None else sr['sharperatio']
    pf = result[0].analyzers.pyfolio.get_pf_items()

    print('DrawDown: %s' % dd)
    print('Sharpe Ratio: %.2f' % sr_result)
    print('Cash: %.2f' % cerebro.broker.getcash())

    print('[ Ploting ]')

    cerebro.plot(
            volume=True,
            stdstats=True,
            style='candles')

if __name__ == '__main__':
    run_strategy()

