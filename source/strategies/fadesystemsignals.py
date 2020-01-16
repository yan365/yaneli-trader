# -*- coding: utf-8 -*-

from orderutils import *
import datautils as du
from strategies.optparams import *
import datetime as dt

# Mode of trading signals
BELOW_RANGE = 'Below Range'
BELOW_VAL = 'Below VAL'
ABOVE_VAH = 'Above VAH'
ABOVE_RANGE = 'Above Range'

class TradeSignalsHandler(object):
    '''This class handles the signals rules for Fade System Strategy.
    The functions 'next', 'generate_mp', 'set_signal_mode' and 'reset'
    must be called by the algorithm running the instance of this class.
 
    Parameters:

       - dataname 

       - std_threshold

       - min_pricechange

       - ticksize

       Minimum price change for sending another signal. The value can be None, which means that this rule is deactivated

       - valuearea (default: 0.7)

       The Value Area parameter for generating Market Profiles

       - signals_interval (default: 60*5)

       Minimum time in seconds for sending another signal

    '''

    def __init__(self, dataname, std_threshold, min_pricechange, ticksize, valuearea=0.7, signals_interval = 60*5):
        
        self.dataname = str(dataname)

        self.valuearea = float(valuearea)
        
        self.std_threshold = float(std_threshold)

        self.min_pricechange = float(min_pricechange)

        self.ticksize = float(ticksize)
    
        self.signals_time_interval = signals_interval

        # Market Profile
        self.market_profile = None
        self.profile_slice = None

        # Trade mode
        self._mode_for_long = NONE
        self._mode_for_short = NONE

        # Check if new High/Low is reached after last trade
        self._last_trade_high = None
        self._last_trade_low = None

        # Last order price
        self._last_longprice = None
        self._last_shortprice= None

        # Market Profile generated time
        self._mp_gen_time = None
    
        self._last_signal_time = None

    def next(self, datetime, std_value, open, high, low, close):
        '''This function should be called every time new data
        '''
        self.now = datetime
        self.std = std_value
        self.open = open
        self.high = high
        self.low = low
        self.close = close

    def check_last_mp_time(self):
        '''Check if Market Profile was generated in the last day
        '''
        return True

    def check_parameters(self):
        '''Check if parameters don't break any rule for this signal handler
        '''
        pass

    def check_std_dev(self):
        '''Check if current value of Standard Deviation indicator
        is equal or greater than Standard Deviation Threshold
        '''
        return (self.std >= self.std_threshold)

    def check_new_high(self):
        '''For sending another Short signal the strategy require
        the current close price be higher than price of last signal
        '''
        if self._last_trade_high is None:
            return True
        if self._last_trade_high < self.close:
            return True
        return False
    
    def check_new_low(self):
        '''For sending another Long signal the strategy require
        the current close price be lower than price of last signal
        '''
        if self._last_trade_low is None:
            return True
        if self._last_trade_low < self.close:
            return True
        return False
    
    def check_last_order_price(self, signal):
        '''Compare current price with last order and check if reached
        the minimum price change parameter
        '''
        if signal == LONG:
            # if parameter is empty don't need to check
            if self._last_longprice == None:
                return True

            if self._last_longprice - self.close  <= self.min_pricechange:
                return False

        elif signal == SHORT:
            # if parameter is empty don't need to check
            if self._last_shortprice == None:
                return True

            if self.close - self._last_shortprice <= self.min_pricechange:                
                return False
        return True

    def check_last_signal_time(self):
        '''Minimum time for opening a new position
        '''
        if self._last_signal_time == None:
            return True

        if pd.Timedelta(self.now - self._last_signal_time).total_seconds() <= self.signals_time_interval:
            return False
        return True

    def generate_mp(self, data, dataname=''):
        '''Generate Market Profile. The signal handler need this function 
        to be called every beginning of cycle. This function is not 
        called internally.
        '''
        self._mp_gen_time = data['datetime'][0]
        self.market_profile, self.profile_slice = du.generateprofiles(
                data, 
                ticksize=self.ticksize,
                valuearea=self.valuearea,
                save_fig=True,
                name=dataname)

    def set_signal_mode(self):
        '''
        Switches the mode for catching signals for Long and Short.
        This function is called after Market Profile is
        generated. 
        '''
        val, vah = self.profile_slice.value_area

        if self.open >= vah:
           self._mode_for_short = ABOVE_RANGE
        else:
            self._mode_for_short = ABOVE_VAH

        if self.open <= val:
            self._mode_for_long = BELOW_RANGE
        else:
            self._mode_for_long = BELOW_VAL

    def checksignals(self):
        if not self.check_last_signal_time():
            return NONE

        if self.check_std_dev():

            mp_signal = self.mpsignal()

            conditions = {
                    'Symbol': self.dataname,
                    'Signal': mp_signal,
                    'Last Order Price': self.check_last_order_price(mp_signal),
                    'New High': self.check_new_high(),
                    'New Low': self.check_new_low(),
                    'MP Generated Time':str(self._mp_gen_time),
                    }

            #print(str(conditions))

            if False in conditions.values():
                return NONE
            else:
                self._last_signal_time = self.now

                if mp_signal == LONG:
                    self._last_longprice = self.close
                    self._last_trade_low = self.close

                elif mp_signal == SHORT:
                    self._last_shortprice = self.close
                    self._last_trade_high = self.close

                return mp_signal

        return NONE

    def mpsignal(self):
        '''Check the current mode of trade, market profile and close 
        value to sinalize a Long or Short signal or None signal
        '''

        if self.profile_slice is None:
            return NONE

        # Market Profile Range
        min_range, max_range = self.profile_slice.open_range()

        # Market Profile Value Area
        val, vah = self.profile_slice.value_area

        # Long signal
        if self._mode_for_long == BELOW_VAL:
            if self.close < val:
                return LONG

        elif self._mode_for_long == BELOW_RANGE:
            if self.close < min_range:
                return LONG
        else:
            raise TradeModeNotFound()

        # Short signal
        if self._mode_for_short == ABOVE_VAH:
            if self.close > vah:
                return SHORT

        elif self._mode_for_short == ABOVE_RANGE:
            if self.close > max_range:
                return SHORT
        else:
            raise TradeModeNotFound()
        return NONE

    def print_status(self):
        '''Print status of this signal handler.
        '''
        val, vah = self.profile_slice.value_area
        min_range, max_range = self.profile_slice.open_range()
        
        # Strategy Params
        df_st = pd.DataFrame({
                'Symbol':self.dataname,
                'STD Threshold':self.std_threshold,
                'Minimum Price':self.min_pricechange,
                'MP Tick Size':self.ticksize,
                'MP Value Area':self.valuearea,
            }, index=[0])

        # Market Profile Info
        df_mp = pd.DataFrame({
                'Date': self._mp_gen_time,
                'Min Range': min_range,
                'Max Range': max_range,
                'VAL':val,
                'VAH':vah,
                'Long Mode': self._mode_for_long,
                'Short Mode': self._mode_for_short,
                }, index=[0])

        df_status = pd.DataFrame({
            'Std Dev':self.std,
            'Open':self.open,
            'High':self.high,
            'Low':self.low,
            'Close':self.close,
            }, index=[0])

        # Orders Info
        df_order = pd.DataFrame({
                'Last Trade High':self._last_trade_high,
                'Last Trade Low':self._last_trade_low,
                'Last Long Price':self._last_longprice,
                'Last Short Price':self._last_shortprice,
                'Last Signal Time':self._last_signal_time,
                }, index=[0])

        print('[ Signal Mode ] \n'+
                 tabulate(df_st, headers='keys', tablefmt='psql', showindex=False)+'\n',
                 tabulate(df_mp, headers='keys', tablefmt='psql', showindex=False)+'\n',
                 tabulate(df_status, headers='keys', tablefmt='psql', showindex=False)+'\n',
                 tabulate(df_order, headers='keys', tablefmt='psql', showindex=False))

    def reset(self):
        '''Reset variables. This function depends on the signal handler
        cycle period. This function is not called internally.
        '''
        self._last_trade_high = None
        self._last_trade_low = None
        self._last_longprice = None
        self._last_shortprice= None

