#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.analyzers as analyzer
import pandas as pd
import argparse
from tabulate import tabulate
from strategies.fadesystem import FadeSystemIB
from ib_insync import *
from dataclient import *
import datautils

# Input File
DEFAULT_FILE = 'GBPUSD'
CONTRACT = Forex('GBPUSD', 'IDEALPRO', 'GBP')

# TWS Parameters
HOST='127.0.0.1'
PORT = 7497
CLIENTID = 1234

# Data Parameters
DOWNLOAD_DATA =  False
DATA_DURATION = '3 D'
DATA_TIMEFRAME = '1 min'

# Results Output File
OUTPUT_FILENAME = 'results.csv'
FILE_DELIMITER = ','

# Optimization Parameters
OPTIMIZE_MA_PERIOD = True
OPTIMIZE_STDDEV_PERIOD = True
OPTIMIZE_STD_THRESHOLD = True
OPTIMIZE_ATR_PERIOD = True
OPTIMIZE_MP_VALUEAREA = True
OPTIMIZE_STOPLOSS = True
OPTIMIZE_TAKEPROFIT = True
OPTIMIZE_POSITIONTIMEDECAY = True
OPTIMIZE_MINIMUMPRICECHANGE = True

MA_PERIOD = [5, 10]#[5, 10, 15]
STDDEV_PERIOD = [6]#[6, 8, 10, 12]
STD_THRESHOLD = [0.0008]#[0.0008, 0.001]
ATR_PERIOD = [10]#[10, 14, 18]
MP_VALUEAREA_RANGE = [0.7]#[0.5, 0.7]
STOPLOSS_RANGE = [0.2]
TAKEPROFIT_RANGE = [0.2]
POSITIONTIMEDECAY = [60*60]#[ 60*60, 60*60*2]
MINIMUMPRICECHANGE = [0.0002]#[ 0.0002, 0.0004]

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

def parse_args(pargs=None):

    parser = argparse.ArgumentParser(
            formatter_class = argparse.ArgumentDefaultsHelpFormatter,
            description='Fade System Optimization'
            )

    parser.add_argument(
            '--data', '-d',
            required= False,
            default= DEFAULT_FILE,
            action= 'store',
            type= str,
            help= 'Input File Name')

    if pargs is not None:
        return parser.parse_args(pargs)
    return parser.parse_args()

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

    args = parse_args(args)

    params = optimization_params()
    client = IBDataClient(HOST, PORT, CLIENTID)
    ticksize = client.getticksize(CONTRACT)
    params.update({'mp_ticksize':ticksize})

    if DOWNLOAD_DATA:
        print('[ Downloading Data ]')
        data = client.getdata_fromct(
                CONTRACT,
                DATA_TIMEFRAME,
                DATA_DURATION)
        datautils.save_data(data, output_filename=args.data)
    client.close()

    cerebro = bt.Cerebro()
    cerebro.broker.set_cash(10000.)
    cerebro.broker.setcommission(0.002)

    data = btfeeds.GenericCSVData(
            dataname = args.data,
            nullvalue = 0.,
            dtformat = ('%Y-%m-%d %H:%M:%S'),
            date = 0,
            open = 1,
            high = 2,
            low = 3,
            close = 4,
            volume = 5,
            timeframe = bt.TimeFrame.Minutes)

    cerebro.adddata(data)
    cerebro.resampledata(
            data, 
            timeframe = bt.TimeFrame.Minutes,
            compression = 5)

    cerebro.addanalyzer(analyzer.DrawDown, _name='drawdown')
    #cerebro.addanalyzer(analyzer.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Weeks)
    #cerebro.addanalyzer(analyzer.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(AcctStats)

    strategies = cerebro.optstrategy(
            FadeSystemIB,
            **params)

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


    sorted_values = df_results.sort_values('Return', ascending= False)
    sorted_values.to_csv(OUTPUT_FILENAME, FILE_DELIMITER)

    print(tabulate(sorted_values, headers='keys'))

if __name__ == '__main__':
    run_optimization()

