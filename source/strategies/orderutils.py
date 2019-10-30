# -*- coding: utf-8 -*-

from backtrader.order import Order
import pandas as pd
from tabulate import tabulate
from strategies.exceptions import *

NONE = 'None'
LONG = 'Long'
SHORT = 'Short'

PERCENT = 'Percent'
VALUE = 'Value'
PRICE = 'Price'

def calc_stops(price, side, stoploss, takeprofit, mode=VALUE,
        lots=None):
    '''Calculate Stop Loss and Take Profit based on price and
    method for calculation: percentage or ticks.
    Parameter lots is used for VALUE mode only

    return: StopLoss, TakeProfit
    '''
    if mode == PERCENT:
        if side == LONG:
            return (price * (1 - stoploss)), (price * (1 + takeprofit))
        elif side == SHORT:
            return (price * (1 + stoploss)), (price * (1 - takeprofit))
        else:
            raise DirectionNotFound()

    elif mode == PRICE:
        if side == LONG:
            return (price - stoploss) , (price + takeprofit)
        elif side == SHORT:
            return (price + stoploss), (price - takeprofit)
        else:
            raise DirectionNotFound()

    elif mode == VALUE:
        if lots == None:
            raise StopCalculationError()
            return None, None
        if side == LONG:
            return (price * lots - stoploss), (price * lots + takeprofit)
        elif side == SHORT:
            return (price * lots + stoploss), (price * lots - takeprofit)
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

    def __init__(self, id, lots, side, symbol):
        self._id = id
        self.symbol = symbol
        self.lot = lots
        self.side = side # LONG or SHORT

        self.closed_time = None
        self.closed_price = None
        self.executed_time = None
        self.executed_price = None

        # Internal vars
        self._stoploss = None # Absolute value of stop loss
        self._takeprofit = None

    def market_order(self, st):
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

    def limit_order(self, st, price, valid = None):
        '''Execute Limit Order
        '''
        if self.side == LONG:
            self.order = st.buy(
                    data= st.getdatabyname(self.symbol),
                    size = self.lot,
                    price = price,
                    exectype = Order.Limit,
                    tradeid = self._id,
                    valid = valid,
                    )
        elif self.side == SHORT:
            self.order = st.sell(
                    data = st.getdatabyname(self.symbol),
                    size = self.lot,
                    price = price,
                    exectype = Order.Limit,
                    tradeid = self._id,
                    valid = valid,
                    )
        else:
            raise DirectionNotFound()

    def stop_order(self, st, trigger_price, valid = None):
        '''Execute Stop Order
        '''
        if self.side == LONG:
            self.order = st.buy(
                    data = st.getdatabyname(self.symbol),
                    size = self.lot,
                    price = trigger_price,
                    exectype = Order.Stop,
                    tradeid = self._id,
                    valid = valid,
                    )
        elif self.side == SHORT:
            self.order = st.sell(
                    data = st.getdatabyname(self.symbol),
                    size = self.lot,
                    price = trigger_price,
                    exectype = Order.Stop,
                    tradeid = self._id,
                    valid = valid,
                    )
        else:
            raise DirectionNotFound()

    def stoplimit_order(self, st, trigger_price, limit_price, valid=None):
        '''Execute Limit Order at Trigger Price
        '''
        if self.side == LONG:
            self.order = st.buy(
                    data = st.getdatabyname(self.symbol),
                    size = self.lot,
                    price = trigger_price,
                    pricelimit = limit_price,
                    exectype = Order.StopLimit,
                    tradeid = self._id,
                    valid = valid,
                    )
        elif self.side == SHORT:
            self.order = st.sell(
                    data = st.getdatabyname(self.symbol),
                    size = self.lot,
                    price = trigger_price,
                    pricelimit = limit_price,
                    exectype = Order.StopLimit,
                    tradeid = self._id,
                    valid = valid,
                    )
        else:
            raise DirectionNotFound()

    def protection_order(self, st, price, valid = None):
        '''Market with Protection Order (IB only)
        '''
        args = {
                'orderType':'MKT PRT',
                'auxPrice':price,
                }
        if self.side == LONG:
            self.order = st.buy(
                    size = self.lot,
                    tradeid = self._id,
                    valid = valid,
                    **args
                    )
        elif self.side == SHORT:
            self.order = st.sell(
                    size = self.lot,
                    tradeid = self._id,
                    valid = valid,
                    **args
                    )
        else:
            raise DirectionNotFound()

    def lit_order(self, st, limit_price, aux_price):
        '''Limit if Touched Order (IB only)
        '''
        args = {
                'orderType':'LIT',
                'lmtPrice':limit_price,
                'auxPrice':aux_price,
                }
        if self.side == LONG:
            self.order = st.buy(
                    size = self.lot,
                    tradeid = self._id,
                    valid = valid,
                    **args
                    )
        elif self.side == SHORT:
            self.order = st.sell(
                    size = self.lot,
                    tradeid = self._id,
                    valid = valid,
                    **args
                    )
        else:
            raise DirectionNotFound()

    def check_stops(self, bt):
        '''Check if stops is not none and compare
        with current price. Return True if any of stops
        is reached
        '''
        current_price = bt.getdatabyname(self.symbol).close[0]
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
        if self.executed_time is not None:
            if self.time_decay is not None:               
                if pd.Timedelta(pd.Timestamp(now) - pd.Timestamp(self.executed_time)).seconds >= self.time_decay:
                    return True
        return False

    def close(self, st):
        '''Close position means openning a oposite
        position with same parameters
        '''
        if self.executed:
            if self.side == LONG:
                self.order = st.sell(
                    data = st.getdatabyname(self.symbol),
                    size= self.lot,
                    price=None, 
                    exectype=Order.Market, 
                    #TODO passar id para saber qnd foi fechada
                    #tradeid=self._id, 
                        )
            elif self.side == SHORT:
                self.order = st.buy(
                    data = st.getdatabyname(self.symbol),
                    size= self.lot,
                    price=None, 
                    exectype=Order.Market, 
                    #tradeid=self._id, 
                        )
            else:
                raise DirectionNotFound()
            #TODO
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
    
    def set_executed(self, price, datetime):
        self.executed = True
        self.executed_time = datetime
        self.executed_price = price

    def print_order(self):
        '''Print order variables to standard output
        '''
        print(tabulate(self.as_dataframe(), headers='keys', tablefmt='psql', showindex=False))

    def as_dataframe(self):
        '''Return Data Frame with variables values
        '''
        return pd.DataFrame({
            'trade_id':str(self._id),
            'lot':str(self.lot),
            'side':self.side,
            'symbol':self.symbol,
            'executed':str(self.executed),
            'executed price':str(self.executed_price),
            'executed_time':str(self.executed_time),
            'stoploss':str(self._stoploss),
            'takeprofit':str(self._takeprofit),
            'time_decay':str(self.time_decay),
            'closed':self.closed,
            }, index=[self.symbol])

