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

LOG = False
SAVEFIGURES = False

BELOW_RANGE = 'Below Range'
BELOW_VAL = 'Below VAL'
ABOVE_VAH = 'Above VAH'
ABOVE_RANGE = 'Above Range'

def generateprofiles(dataframe, ticksize=0.5, valuearea = 0.7, 
        mp_mode='tpo', save_fig=True):
    '''Generate Market Profile from pandas Data Frame

    Params:
        - dataframe (required)
        Pandas Data Frame

        - ticksize (default: 0.5)
        Size of ticks in Market Profile

        - valuearea (default: 0.7)
        Value Area parameter for Market Profile

        -mp_mode (default: 'tpo')
        Market Profile mode ('tpo' or 'vol')

        -save_fig (default: True)
        Create and save the Market Profile chart
    '''

    # Generate Market Profile
    mp = MarketProfile(
            dataframe,
            value_area_pct = valuearea,
            tick_size=ticksize,
            open_range_size=pd.to_timedelta(1, 'd'),
            initial_balance_delta=pd.to_timedelta(1, 'h'),
            mode=mp_mode)

    mp_slice = mp[0: len(dataframe.index)]
    profile = mp_slice.profile

    # Save figure
    if save_fig:
        val, vah = mp_slice.value_area
        plt.clf()
        plt.axhline(y=val, color='yellow', linestyle= '-')
        plt.axhline(y=vah, color='blue', linestyle= '-')
        plt.plot(dataframe['Open'].iloc[0], color='red', marker='o')
        fig = profile.plot(kind='barh')
        fig.figure.savefig(
                str(mp_mode+dataframe['datetime'].iloc[
                    dataframe['datetime'].size-1]).
                replace(' ','_').replace(':','')+'.png')
    return profile, mp_slice

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
            'lotsize':[1, 2, 3, 1, 2, 3], 
            'ma_period':10,
            'stddev_period':10,
            'std_threshold':0.0004,
            'atr_period':14,
            'mp_valuearea':0.7, # Market Profile Value Area
            'mp_ticksize':0.0002, # Market Profile Tick Size
            'stoploss':0.005,
            'takeprofit':0.005,
            'starttime':dt.time(0,0,0),
            'orderfinaltime':dt.time(15,0,0),
            'timetocloseorders':dt.time(16,0,0),
            'timebetweenorders':dt.time(0,1,0),
            'positiontimedecay':60*60*2, # Time in seconds to force a stop
            'minimumchangeprice':0.0003, # Minimum price change since last order
            }

    def __init__(self, **kwargs):

        ## Indicators
        self.ma = btind.SimpleMovingAverage(self.datas[1].close, period=self.params.ma_period)
        self.stddev = btind.StandardDeviation(self.datas[1].close, period=self.params.stddev_period)
        self.atr = btind.AverageTrueRange(self.datas[1], period=self.params.atr_period)

        ## Internal Vars
        # Stops
        self._stoploss, self._takeprofit = None, None

        # Order id (for backtrader only)
        self._tradeid = 1

        # Date/Time vars
        self._lastday = None
        self._newday = False
        self._lastordertime = dt.datetime(2000,1,1)

        # Counter for daily orders
        self._longdailyorders = 0
        self._shortdailyorders = 0

        # Market Profile slice
        self._mp_slice = None

        # Trade mode
        self._mode_for_long = NONE
        self._mode_for_short = NONE

        # Check if new High/Low is reached after last trade
        self._last_trade_high = None
        self._last_trade_low = None

        # Order List
        self.order_list = []
        # Used for ploting
        self._daily_orders = []

        # If all positions were already closed
        self._positions_closed = False

        # Last order price
        self._last_longprice = None
        self._last_shortprice= None

    def start(self):
        df = pd.DataFrame({
            'Initial Cash':self.broker.getcash(),
            'MA Period':self.params.ma_period,
            'STD Period':self.params.stddev_period,
            'STD Threshold':self.params.std_threshold,
            'ATR Period':self.params.atr_period,
            'Stop Loss':self.params.stoploss,
            'Take Profit':self.params.takeprofit,
            'Lots':str(self.params.lotsize),
            }, index=[0])

        print('[ Strategy Started ] \n'+
                tabulate(df, headers='keys', tablefmt='psql', showindex=False))

    def next(self):
        if self._lastday == None:
            self._lastday = self.datas[0].datetime.date(0)
            self._last_cron_time = self.datas[0].datetime.time(0)

        now = self.datas[0].datetime.time(0)
        today = self.datas[0].datetime.date(0)

        self.cron_report(now)

        if today > self._lastday:
            # Every day those vars must be changed
            self._newday = True
            self._longdailyorders = 0
            self._shortdailyorders= 0
            self._positions_closed = False
            self._last_longprice = None
            self._last_shortprice= None
            self._last_trade_low = None
            self._last_trade_high = None

        if now >= self.params.starttime and self._newday:
            self._newday = False

            # Get Timestamp 
            lastday_begin = dt.datetime.timestamp(
                    pd.Timestamp(self._lastday))
            lastday_end = dt.datetime.timestamp(
                    pd.Timestamp(self._lastday)+dt.timedelta(days=1))

            # Get day before data
            data = self.parsedata(
                        from_date=lastday_begin, 
                        to_date=lastday_end)

            # Plot data and orders
            self.daily_plot(data, self._daily_orders)

            # Generate Market Profile
            self._mp, self._mp_slice = generateprofiles(
                    data, 
                    ticksize=self.params.mp_ticksize,
                    valuearea=self.params.mp_valuearea,
                    save_fig=SAVEFIGURES)

            self.profilestatistics(self._mp_slice)
            self.set_signal_mode(self._mp_slice)

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
        signal = NONE
        if self._mp_slice is not None:
            signal = self.lookforsignals(self._mp_slice)

        if signal is not NONE:
            self.log('[ %s Signal ]' % signal)
            if (signal == LONG and self._longdailyorders < len(self.params.lotsize) ) or (signal == SHORT and self._shortdailyorders < len(self.params.lotsize)):
                if self.check_last_order_time() and \
                        self.check_last_order_price(signal) and \
                        self.check_new_highlow(signal):
                    self.open_order(signal)
                else:
                    self.log('Minimum period between orders not reached %s ' % self.datas[0].datetime.datetime(0))
            else:
                self.log('Max orders by day reached O:%s H:%s L:%s C:%s' %
                        (self.datas[0].open[0],self.datas[0].high[0],
                        self.datas[0].low[0],self.datas[0].close[0]))

    def check_last_order_price(self, signal):
        '''Compare current price with last order
        '''
        #TODO implement with ATR indicator
        if signal == LONG:
            if self._last_longprice == None:
                return True

            if self._last_longprice - self.datas[0].close[0]  >= self.params.minimumchangeprice:
                return True

        elif signal == SHORT:
            if self._last_shortprice == None:
                return True

            if self.datas[0].close[0] - self._last_shortprice >= self.params.minimumchangeprice:
                return True
        return False


    def check_last_order_time(self):
        '''Minimum time for opening a new position
        '''
        if pd.Timestamp(self.datas[0].datetime.datetime(0)) \
                - pd.Timestamp(self._lastordertime) \
                <= dt.timedelta(hours=self.params.timebetweenorders.hour):
            self.log('DEBUG Order not opened')
            return False
        return True

    def close_positions(self, direction):
        '''Close all positions based on direction parameter.
        If direction is LONG, all Long positions will be closed.
        '''
        for i in range(len(self.order_list)-1, 0, -1):
            order = self.order_list[i]
            if order.side == direction:
                if order.executed and not order.closed:
                    self.order_list[i].close(self)

    def close_position(self, tradeid):
        '''Close position based on parameter id
        '''
        for i in range(len(self.order_list)-1, 0, -1):
            if order._id == tradeid:
                self.order_list[i].close(self)
                #self.order_list.pop(i)
                return

    def check_close_conditions(self):
        '''Check Stop Loss and Take Profit of all opened
        positions and the Time Decay (if configured).
        '''
        close = self.datas[0].close[0]
        dt = self.datas[0].datetime.datetime(0)

        # Iterate each order
        for i in range(len(self.order_list)-1, 0, -1):
            order = self.order_list[i]
            if not order.closed:
                # Check Stops and Time Decay
                if order.check_stops(close) or order.check_timedecay(dt):
                    self.order_list[i].close(self)
                    self.log('Position Closed: %d  Price: %.5f\n%s' % (order._id, close, order.print_order()))
    
    def check_std_dev(self):
        '''Check if current value of Standard Deviation indicator
        is equal or greater than Standard Deviation Threshold
        '''
        return (self.stddev[0] >= self.params.std_threshold)

    def check_new_highlow(self, signal):

        if signal == SHORT:
            if self._last_trade_high is None:
                return True

            if self._last_trade_high < self.datas[1].high[0]:
                return True

        elif signal == LONG:
            if self._last_trade_low is None:
                return True

            if self._last_trade_low < self.datas[1].low[0]:
                return True

        else:
            raise DirectionNotFound()
        return False

    def daily_plot(self, data, orders):
        '''Plot close data with orders parameters
        '''
        title = str(data['datetime'].iloc[\
                data['datetime'].size-1]).\
                replace(' ','_').replace(':','')
        plt.clf()
        plt.plot(data['Close'], linewidth=1)
        plt.title(title)
        plt.grid(True)
        plt.ylabel('Close')
        plt.xlabel('Time')
        plt.tight_layout()

        for order in orders:
            if order.executed_price is not None:

                # Plot Order
                if order.side == LONG:
                    _color = 'blue'
                    plt.plot(order.executed_time, order.executed_price, marker='^', color= _color)
                elif order.side == SHORT:
                    _color = 'red'
                    plt.plot(order.executed_time, order.executed_price, marker='v', color= _color)

                # Plot Stops
                if order._stoploss is not None:
                    plt.plot(order.executed_time, order._stoploss, '_', color= _color)
                if order._takeprofit is not None:
                    plt.plot(order.executed_time, order._takeprofit, '_', color= _color)
        
        plt.savefig(title+'.png')
    
    def lookforsignals(self, market_profile):
        '''
        Check the current mode of trade, indicators,
        market profile and close value to 
        sinalize a Long or Short signal or None signal
        '''
        # Market Profile Range
        min_range, max_range = market_profile.open_range()
        # Market Profile Value Area
        val, vah = market_profile.value_area
        # Check Standard Deviation signal
        if self.check_std_dev():

            # Long signal
            if self._mode_for_long == BELOW_VAL:
                if self.datas[0].close[0] < val:
                    return LONG
            elif self._mode_for_long == BELOW_RANGE:
                if self.datas[0].close[0] < min_range:
                    return LONG
            else:
                raise TradeModeNotFound()

            # Short signal
            if self._mode_for_short == ABOVE_VAH:
                if self.datas[0].close[0] > vah:
                    return SHORT
            elif self._mode_for_short == ABOVE_RANGE:
                if self.datas[0].close[0] > max_range:
                    return SHORT
            else:
                raise TradeModeNotFound()
        return NONE

    def parsedata(self, from_date=None, to_date=None, size_limit=60*60*24):
        '''Get data from backtrader cerebro and convert
        in a pandas dataframe. The columns names are changed for
        compatibility with Market Profile library. The dataframe 
        can be filtered by date and size.
        '''
        timestamp = []
        datetime = []

        # Define maximum size of data
        _size = size_limit if len(self.datas[0]) > size_limit else len(self.datas[0])

        open = self.datas[0].open.get(ago=0, size=_size)
        high = self.datas[0].high.get(ago=0, size=_size)
        low = self.datas[0].low.get(ago=0, size=_size)
        close = self.datas[0].close.get(ago=0, size=_size)
        volume = self.datas[0].volume.get(ago=0, size=_size)
 
        for i in range(-_size+1, 1,  1):
            timestamp.append(dt.datetime.timestamp(self.datas[0].datetime.datetime(i)))
            datetime.append(self.datas[0].datetime.datetime(i))
        
        dataframe = pd.DataFrame({
                'timestamp':timestamp,
                'datetime':datetime,
                'Close':close,
                'High':high,
                'Low':low,
                'Open':open,
                'Volume':volume},
                )

        dataframe['Close'] = dataframe['Close'].astype('float')
        dataframe['Volume'] = dataframe['Volume'].astype('float')

        # To work properly with Market Profile library
        dataframe['datetime'] = pd.to_datetime(dataframe['datetime'],
                format = '%Y-%m-%d %H:%M:%S', 
                infer_datetime_format=True).dt.strftime('%Y%m%d %H:%M')
        dataframe=dataframe.set_index('datetime',drop=False)
        dataframe.index = pd.to_datetime(dataframe.index)

        # Filter by date
        if from_date is not None:
            dataframe = dataframe.query('timestamp >= %s' % str(from_date))
        if to_date is not None:
            dataframe = dataframe.query('timestamp <= %s' % str(to_date))

        return dataframe
    
    def open_order(self, signal):
        '''Open order based on signal parameter.
        '''
        if signal == LONG:
            _lots = self.params.lotsize[self._longdailyorders]
        elif signal == SHORT:
            _lots = self.params.lotsize[self._shortdailyorders]
        order = OrderHandler(
                self._tradeid,
                lots=_lots,
                side=signal,
                )
        order.market_order(self)
        sl, tp = calc_stops(self.datas[0].close[0], signal,
                self.params.stoploss, self.params.takeprofit)
        order.set_stops(sl, tp)
        order.set_timedecay(self.params.positiontimedecay)
        order.print_order()
        self.order_list.append(order)
        self._daily_orders.append(order)

    def profilestatistics(self, profile_slice):
        '''
        Log a table with Market Profile Statistics
        '''
        profile_df = pd.DataFrame(profile_slice.as_dict(), index=[0])
        self.log('[ Profile Statistics ] \n'+
                tabulate(profile_df, headers='keys', tablefmt='psql', showindex=False))
    
    def log(self, txt, dt=None):
        '''Print log messages and date
        '''
        if LOG:
            dt = dt or self.datas[0].datetime.datetime(0)
            print('%s    %s' % (dt.isoformat(), txt))

    def set_signal_mode(self, profile_slice):
        '''
        Switches the mode of catch signals for Long and Short.
        This function is called after Market Profile is
        generated. 
        '''
        val, vah = profile_slice.value_area
        if self.datas[0].open[0] >= vah:
           self._mode_for_short = ABOVE_RANGE
        else:
            self._mode_for_short = ABOVE_VAH

        if self.datas[0].open[0] <= val:
           self._mode_for_long = BELOW_RANGE
        else:
            self._mode_for_long = BELOW_VAL

        # Data Frame
        df = pd.DataFrame({
                'Date':str(self.datas[0].datetime.datetime(0)),
                'Open':self.datas[0].open[0],
                'VAL':val,
                'VAH':vah,
                'Long Mode':self._mode_for_long,
                'Short Mode':self._mode_for_short,
                }, index=[0])

        self.log('[ Signal Mode ] \n'+
                tabulate(df, headers='keys', tablefmt='psql', showindex=False))
 
    def notify_data(self, data, status, *args, **kwargs):
        '''Receive notifications from Broker
        '''
        print(data._getstatusname(status))
        print('%s    %s' % (data, status))
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

            self._last_trade_high = self.datas[1].high[0]
            self._last_trade_low = self.datas[1].low[0]

            if order.isbuy():
                self._longdailyorders += 1
                #self._last_longprice = order.price
                self._last_longprice = self.datas[0].close[0]
            elif order.issell():
                self._shortdailyorders += 1
                #self._last_shortprice = order.price
                self._last_shortprice = self.datas[0].close[0]

            df = pd.DataFrame({
                'Order price': order.price,
                'Order time':self._lastordertime,
                'Close':self.datas[0].close[0],
                'Long daily orders':self._longdailyorders,
                'Short daily orders':self._shortdailyorders,
                }, index=[0])

            self.log('DEBUG \n'+
                    tabulate(df, headers='keys', tablefmt='psql', showindex=False))
            for i in range(len(self.order_list)-1, 0 , -1):
                if self.order_list[i]._id == order.tradeid:
                    if self.order_list[i].executed:
                        self.order_list[i].closed = True
                    else:
                        self.order_list[i].executed = True
                        self.order_list[i]._exec_timestamp = pd.Timestamp(self.datas[0].datetime.datetime(0))
                        self.order_list[i].executed_price = self.datas[0].close[0]
                        self.order_list[i].executed_time = self.datas[0].datetime.datetime(0)

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
                'MA':self.ma[0],
                'Std Dev':self.stddev[0],
                'Open Orders':len(self.order_list),
                'Long Daily Orders':self._longdailyorders,
                'Short Daily Orders':self._shortdailyorders,
                }, index=[0])

        data1 = pd.DataFrame({
                'Open':self.datas[0].open[0],
                'High':self.datas[0].high[0],
                'Low':self.datas[0].low[0],
                'Close':self.datas[0].close[0],
            }, index=[0])

        data2 = pd.DataFrame({
                'Open':self.datas[1].open[0],
                'High':self.datas[1].high[0],
                'Low':self.datas[1].low[0],
                'Close':self.datas[1].close[0],
            }, index=[0])

        self.log('[ CRON Report ] \n'+
                tabulate(df, headers='keys', tablefmt='psql', showindex=False)+'\nData1: \n'+
                tabulate(data1, headers='keys', tablefmt='psql', showindex=False)+'\nData2: \n'+
                tabulate(data2, headers='keys', tablefmt='psql', showindex=False))

    def stop(self):
        self.log('[ Strategy Stop] \nPrinting orders:')
        for order in self.order_list:
            order.print_order()
