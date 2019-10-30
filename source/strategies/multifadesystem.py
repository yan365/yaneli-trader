#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.indicators as btind
import datetime as dt
import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate
from market_profile import MarketProfile
from strategies.orderutils import *

from strategies.exceptions import DirectionNotFound, TradeModeNotFound, OrderNotExecuted

import datautils as du
import strategies.fadesystemsignals as sig
from optparams import *

LOG = True
SAVEFIGURES = True
NOTIFY_DATA = True

BELOW_RANGE = 'Below Range'
BELOW_VAL = 'Below VAL'
ABOVE_VAH = 'Above VAH'
ABOVE_RANGE = 'Above Range'

class FadeSystemIB(bt.Strategy):
    '''
    Params:
        
        - lotconfig
        Set the configuration index for lot size. The trade signal object
        handle the lot size for each order

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
            'mp_ticksize':0, # Market Profile Tick Size
            'stoploss':0,
            'takeprofit':0, 
            'minimumchangeprice':0,
            'ma_period':10,
            'stddev_period':10,
            'std_threshold':0.004,# [0.0004, 0.0005, 0.0006],
            'atr_period':14,
            'mp_valuearea':0.7, # Market Profile Value Area
            'starttime':dt.time(0,0,0),
            'orderfinaltime':dt.time(15,0,0),
            'timetocloseorders':dt.time(16,0,0),
            'timebetweenorders':dt.time(0,1,0),
            'positiontimedecay':60*60*2, # Time in seconds to force a stop
            }

    def __init__(self, **kwargs):

        ## Indicators and Signals Handler
        self.ma = dict()
        self.stddev = dict()
        self.atr = dict()
        self.signals = dict()

        for _data in self.getdatanames():

            self.ma[ _data ] = btind.SimpleMovingAverage(self.getdatabyname(_data), period=self.params.ma_period)

            self.stddev[ _data ] = btind.StandardDeviation(self.getdatabyname(_data), period=self.params.stddev_period)
            self.atr[ _data ] = btind.AverageTrueRange(self.getdatabyname(_data), period=self.params.atr_period)
          
            # Create signals trade handler for each data
            self.signals[_data] = sig.TradeSignalsHandler(_data,
                    self.params.lotconfig,
		    self.params.stoploss,
		    self.params.takeprofit,
                    self.params.mp_valuearea, 
                    self.params.mp_ticksize, 
                    self.params.std_threshold,
                    self.params.minimumchangeprice,
                    self.params.timebetweenorders)

        ## Internal Vars
        # Order id (for backtrader only)
        self._tradeid = 1

        # Date/Time vars
        self._lastday = None
        self._newday = False
        self._lastordertime = dt.datetime(2000,1,1)

        # Open Orders List
        self.order_list = []
        # History Order List
        self.order_history = []
        # Used for ploting
        self._daily_orders = []

        # If all positions were already closed
        self._positions_closed = False

    def start(self):
        if LOG:

            df = pd.DataFrame({
                'Initial Cash':self.broker.getcash(),
                'MA Period':self.params.ma_period,
                'STD Period':self.params.stddev_period,
                'STD Threshold':str(self.params.std_threshold),
                'ATR Period':self.params.atr_period,
                'Stop Loss':str(self.params.stoploss),
                'Take Profit':str(self.params.takeprofit),
                'Lot Config Index':self.params.lotconfig,
                'MP Value Area':self.params.mp_valuearea,
                'MP Tick Size':self.params.mp_ticksize,
                'Time Decay':self.params.positiontimedecay,
                'Minimum Price':self.params.minimumchangeprice,
                }, index=[0])

            print('[ Strategy Started ] \n'+
                    tabulate(df, headers='keys', tablefmt='psql', showindex=False))

    def next(self):
        if self._lastday == None:
            self._lastday = self.datas[0].datetime.date(0)
            self._last_cron_time = self.datas[0].datetime.time(0)

        # The first data added will define the datetime
        now = self.datas[0].datetime.time(0)
        today = self.datas[0].datetime.date(0)

        self.cron_report(now)

        if today > self._lastday:
            # Every day those vars must be changed
            self._newday = True
            self._positions_closed = False
            for dataname in self.getdatanames():
                # Reset trade signals handler variables
                self.signals[dataname].reset()

        if now >= self.params.starttime and self._newday:
            self._newday = False

            # Get timestamp of previous day
            lastday_begin = dt.datetime.timestamp(
                    pd.Timestamp(self._lastday))
            lastday_end = dt.datetime.timestamp(
                    pd.Timestamp(self._lastday)+dt.timedelta(days=1))

            for _data in self.getdatanames():

                # Get data from day before
                data = parsedata(self.getdatabyname(_data),
                            from_date=lastday_begin, 
                            to_date=lastday_end)

                # Plot data and orders
                du.plot_close(data, self._daily_orders, dataname=_data)
                # Generate Market Profile
                self.signals[_data].generate_mp(data)
                self.signals[_data].set_signal_mode(self.getdatabyname(_data))
                self.signals[_data].print_status()

            self._lastday = today
            self._daily_orders = [] 

        if now >= self.params.timetocloseorders and not self._positions_closed:
            # Time to close all current positions
            self.close_positions(LONG)
            self.close_positions(SHORT)
            self._positions_closed = True
            return

        # Stops and Time Decay
        self.check_close_conditions()

        if now >= self.params.orderfinaltime:
            # Not time for creating orders
            return

        for _data in self.getdatanames():
            signal = NONE
            mp = self.signals[_data]

            # The strategy don't allow multiple orders in short time
            if st.datas[0].datetime.datetime(0) < self._last_order_time + dt.timedelta(seconds=self.minimum_order_time):
                return
            signal = mp.checksignals(self)

            if str(signal) != str(NONE):
                lots = mp.get_lot_size(_data)
                self.log('[ %s Signal ] %s Lots: %s' % (signal, _data, lots))
                self.open_order(_data, signal, lots)

    def close_positions(self, direction):
        '''Close all positions based on direction parameter.
        If direction is LONG, all Long positions will be closed.
        '''
        for i in range(len(self.order_list)-1, 0, -1):
            order = self.order_list[i]
            if str(order.side) == str(direction):
                if order.executed and not order.closed:
                    self.order_list[i].close(self)

    def close_position(self, tradeid):
        '''Close position based on parameter id
        '''
        self.log('[ Close Position ] %s' % tradeid)
        for i in range(len(self.order_list)-1, 0, -1):
            if str(order._id) == str(tradeid):
                self.order_list[i].close(self)
                return

    def check_close_conditions(self):
        '''Check Stop Loss and Take Profit of all opened
        positions and the Time Decay (if configured).
        '''
        dt = self.datas[0].datetime.datetime(0)

        # Iterate each order
        for i in range(len(self.order_list)-1, -1, -1):
            order = self.order_list[i]
            if not order.closed:
                # Check Stops and Time Decay
                if order.check_stops(self) or order.check_timedecay(dt):
                    self.order_list[i].close(self)
                    self.log('[ Position Closed ] Id: %d  Price: %.5f\n%s' % (order._id, order.print_order()))
    
    def open_order(self, dataname, signal, lots):
        '''Open order based on signal parameter.
        '''
        self.log('[ Open Order ] %s %s' % (dataname, signal))

        order = OrderHandler(
                self._tradeid,
                lots = lots,
                side = signal,
                symbol = dataname
                )

        self.signals[dataname].last_orderid = self._tradeid
        order.market_order(self)
        sl, tp = calc_stops(self.getdatabyname(dataname).close[0], signal,
                self.params.stoploss, self.params.takeprofit, mode=VALUE)
        order.set_stops(sl, tp)
        order.set_timedecay(self.params.positiontimedecay)
        order.print_order()
        self.order_list.append(order)
        self._daily_orders.append(order)


    def log(self, txt, dt=None):
        '''Print log messages and date
        '''
        if LOG:
            dt = dt or self.datas[0].datetime.datetime(0)
            print('%s    %s' % (dt.isoformat(), txt))

    def notify_data(self, data, status, *args, **kwargs):
        '''Receive notifications from Broker
        '''
        if not NOTIFY_DATA:
            return
        print('%s    %s' % (data._getstatusname(status), status))
        if status == data.LIVE:
            pass

    def notify_order(self, order):
        '''Receive notifications in status changes of orders
        '''
        if order.status == order.Submitted:
            self.log('Order [%d] Submitted' % order.tradeid)

        if order.status == order.Completed:
            self.log('Order [%d] Completed' % order.tradeid)
            self._tradeid += 1

            self._lastordertime = self.datas[0].datetime.datetime(0)
            
            for key, value in self.signals.items():
                if value.last_orderid == order.tradeid:
                    signal = LONG if order.isbuy() else SHORT
                    self.signals[key].set_executed(self, signal)
                    df = pd.DataFrame({
                            'Symbol': key,
                            'Trade Id': order.tradeid,
                            'Order price': order.price,
                            'Order time': self._lastordertime,
                            'Close': self.getdatabyname(key).close[0],
                            }, index=[0])
                    self.log('[ Executed Order ] \n'+
                            tabulate(df, headers='keys', tablefmt='psql', showindex=False))
                    break

            for i in range(len(self.order_list)-1, 0 , -1):
                if self.order_list[i]._id == order.tradeid:
                    if self.order_list[i].executed:
                        # Trade in opposite direction happened
                        self.order_list[i].closed = True
                        
                        self.order_list[i].closed_time = self.getdatabyname(self.order_list[i].symbol).datetime.datetime(0)
                        self.order_list[i].closed_price = order.price

                        _order = self.order_list[i]
                        self.order_history.append(_order)
                        self.order_list.pop(i)

                    else:
                        self.order_list[i].executed = True
                        self.order_list[i]._exec_timestamp = pd.Timestamp(
                                self.getdatabyname(self.order_list[i].symbol).datetime.datetime(0))
                        self.order_list[i].executed_price = self.getdatabyname(self.order_list[i].symbol).close[0]
                        self.order_list[i].executed_time = self.getdatabyname(self.order_list[i].symbol).datetime.datetime(0)
                        
                        _order = self.order_list[i]
                        self.order_history.append(_order)
                        self.order_list.pop(i)
                    break

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
        if not trade.isclosed:
            return
        else:
            self.log('[ Notify Trade ]\nGross: %.2f    Net: %.2f' % (trade.pnl, trade.pnlcomm))

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
                'Open Orders':len(self.order_list),
                'Closed Orders':len(self.order_history)
                }, index=[0])
        self.log('[ CRON Report ] \n'+
                tabulate(df, headers='keys', 
                    tablefmt='psql', showindex=False))

        for _data in self.getdatanames():
            dataframe = pd.DataFrame({
                    'Dataname': _data,
                    'MA':self.ma[_data][0],
                    'Std Dev':self.stddev[_data][0],
                    'Open':self.getdatabyname(_data).open[0],
                    'High':self.getdatabyname(_data).high[0],
                    'Low':self.getdatabyname(_data).low[0],
                    'Close':self.getdatabyname(_data).close[0],
                }, index=[0])

            self.log('\n'+tabulate(dataframe, headers='keys', tablefmt='psql', showindex=False))

    def stop(self):

        self.log('[ Strategy Stop ]\n[ Open Orders ]')
        for order in self.order_list:
            order.print_order() 

        if len(self.order_list) > 0:
            open_orders = pd.DataFrame()

            for order in self.order_list:
                open_orders = open_orders.append(order.as_dataframe())


            output_fn= 'open_orders_'+str(self._lastday).replace('-','')+'.csv'
            du.save_data(dataframe=open_orders, output_filename=output_fn)

        if len(self.order_history) > 0:
            order_history = pd.DataFrame()
            for order in self.order_history:
                order_history = order_history.append(order.as_dataframe())

            output_his='closed_orders_'+str(self._lastday).replace('-','')+'.csv'
            save_data(dataframe=order_history, output_filename=output_his)

