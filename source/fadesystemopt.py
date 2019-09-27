#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.feeds as btfeeds
import pandas as pd
import argparse
from tabulate import tabulate
from strategies.fadesystem import FadeSystemIB

# Input File
DEFAULT_FILE = 'dataname.csv'

# Results Output File
OUTPUT_FILENAME = 'out.csv'
FILE_DELIMITER = ','

OPTIMIZE_MA_PERIOD = True
OPTIMIZE_STDDEV_PERIOD = True
OPTIMIZE_STD_THRESHOLD = True
OPTIMIZE_ATR_PERIOD = True
OPTIMIZE_MP_VALUEAREA = True
OPTIMIZE_MP_TICKSIZE = True
OPTIMIZE_STOPLOSS = True
OPTIMIZE_TAKEPROFIT = True
OPTIMIZE_POSITIONTIMEDECAY = True
OPTIMIZE_MINIMUMPRICECHANGE = True

MA_PERIOD_MIN = 10
MA_PERIOD_MAX = 10
MA_PERIOD_STEP = 2
STDDEV_PERIOD_MIN = 10
STDDEV_PERIOD_MAX = 10
STDDEV_PERIOD_STEP = 10
STD_THRESHOLD_MIN = 10
STD_THRESHOLD_MAX = 10
STD_THRESHOLD_STEP = 10
ATR_PERIOD_MIN = 10
ATR_PERIOD_MAX = 10
ATR_PERIOD_STEP = 10
MP_VALUEAREA_RANGE = [0.5]
MP_TICKSIZE_RANGE = [0.2]
STOPLOSS_RANGE = [0.2]
TAKEPROFIT_RANGE = [0.2]
POSITIONTIMEDECAY_MIN = 10
POSITIONTIMEDECAY_MAX = 10
POSITIONTIMEDECAY_STEP = 10
MINIMUMPRICECHANGE_MIN = 10
MINIMUMPRICECHANGE_MAX = 10
MINIMUMPRICECHANGE_STEP = 10

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
        args.update({'ma_period': range(
                MA_PERIOD_MIN, 
                MA_PERIOD_MAX, 
                MA_PERIOD_STEP)})

    if OPTIMIZE_STDDEV_PERIOD:
        args.update({ 'stddev_period': range(
                STDDEV_PERIOD_MIN,
                STDDEV_PERIOD_MAX,
                STDDEV_PERIOD_STEP)})

    if OPTIMIZE_STD_THRESHOLD:
        args.update({'std_threshold': range(
                STD_THRESHOLD_MIN,
                STD_THRESHOLD_MAX,
                STD_THRESHOLD_STEP)})

    if OPTIMIZE_ATR_PERIOD:
        args.update({'atr_period': range(
                ATR_PERIOD_MIN,
                ATR_PERIOD_MAX,
                ATR_PERIOD_STEP)})

    if OPTIMIZE_MP_VALUEAREA:
        args.update({ 'mp_valuearea': MP_VALUEAREA_RANGE })

    if OPTIMIZE_MP_TICKSIZE:
        args.update({ 'mp_ticksize': MP_TICKSIZE_RANGE })

    if OPTIMIZE_STOPLOSS:
        args.update({ 'stoploss': STOPLOSS_RANGE })

    if OPTIMIZE_TAKEPROFIT:
        args.update({ 'takeprofit': TAKEPROFIT_RANGE })

    if OPTIMIZE_POSITIONTIMEDECAY:
        args.update({ 'positiontimedecay': range(
                POSITIONTIMEDECAY_MIN,
                POSITIONTIMEDECAY_MAX,
                POSITIONTIMEDECAY_STEP)})

    if OPTIMIZE_MINIMUMPRICECHANGE:
        args.update({ 'minimumchangeprice': range(
                POSITIONTIMEDECAY_MIN,
                POSITIONTIMEDECAY_MAX,
                POSITIONTIMEDECAY_STEP)})

    return args

def run_optimization(args=None, **kwargs):

    args = parse_args(args)

    params = optimization_params()

    cerebro = bt.Cerebro()
    cerebro.broker.set_cash(10000.)
    cerebro.broker.setcommission(0.02)

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
            timeframe = bt.TimeFrame.Ticks)

    cerebro.adddata(data)
    cerebro.resampledata(
            data, 
            timeframe = bt.TimeFrame.Minutes,
            compression = 5)

    strategies = cerebro.optstrategy(
            FadeSystemIB,
            **params)

    results = cerebro.run()


if __name__ == '__main__':
    run_optimization()
