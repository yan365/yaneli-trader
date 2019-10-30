# -*- coding: utf-8 -*-

from strategies.orderutils import *
import datautils as du
from optparams import *
import datetime as dt

LOTS_CONFIGURATION = [
        [1,2,3,1,2,3],
        [1,2,3,4,5,6],
        ]

class TradeSignalsHandler:

    market_profile = None
    profile_slice = None

    lot_configuration = None

    std_threshold = 0.
    min_pricechange = 0.

    last_orderid = -1

    minimum_order_time = 60*10 # Minimum time to send another order

    def __init__(self, dataname, lot_index, stoploss_index, 
            takeprofit_index, valuearea, ticksize_index, std_threshold_index,
            min_pricechange_index, min_ordertime):
        
        self.dataname = dataname
        self.lot_configuration = LOTS_CONFIGURATION[lot_index]
        self.ticksize = MP_TICKSIZE_CONFIGURATION[ticksize_index][dataname]
        self.stoploss = STOP_LOSS_CONFIGURATION[stoploss_index][dataname]
        self.takeprofit = TAKE_PROFIT_CONFIGURATION[takeprofit_index][dataname]

        self.valuearea = valuearea
        self.std_threshold = STD_THRESHOLD_CONFIGURATION[std_threshold_index][dataname]

        self.min_pricechange = MINIMUM_PRICE_CONFIGURATION[min_pricechange_index][dataname]

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

        self.min_ordertime = min_ordertime

        # Market Profile generated time
        self.mp_gen_time = None

        self._long_daily_orders = 0
        self._short_daily_orders = 0

        self._last_order_time = pd.Timestamp(dt.datetime.now())

    def check_std_dev(self, st):
        '''Check if current value of Standard Deviation indicator
        is equal or greater than Standard Deviation Threshold
        '''
        return (st.stddev[self.dataname][0] >= self.std_threshold)
    
    def check_new_highlow(self, st, signal):

        if signal == NONE:
            return False

        elif signal == SHORT:
            if self._last_trade_high is None:
                return True

            if self._last_trade_high < st.getdatabyname(self.dataname).high[0]:
                return True

        elif signal == LONG:
            if self._last_trade_low is None:
                return True

            if self._last_trade_low < st.getdatabyname(self.dataname).low[0]:
                return True

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
                <= dt.timedelta(hours=st.params.timebetweenorders.hour,
                        minutes=st.params.timebetweenorders.minute):
            return False
        return True

    def check_orders_limit(self, signal):
        '''The limit number of orders for a specific direction 
        is the number of elements in list received by input
        parameter lotconfig
        '''
        if signal == LONG:
            if len(self.lot_configuration)-1 < self._long_daily_orders:
                return False
        elif signal == SHORT:
            if len(self.lot_configuration)-1 < self._short_daily_orders:
                return False
        return True

    def get_lot_size(self, signal):
        '''Get the element in the list with the size of lots
        '''
        if signal == LONG:
            return self.lot_configuration[self._long_daily_orders]
        elif signal == SHORT:
            return self.lot_configuration[self._short_daily_orders]

    def generate_mp(self, data):
        '''Generate Market Profile
        '''
        self.mp_gen_time = data['datetime'][0]
        self.market_profile, self.profile_slice = generateprofiles(
                data, 
                ticksize=self.ticksize,
                valuearea=self.valuearea,
                save_fig=SAVEFIGURES)

    def set_signal_mode(self, data):
        '''
        Switches the mode for catching signals for Long and Short.
        This function is called after Market Profile is
        generated. 
        '''
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
                    'Symbol': self.dataname,
                    'Signal': mp_signal,
                    'Last Order Time': self.check_last_order_time(st),
                    'Last Order Price': self.check_last_order_price(st, mp_signal),
                    'New High/Low': self.check_new_highlow(st, mp_signal),
                    'Orders Limit': self.check_orders_limit(mp_signal)
                    }

            if LOG: print(str(conditions))

            if False in conditions.values():
                return NONE
            else:
                self._last_order_time = pd.Timestamp(dt.datetime.now())
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

