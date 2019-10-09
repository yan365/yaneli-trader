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
from datautils import save_data
from strategies.exceptions import DirectionNotFound, TradeModeNotFound, OrderNotExecuted

LOG = True
SAVEFIGURES = True
NOTIFY_DATA = True

BELOW_RANGE = 'Below Range'
BELOW_VAL = 'Below VAL'
ABOVE_VAH = 'Above VAH'
ABOVE_RANGE = 'Above Range'

LOTS_CONFIGURATION = [
        [1,2,3,1,2,3],
        [1,2,3,4,5,6],
        ]

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
    
def parsedata(data, from_date=None, to_date=None, size_limit=60*60*24):
    '''Get data from backtrader cerebro and convert
    in a pandas dataframe. The columns names are changed for
    compatibility with Market Profile library. The dataframe 
    can be filtered by date and size.
    '''
    timestamp = []
    datetime = []
    
    #data = st.getdatabyname(dataname)
    # Define maximum size of data
    _size = size_limit if len(data) > size_limit else len(data)

    open = data.open.get(ago=0, size=_size)
    high = data.high.get(ago=0, size=_size)
    low = data.low.get(ago=0, size=_size)
    close = data.close.get(ago=0, size=_size)
    volume = data.volume.get(ago=0, size=_size)

    for i in range(-_size+1, 1,  1):
        timestamp.append(dt.datetime.timestamp(data.datetime.datetime(i)))
        datetime.append(data.datetime.datetime(i))
    
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

def plot_close(data, orders, dataname=''):
    '''Plot close data with orders parameters
    '''
    title = dataname+str(data['datetime'].iloc[\
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

    
class TradeSignalsHandler:

    market_profile = None
    profile_slice = None

    lot_configuration = None

    std_threshold = 0.
    min_pricechange = 0.

    last_orderid = -1

    def __init__(self, dataname, lot_index, valuearea, ticksize, std_threshold,
            min_pricechange, min_ordertime):
        
        self.dataname = dataname
        self.lot_configuration = LOTS_CONFIGURATION[lot_index]
        self.ticksize = ticksize
        self.valuearea = valuearea
        self.std_threshold = std_threshold

        # Trade mode
        self._mode_for_long = NONE
        self._mode_for_short = NONE

        # Check if new High/Low is reached after last trade
        self._last_trade_high = None
        self._last_trade_low = None

        # Last order price
        self._last_longprice = None
        self._last_shortprice= None

        self._last_ordertime = None

        self.min_pricechange = min_pricechange
        self.min_ordertime = min_ordertime

        # Market Profile generated time
        self.mp_gen_time = None

        self._long_daily_orders = 0
        self._short_daily_orders = 0

    def check_std_dev(self, st):
        '''Check if current value of Standard Deviation indicator
        is equal or greater than Standard Deviation Threshold
        '''
        return (st.stddev[self.dataname][0] >= self.std_threshold)
    
    def check_new_highlow(self, st, signal):

        if signal == SHORT:
            if self._last_trade_high is None:
                return True

            if self._last_trade_high < st.getdatabyname(self.dataname).high[0]:
                return True

        elif signal == LONG:
            if self._last_trade_low is None:
                return True

            if self._last_trade_low < st.getdatabyname(self.dataname).low[0]:
                return True

        elif signal == NONE:
            return False
        else:
            raise DirectionNotFound()
        return False
    
    def check_last_order_price(self, st, signal):
        '''Compare current price with last order
        '''
        if signal == LONG:
            if self._last_longprice == None:
                return True

            if self._last_longprice - st.getdatabyname(self.dataname).close[0]  >= self.min_pricechange:
                return True

        elif signal == SHORT:
            if self._last_shortprice == None:
                return True

            if st.getdatabyname(self.dataname).close[0] - self._last_shortprice >= self.min_pricechange:
                return True
        return False

    def set_executed(self, st, direction):

        self._last_ordertime = st.datas[0].datetime.datetime(0)
        if direction == LONG:
            self._last_longprice = st.getdatabyname(self.dataname).close[0]
            self._last_trade_low =  st.getdatabyname(self.dataname).low[0]
            self._long_daily_orders += 1

        elif direction == SHORT:
            self._last_shortprice = st.getdatabyname(self.dataname).close[0]
            self._last_trade_high = st.getdatabyname(self.dataname).high[0]
            self._short_daily_orders += 1


    def check_last_order_time(self, st):
        '''Minimum time for opening a new position
        '''
        if self._last_ordertime is None:
            return True
        if pd.Timestamp(st.datas[0].datetime.datetime(0)) \
                - pd.Timestamp(self._last_ordertime) \
                <= dt.timedelta(hours=st.params.timebetweenorders.hour):
            st.log('DEBUG Order not opened')
            return False
        return True

    def check_orders_limit(self, signal):
        if signal == LONG:
            if len(self.lot_configuration)-1 < self._long_daily_orders:
                return False
        elif signal == SHORT:
            if len(self.lot_configuration)-1 < self._short_daily_orders:
                return False
        return True

    def get_lot_size(self, signal):
        if signal == LONG:
            return self.lot_configuration[self._long_daily_orders]
        elif signal == SHORT:
            return self.lot_configuration[self._short_daily_orders]

    def generate_mp(self, data):
        self.mp_gen_time = data['datetime'][0]
        self.market_profile, self.profile_slice = generateprofiles(
                data, 
                ticksize=self.ticksize,
                valuearea=self.valuearea,
                save_fig=SAVEFIGURES)

    def set_signal_mode(self, data):
        '''
        Switches the mode of catch signals for Long and Short.
        This function is called after Market Profile is
        generated. 
        '''
        #data = st.getdatabyname(self.dataname)
        val, vah = self.profile_slice.value_area

        if data.open[0] >= vah:
           self._mode_for_short = ABOVE_RANGE
        else:
            self._mode_for_short = ABOVE_VAH

        if data.open[0] <= val:
            self._mode_for_long = BELOW_RANGE
        else:
            self._mode_for_long = BELOW_VAL

    def checksignals(self, st):

        mp_signal = self.mpsignal(st.getdatabyname(self.dataname))
        if self.check_std_dev(st):

            conditions = {
                    'Symbol':self.dataname,
                    'Signal':mp_signal,
                    'Last Order Time':self.check_last_order_time(st),
                    'Last Order Price':self.check_last_order_price(st, mp_signal),
                    'New High/Low':self.check_new_highlow(st, mp_signal),
                    'Orders Limit':self.check_orders_limit(mp_signal)
                    }

            if LOG: print(str(conditions))

            if False in conditions.values():
                return NONE
            else:
                return mp_signal
        return NONE


    def mpsignal(self, data):
        '''
        Check the current mode of trade, indicators,
        market profile and close value to 
        sinalize a Long or Short signal or None signal
        '''

        if self.profile_slice is None:
            return NONE

        # Market Profile Range
        min_range, max_range = self.profile_slice.open_range()
        # Market Profile Value Area
        val, vah = self.profile_slice.value_area

        # Long signal
        if self._mode_for_long == BELOW_VAL:
            if data.close[0] < val:
                return LONG

        elif self._mode_for_long == BELOW_RANGE:
            if data.close[0] < min_range:
                return LONG
        else:
            raise TradeModeNotFound()

        # Short signal
        if self._mode_for_short == ABOVE_VAH:
            if data.close[0] > vah:
                return SHORT

        elif self._mode_for_short == ABOVE_RANGE:
            if data.close[0] > max_range:
                return SHORT

        else:
            raise TradeModeNotFound()
        return NONE

    def print_status(self):
        if not LOG:
            return
        val, vah = self.profile_slice.value_area
        min_range, max_range = self.profile_slice.open_range()
        
        # Strategy Params
        df_st = pd.DataFrame({
                'Symbol':self.dataname,
                'STD Threshold':self.std_threshold,
                'Minimum Price':self.min_pricechange,
                'MP Tick Size':self.ticksize,
                'MP Value Area':self.valuearea,
                'Lots':str(self.lot_configuration)
            }, index=[0])

        # Market Profile Info
        df_mp = pd.DataFrame({
                'Date': self.mp_gen_time,
                'Min Range': min_range,
                'Max Range': max_range,
                'VAL':val,
                'VAH':vah,
                'Long Mode': self._mode_for_long,
                'Short Mode': self._mode_for_short,
                }, index=[0])

        # Orders Info
        df_order = pd.DataFrame({
                'Last Trade High':self._last_trade_high,
                'Last Trade Low':self._last_trade_low,
                'Last Long Price':self._last_longprice,
                'Last Short Price':self._last_shortprice,
                'Last Order Time':self._last_ordertime,
                }, index=[0])

        print('[ Signal Mode ] \n'+
                 tabulate(df_st, headers='keys', tablefmt='psql', showindex=False)+'\n',
                 tabulate(df_mp, headers='keys', tablefmt='psql', showindex=False)+'\n',
                 tabulate(df_order, headers='keys', tablefmt='psql', showindex=False))

    def reset(self):
        '''Reset variables
        '''
        self._last_trade_high = None
        self._last_trade_low = None
        self._last_longprice = None
        self._last_shortprice= None
        self._long_daily_orders = 0
        self._short_daily_orders = 0

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
            'ma_period':10,
            'stddev_period':10,
            'std_threshold':0.004,# [0.0004, 0.0005, 0.0006],
            'atr_period':14,
            'mp_valuearea':0.7, # Market Profile Value Area
            'mp_ticksize':0.0002, # Market Profile Tick Size
            'stoploss':0.001,
            'takeprofit':0.002, 
            'starttime':dt.time(0,0,0),
            'orderfinaltime':dt.time(15,0,0),
            'timetocloseorders':dt.time(16,0,0),
            'timebetweenorders':dt.time(0,1,0),
            'positiontimedecay':60*60*2, # Time in seconds to force a stop
            'minimumchangeprice':0.0003, # Minimum price change since last order
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
            self.signals[_data] = TradeSignalsHandler(_data,
                    self.params.lotconfig,
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

            # Get Timestamp 
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
                plot_close(data, self._daily_orders, dataname=_data)
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

            signal = mp.checksignals(self)

            if signal is not NONE:
                self.log('[ %s Signal ] %s' % (signal, _data))
                lots = mp.get_lot_size(_data)
                self.open_order(_data, signal, lots)

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
        self.log('[ Close Position ] %s' % tradeid)
        for i in range(len(self.order_list)-1, 0, -1):
            if order._id == tradeid:
                self.order_list[i].close(self)
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
                if order.check_stops(self) or order.check_timedecay(dt):
                    self.order_list[i].close(self)
                    self.log('Position Closed: %d  Price: %.5f\n%s' % (order._id, close, order.print_order()))
    
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
                self.params.stoploss, self.params.takeprofit, mode=PERCENT)
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
            
            for key, value in self.signals.items():
                #TODO 
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
            save_data(dataframe=open_orders, output_filename=output_fn)

        if len(self.order_history) > 0:
            order_history = pd.DataFrame()
            for order in self.order_history:
                order_history = order_history.append(order.as_dataframe())

            output_his='closed_orders_'+str(self._lastday).replace('-','')+'.csv'
            save_data(dataframe=order_history, output_filename=output_his)

