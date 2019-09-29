#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.analyzers as analyzer
import argparse
from strategies.fadesystem import FadeSystemIB

# Strategy Parameters
SYMBOL = 'EUR.USD-CASH-IDEALPRO'
INIT_DATE = dt.datetime(2014,1,1)
END_DATE = dt.datetime(2018,1,1)
MA_PERIOD = 5
STD_PERIOD = 8

# IB Parameters
HOST = '127.0.0.1'
PORT = 7497  # Live: 7496 
CLIENTID = 1234


def parse_args(pargs=None):
    parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description='IB Strategy')
    
    parser.add_argument(
            '--symbol', '-s',
            required=False, 
            default = SYMBOL, 
            help='Symbol to be used')
    
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
    
    cerebro = bt.Cerebro(
            #maxcpus=1, 
            live=False)
    
    broker_args = {
        "host":HOST,
        "port":PORT,
        "clientId":CLIENTID,
        "notifyall":True, 
        "_debug":True,
        "reconnect":3,
        "timeout":2.0,
    }

    ibstore = bt.stores.IBStore(**broker_args)
    cerebro.setbroker(ibstore.getbroker())

    data_args = {
        "dataname":args.symbol,
        "fromdate":INIT_DATE,
        "todate":END_DATE,
        #"sessionstart":,
        #"sessionend":,
        "timeframe":bt.TimeFrame.Seconds,
        "compression":1,
        "historical":True
    }

    data_args.update(**kwargs)

    data = ibstore.getdata(**data_args)
    
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

