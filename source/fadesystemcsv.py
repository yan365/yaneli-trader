#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.indicators as btind
import backtrader.feeds as btfeeds
import backtrader.analyzers as analyzer
import argparse
import time
from strategies.fadesystem import FadeSystemIB

# Strategy Parameters
MA_PERIOD = 5
STD_PERIOD = 8

def parse_args(pargs=None):
    parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description='IB Strategy')
    
    parser.add_argument(
            '--ma_period', '-p',
            required=False,
            default=MA_PERIOD,
            action='store',
            type=int,
            help='Moving Average period'
            )
    parser.add_argument(
            '--std_period', '-t',
            required=False,
            default=STD_PERIOD,
            action='store',
            type=int,
            help='Standard Deviation period'
            )
    if pargs is not None:
        return parser.parse_args(pargs)
    return parser.parse_args()


def run_strategy(args=None, **kwargs):

    print('[ Configuring Cerebro ]')
    args = parse_args(args)
    
    cerebro = bt.Cerebro()
    
    data = btfeeds.GenericCSVData(
            dataname = 'example.csv',
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

    cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=5)

    cerebro.addstrategy(FadeSystemIB, ma_period=args.ma_period, stddev_period=args.std_period)

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

