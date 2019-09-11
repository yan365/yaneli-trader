# -*- coding: utf-8 -*-

from backtrader.order import Order
import pandas as pd
from tabulate import tabulate

NONE = 'None'
LONG = 'Long'
SHORT = 'Short'

PERCENT = 'Percent'
TICK = 'Tick'

def calc_stops(price, side, stoploss, takeprofit, mode=PERCENT):
    '''Calculate Stop Loss and Take Profit based on price and
    method for calculation: percentage or ticks

    return: StopLoss, TakeProfit
    '''
    if mode == PERCENT:
        if side == LONG:
            return (price * (1 - stoploss)), (price * (1 + takeprofit))
        elif side == SHORT:
            return (price * (1 + stoploss)), (price * (1 - takeprofit))
        else:
            raise DirectionNotFound()

    elif mode == TICKS:
        if side == LONG:
            return (price - stoploss) , (price + takeprofit)
        elif side == SHORT:
            return (price + stoploss), (price - takeprofit)
        else:
            raise DirectionNotFound()
    else:
        raise TradeModeNotFound()
    return None, None

class OrderHandler:
    '''Order management methods for backtrader strategies
    '''
    _id = -1
    lot = 0.
    price = 0.
    side = NONE
    symbol = ''
    executed = False
    closed = False
    time_decay = None

    def __init__(self, id, lots, side, symbol=''):
        self._id = id
        self.symbol = symbol
        self.lot = lots
        self.side = side # LONG or SHORT
        # Internal vars
        self._stoploss = None # Absolute value of stop loss
        self._takeprofit = None
        self._exec_timestamp = None # Timestamp of order execution

    def execute(self, st):
        '''Execute market order with already given parameters
        '''
        if self.side == LONG:
            self.order = st.buy( 
                    size= self.lot,
                    price=None, 
                    exectype=Order.Market, 
                    tradeid=self._id, 
                    )
        elif self.side == SHORT:
            self.order = st.sell(
                    size= self.lot,
                    price=None, 
                    exectype=Order.Market, 
                    tradeid=self._id, 
                    )
        else:
            raise DirectionNotFound()
        #TODO need broker confirmation to set executed as True
        self.executed = True
        self._exec_timestamp = pd.Timestamp(st.datas[0].datetime.datetime(0))

    def check_stops(self, current_price):
        '''Check if stops is not none and compare
        with current price. Return True if any of stops
        is reached
        '''
        if self._stoploss is not None:
            if self.side == LONG:
                if current_price <= self._stoploss:
                    return True
            elif self.side == SHORT:
                if current_price >= self._stoploss:
                    return True
            else:
                DirectionNotFound()

        if self._takeprofit is not None:
            if self.side == LONG:
                if current_price >= self._takeprofit:
                    return True
            elif self.side == SHORT:
                if current_price <= self._takeprofit:
                    return True
            else:
                DirectionNotFound()
        return False

    def check_timedecay(self, now):
        '''Time decay is the time for closing order after the order is executed
        '''
        if self._exec_timestamp is not None:
            if self.time_decay is not None:               
                if pd.Timedelta(pd.Timestamp(now) - self._exec_timestamp).seconds >= self.time_decay:
                    return True
        return False

    def close(self, st):
        '''Close position means openning a oposite
        position with same parameters
        '''
        if self.executed:
            if self.side == LONG:
                self.order = st.sell(
                    size= self.lot,
                    price=None, 
                    exectype=Order.Market, 
                    tradeid=self._id, 
                        )
            elif self.side == SHORT:
                self.order = st.buy(
                    size= self.lot,
                    price=None, 
                    exectype=Order.Market, 
                    tradeid=self._id, 
                        )
            else:
                raise DirectionNotFound()
            # TODO broker confirmation
            self.closed = True

    def set_timedecay(self, time=None):
        '''Configure time decay
        '''
        self.time_decay = time

    def set_stops(self, sl, tp):
        '''Change Stops values
        '''
        self._takeprofit = tp
        self._stoploss = sl

    def print_order(self):
        '''Print order variables to standard output
        '''
        print(tabulate(pd.DataFrame({
            'trade_id':str(self._id),
            'lot':str(self.lot),
            'side':self.side,
            'symbol':self.symbol,
            'executed':str(self.executed),
            'stoploss':str(self._stoploss),
            'takeprofit':str(self._takeprofit),
            'time_decay':str(self.time_decay),
            'closed':self.closed,
            }, index=[0]), headers='keys', tablefmt='psql', showindex=False))

    def as_dataframe(self):
        '''Return Data Frame with variables values
        '''
        return pd.DataFrame({
            'trade_id':str(self._id),
            'lot':str(self.lot),
            'side':self.side,
            'symbol':self.symbol,
            'executed':str(self.executed),
            'stoploss':str(self._stoploss),
            'takeprofit':str(self._takeprofit),
            'time_decay':str(self.time_decay),
            'closed':self.closed,
            }, index=[0])

