#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.indicators as btind

import datetime as dt
import pandas as pd
import matplotlib.pyplot as plt

from tabulate import tabulate

from orderutils import *
from datautils import *
from strategies.fadesystemsignals import *

from strategies.exceptions import DirectionNotFound, TradeModeNotFound, OrderNotExecuted

LOG = False
SAVEFIGURES = False

class FadeSystemIB(bt.Strategy):
    '''
    Params:
        
        - lotsize 
        List with the size of lots in order of execution. Maximum number of orders allowed by day is the length of the list.

        - ma_period (default: 10)
        Period for simple Moving Average Indicator

        - stddev_period (default: 10)
        Period for Standard Deviation Indicator

        - std_threshold (default: 0.1)
        Standard Deviation Equal or Above the threshold is a prerequisite for Long or Short signals

        - mp_valuearea (default: 0.7)
        The Market Profile Value Area parameter

        - mp_ticksize (default: 0.0002)
        The size of ticks in Market Profile

        - stoploss
        Stop Loss value in percentage of price

        - takeprofit
        Take Profit value in percentage of executed price

        - starttime (default: dt.time(0, 0, 0)
        The time of day the strategy can start trade

        - orderfinaltime (default: dt.time(15, 0, 0))
        The time of day the algorithm can't open orders (but can close positions)
        - timetocloseorders (default: dt.time(16,0,0))
        Time of day where all positions must be closed

        -timebetweenorders (default: dt.time(0, 1, 0))
        Minimum time for opening another order

        - positiontimedecay (default: 60*60*2)
        Time in seconds for closing a position after it's opened

        - minimumchangeprice (default:2.0)
        Only open a new position if price have increased (Short) 
        or decreased (Long) this parameter value

    '''

    params = {
            'lotconfig':0,
            'stoploss':0.005,
            'takeprofit':0.005,
            'std_threshold':0.0004,
            # Price Parameter
            'minimumchangeprice':0.0003, 
            # Indicators Period
            'ma_period':10,
            'stddev_period':10,
            'atr_period':14,
            # Market Profile Parameters
            'mp_valuearea':0.7, # Market Profile Value Area
            'mp_ticksize':0.0002, # Market Profile Tick Size
            # Time Parameters
            'starttime':dt.time(0,0,0),
            'orderfinaltime':dt.time(15,0,0),
            'timetocloseorders':dt.time(16,0,0),
            'timebetweenorders':60 * 5,
            'positiontimedecay':60 * 60 * 2, # Time in seconds to force a stop
            # Data Client Parameters
            'dataclient':None,
            'account_number':'',
            }

    def __init__(self, **kwargs):

        ## Indicators
        self.ma = btind.SimpleMovingAverage(self.datas[1].close, period=self.params.ma_period)
        self.stddev = btind.StandardDeviation(self.datas[1].close, period=self.params.stddev_period)
        self.atr = btind.AverageTrueRange(self.datas[1], period=self.params.atr_period)

        # Order Management 
        dataclient = self.params.dataclient
        account = self.params.account_number
        self.order_management = OrdersManagement(self, dataclient, account)

        self.order_management.set_orders_start_time(self.params.starttime)
        self.order_management.set_orders_final_time(self.params.orderfinaltime)
        self.order_management.set_orders_close_time(self.params.timetocloseorders)
        self.order_management.set_time_between_orders(self.params.timebetweenorders) 

        # Trade Signals
        self.signals_handler = TradeSignalsHandler(
                dataname=self.datas[0]._name, 
                valuearea = self.params.mp_valuearea,
                ticksize= self.params.mp_ticksize,
                std_threshold=self.params.std_threshold,
                min_pricechange=self.params.minimumchangeprice)

        self.lot_config = LOTS_CONFIGURATION[self.params.lotconfig]

        ## Internal Vars

        # Order id (for backtrader only)
        self._tradeid = 1

        # Date/Time vars
        self._lastday = None
        self._newday = False
        
        self.orders_allowed = dict()

    def start(self):
        df = pd.DataFrame({
            'Initial Cash':self.broker.getcash(),
            'MA Period':self.params.ma_period,
            'STD Period':self.params.stddev_period,
            'STD Threshold':self.params.std_threshold,
            'ATR Period':self.params.atr_period,
            'Stop Loss':self.params.stoploss,
            'Take Profit':self.params.takeprofit,
            'Lot Config Index':self.params.lotconfig,
            'MP Value Area':self.params.mp_valuearea,
            'Time Decay':self.params.positiontimedecay,
            'Minimum Price':self.params.minimumchangeprice,
            }, index=[0])

        print('[ Strategy Started ] \n'+
                tabulate(df, headers='keys', tablefmt='psql', showindex=False))

    def next(self):

        if self._lastday == None:
            self._lastday = self.datas[0].datetime.date(0)
            self._last_cron_time = self.datas[0].datetime.time(0)

        now = self.datas[0].datetime.time(0)
        today = self.datas[0].datetime.date(0)
        _datetime = self.datas[0].datetime.datetime(0)

        self.cron_report(now)
        self.orders_allowed = self.order_management.next(_datetime)

        _std = self.stddev[0]
        _open = self.datas[0].open[0]
        _high = self.datas[0].high[0]
        _low = self.datas[0].low[0]
        _close = self.datas[0].close[0]


        self.signals_handler.next(_datetime, _std, _open, _high,
                _low, _close)

        if today > self._lastday:
            # Every day those vars must be changed
            self._newday = True

            self.order_management.reset()
            self.signals_handler.reset()

        if self._newday:
            self._newday = False

            # Get Timestamp 
            lastday_begin = dt.datetime.timestamp(
                    pd.Timestamp(self._lastday))
            lastday_end = dt.datetime.timestamp(
                    pd.Timestamp(self._lastday)+dt.timedelta(days=1))

            # Get day before data
            data = parsedata(
                        data=self.datas[0],
                        from_date=lastday_begin, 
                        to_date=lastday_end)

            # Plot data and orders
            plot_orders(data, self.order_management.daily_orders, dataname=str(today))
            self.signals_handler.generate_mp(data)
            self.signals_handler.set_signal_mode()
            self.signals_handler.print_status()

            self._lastday = today

        if not self.order_management.check_time_close_orders():
            self.order_management.close_all_positions()
            return
        
        # Check Stops and Time Decay
        self.order_management.check_close_conditions()

        if 'False' in  self.orders_allowed.values():
            return

        # Check Trade Signals
        signal = self.signals_handler.checksignals()

        if str(signal) != str(NONE):
            if str(signal) == LONG:
                if len(self.lot_config) <= self.order_management.long_daily_orders:
                    return
                lots = self.lot_config[self.order_management.long_daily_orders]
            elif str(signal) == SHORT:
                if len(self.lot_config) <= self.order_management.short_daily_orders:
                    return
                lots = self.lot_config[self.order_management.short_daily_orders]
            self.log('[ %s Signal] %s Lots: %s ' %(signal, self.datas[0]._name, lots))
            # Open Order
            self.open_order(self.datas[0]._name, signal, lots)

    def open_order(self, dataname, signal, lots):
        '''Open order based on signal parameter and lots
        '''
        # Create the order
        order = OrderHandler(
                self._tradeid,
                lots = lots,
                side = signal, 
                symbol = dataname,
                datetime = self.datas[0].datetime.datetime(0))

        self.signals_handler.last_orderid = self._tradeid
        self._tradeid += 1

        # Order parameters
        order.set_timedecay(self.params.positiontimedecay)
        #TODO remove and configure stops based on PnL
        sl, tp =calc_stops(self.datas[0].close[0], order.side, 0.01, 0.01, mode=PERCENT)
        order.set_stops(sl, tp)
        order.print_order()

        # Send the Order to the Order Management object
        self.order_management.market_order(self, order)

    def log(self, txt, dt=None):
        '''Print log messages and date
        '''
        if LOG:
            dt = dt or self.datas[0].datetime.datetime(0)
            print('%s    %s' % (dt.isoformat(), txt))

    def notify_data(self, data, status, *args, **kwargs):
        '''Receive notifications from Broker
        '''
        print(data._getstatusname(status))
        print('%s    %s' % (data, status))
        if status == data.LIVE:
            if self.order_management.dataclient == None:
                self.log('[ Warning ] Data Client is None')

    def notify_order(self, order):
        '''Receive notifications in status changes of orders
        '''
        if order.status == order.Submitted:
            self.log('Order [%d] Submitted' % order.tradeid)

        if order.status == order.Completed:
            if order.tradeid == 0:
                return


            df = pd.DataFrame({
                'Trade Id':order.tradeid,
                'Order price': order.price,
                'Order time':self.datas[0].datetime.datetime(0),
                'Size':order.size,
                'Data Name':order.data._name,
                'Close price':self.getdatabyname(order.data._name).close[0],
                }, index=[0])

            self.log('[ Executed Order ] \n'+
                    tabulate(df, headers='keys', tablefmt='psql', showindex=False))

        if order.status == order.Canceled:
            self.log('Order [%d] Canceled' % order.tradeid)

        if order.status == order.Expired:
            self.log('Order Expired')

        if order.status == order.Accepted:
            self.log('Order Accepted')

        if order.status == order.Rejected:
            self.log('Order Rejected')

        if order.status == order.Partial:
            pass

    def notify_trade(self, trade):
        '''Notify any opening/updating/closing trade
        '''
        self.log('[ Notify Trade ]  Ref: %s  Status: %s  Is closed: %s' % (
            trade.ref, trade.status, trade.isclosed))
        self.order_management.set_exec(trade.ref, trade.tradeid, trade.status, self.datas[0].datetime.datetime(0))

        if not trade.isclosed:
            return
        else:
            self.log('[ Position Closed ]\nGross: %.2f    Net: %.2f' % (trade.pnl, trade.pnlcomm))

    def notify_cashvalue(self, cash, value):
        '''Notify any change in cash or value in broker
        '''
        pass

    def notify_fund(self, cash, value, fundvalue, shares):
        '''Current cash and portfolio in the broker and tradking of fundvalue and shares
        '''
        pass

    def notify_store(self, msg, *args, **kwargs):
        pass

    def cron_report(self, time):
        '''Show current status of strategy, bar values, 
        indicators values and orders
        '''
        if time.hour == self._last_cron_time.hour:
            return
        self._last_cron_time = time

        df = pd.DataFrame({
                'MA':self.ma[0],
                'Std Dev':self.stddev[0],
                'Open Orders':len(self.order_management.order_list),
                'Long Daily Orders':self.order_management.long_daily_orders,
                'Short Daily Orders':self.order_management.short_daily_orders,
                }, index=[0])

        data = pd.DataFrame({
                'Open':self.datas[1].open[0],
                'High':self.datas[1].high[0],
                'Low':self.datas[1].low[0],
                'Close':self.datas[1].close[0],
            }, index=[0])

        self.log('[ CRON Report ] \n'+
                tabulate(df, headers='keys', tablefmt='psql', showindex=False)+'\nData1: \n'+
                tabulate(data, headers='keys', tablefmt='psql', showindex=False))

        order_status = self.order_management.get_order_status()

        self.log('\n'+tabulate(order_status, headers='keys', showindex= False))

    def stop(self):
        self.log('[ Strategy Stop]')
        self.order_management.stop()

