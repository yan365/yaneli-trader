#!/usr/bin/env python
# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.indicators as btind

import datetime as dt
import pandas as pd
import matplotlib.pyplot as plt

from tabulate import tabulate
from market_profile import MarketProfile

from datautils import *
from orderutils import *
from strategies.fadesystemsignals import *
from strategies.optparams import *

from strategies.exceptions import DirectionNotFound, TradeModeNotFound, OrderNotExecuted

LOG = True
SAVEFIGURES = True
NOTIFY_DATA = True

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
            'stoploss':0,
            'takeprofit':0, 
            'std_threshold':0,
            # Price Parameter
            'minimumchangeprice':0,
            # Indicators Period
            'ma_period':10,
            'stddev_period':10,
            'atr_period':14,
            # Market Profile Parameter
            'mp_valuearea':0.7,
            # Time Parameters
            'starttime':dt.time(0,0,0),
            'orderfinaltime':dt.time(15,0,0),
            'timetocloseorders':dt.time(16,0,0),
            'timebetweenorders':60 * 5,
            'positiontimedecay':60*60*2, # Time in seconds to force a stop
            }

    def __init__(self, **kwargs):

        ## Indicators and Signals Handler
        self.ma = dict()
        self.stddev = dict()
        self.atr = dict()
        self.signals = dict()

        # Order Management
        self.order_management = OrdersManagement(self, None, None)

        self.order_management.set_orders_start_time(self.params.starttime)
        self.order_management.set_orders_final_time(self.params.orderfinaltime)
        self.order_management.set_orders_close_time(self.params.timetocloseorders)
        self.order_management.set_time_between_orders(self.params.timebetweenorders)

        for _data in self.getdatanames():

            self.ma[ _data ] = btind.SimpleMovingAverage(self.getdatabyname(_data), period=self.params.ma_period)

            self.stddev[ _data ] = btind.StandardDeviation(self.getdatabyname(_data), period=self.params.stddev_period)
            self.atr[ _data ] = btind.AverageTrueRange(self.getdatabyname(_data), period=self.params.atr_period)
          
            # Create signals trade handler for each data
            self.signals[_data] = TradeSignalsHandler(
                    dataname=_data,
                    valuearea=self.params.mp_valuearea, 
                    ticksize=TICKSIZE_CONFIGURATION[_data], 
                    std_threshold=STD_THRESHOLD_CONFIGURATION[self.params.std_threshold][_data],
                    min_pricechange=MINIMUM_PRICE_CONFIGURATION[self.params.minimumchangeprice][_data])

        # Lot configuration is handled by the strategy
        self.lot_config = LOTS_CONFIGURATION[self.params.lotconfig]

        ## Internal Vars
        # Order id (for backtrader only)
        self._tradeid = 1

        # Date/Time vars
        self._lastday = None
        self._newday = False

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
        _datetime = self.datas[0].datetime.datetime(0)

        self.cron_report(now)
        self.order_management.next(_datetime)
        for key, value in self.signals.items():
            self.signals[key].next(
                    datetime=_datetime,
                    std_value=self.stddev[key][0],
                    open=self.getdatabyname(key).open[0],
                    high=self.getdatabyname(key).high[0],
                    low=self.getdatabyname(key).low[0],
                    close=self.getdatabyname(key).close[0]
                    )

        if today > self._lastday:
            # Every day those vars must be changed
            self._newday = True

            for dataname in self.getdatanames():
                # Reset trade signals handler variables
                self.signals[dataname].reset()
            self.order_management.reset()

        if self._newday:
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
                plot_orders(data, self.order_management.daily_orders, dataname=_data)
                # Generate Market Profile
                self.signals[_data].generate_mp(data)

                self.signals[_data].set_signal_mode()
                self.signals[_data].print_status()

            self._lastday = today

        if self.order_management.check_time_close_orders():
            self.order_management.close_all_positions()
            return

        # Check Stops and Time Decay
        self.order_management.check_close_conditions()

        if not self.order_management.check_order_final_time():
            # Not time for creating orders
            return

        for _data in self.getdatanames():
            # Check Trade Signals
            signal = self.signals[_data].checksignals()

            if str(signal) != str(NONE):
                # Get lot size 
                if str(signal) == LONG:
                    lots = self.lot_config[
                        self.order_management.long_daily_orders]

                elif str(signal) == SHORT:
                    lots = self.lot_config[
                        self.order_management.short_daily_orders]

                self.log('[ %s Signal ] %s Lots: %s' % (signal, _data, lots))
                # Open the order
                self.open_order(_data, signal, lots)
                #self._last_order_time = st.datas[0].datetime.datetime(0)
    
    def open_order(self, dataname, signal, lots):
        '''Open order based on signal parameter and lots
        '''
        # Create the order
        order = OrderHandler(
                self._tradeid,
                lots = lots,
                side = signal,
                symbol = dataname,
                datetime = self.datas[0].datetime.datetime(0)
                )

        self.signals[dataname].last_orderid = self._tradeid
        self._tradeid += 1

        # Order parameters
        order.set_timedecay(self.params.positiontimedecay)
        #TODO remove
        sl, tp = calc_stops(self.getdatabyname(dataname).close[0], 
                order.side, 0.01, 0.01, mode=PERCENT)
        order.set_stops(sl, tp)
        order.print_order()

        # Send the order to the Order Management object
        self.order_management.market_order(order)

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
            if self.order_management.dataclient == None:
                self.log('[ WARNING ] Data Client is None')

    def notify_order(self, order):
        '''Receive notifications in status changes of orders
        '''
        if order.status == order.Submitted:
            self.log('Order [%d] Submitted' % order.tradeid)

        if order.status == order.Completed:
            self.log('Order [%d] Completed' % order.tradeid)

            self.order_management.set_executed(order.tradeid, self.getdatabyname(order.data), self.datas[0].datetime.datetime(0))
            self.order_management.update_orders()

            df = pd.DataFrame({
                    'Trade Id': order.tradeid,
                    'Order price': order.price,
                    'Order time': self.datas[0].datetime.datetime(0),
                    'Size':order.size,
                    'Data Name':order.data._name,
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

        self.log('[ CRON Report ]')

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
        self.log('[ Strategy Stop ]')
        self.order_management.stop()

