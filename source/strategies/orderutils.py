# -*- coding: utf-8 -*-

from backtrader.order import Order
import pandas as pd
from tabulate import tabulate
import datetime as dt
from strategies.exceptions import *
import datautils as du

# Position types
NONE = 'None'
LONG = 'Long'
SHORT = 'Short'

# Stops calculation mode
PERCENT = 'Percent' # 0.01 = 1%
PRICE = 'Price'     # absolute price
VALUE = 'Value'     # price * lot size
TICK = 'Tick'       # tick size of symbol * stops value

def calc_stops(price, side, stoploss, takeprofit, mode=VALUE,
        lots=None, ticksize=None):
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

    elif mode == TICK:
        if ticksize == None:
            raise StopCalculationError()
            return None, None
        if side == LONG:
            return (price - (ticksize * stoploss)), (price + (ticksize * takeprofit))
        elif side == SHORT:
            return (price + (ticksize * stoploss)), (price - (ticksize * takeprofit))
        else:
            raise DirectionNotFound()
    else:
        raise TradeModeNotFound()

    return None, None

class OrdersManagement(object):
    '''Handle the orders state. 
    Manage time parameters, check open and close conditions, 
    refresh the orders state with broker, open and close positions.

    Parameters:

      - strategy 

      The backtrader strategy class which will have the orders managed by this class

      - dataclient (default: None)

      The dataclient is optional, recommended in Live mode. Some features are handled by the dataclient, like the confirmation with broker about the
      orders state

      - account (default='')

      If running this object with dataclient and account filter is needed
    '''

    def __init__(self, strategy, dataclient=None, account_number='' ):
        self.st = strategy
        self.dataclient = dataclient
        self.account_number = account_number

        # Current orders
        self.order_list = []
        # Closed orders
        self.order_history = []
        # Daily orders
        self.daily_orders = []

        # Daily orders counter
        self.long_daily_orders = 0
        self.short_daily_orders = 0

        # Time Parameters
        self.orderstarttime = None
        self.orderfinaltime = None
        self.timetocloseorders = None
        self.timebetweenorders = None

        ## Stops Prameters
        # Dictionary with data name and value.
        self.takeprofit = dict()
        self.stoploss = dict()

        # Internal variable that stores last order time
        self._lastordertime = dt.datetime(2000,1,1)

    def next(self, datetime):
        if self.dataclient != None:
            self.now = dt.datetime.utcnow()
        else:
            self.now = datetime

    def check_last_trade_time(self):
        '''Check if time parameter allow open a new order based on last order executed time
        '''
        if self.timebetweenorders == None:
            return True
        if self.now - self._lastordertime <= dt.timedelta(seconds=self.timebetweenorders):
            return False
        return True
    
    def confirm_fill(self, order):
        '''Get confirmation about the execution of order with the dataclient
        '''
        if self.dataclient != None:
            contract, execution, report = self.dataclient.getfills()
            #TODO
        return True

    def confirm_close(self):
        '''Check with dataclient if the order was executed
        '''
        if self.dataclient != None:
            contract, execution, report = self.dataclient.getfills()
            #TODO
        return True

    def clear_closed_orders(self):
        '''Check with dataclient if order is already closed
        '''
        if self.dataclient != None:
            contracts, executions, reports = self.dataclient.getcompletedorders(apionly=True)
            #TODO 

        # Remove from current order list and append to order history list
        for i in range(len(self.order_list)-1, -1, -1):
            if self.order_list[i].closed:
                self.order_history.append(self.order_list[i])
                self.order_list.pop(i)

    def close_all_positions(self):
        for i in range(0, len(self.order_list)-1,  1):
            self.close_order(self.order_list[i])
        self.clear_closed_orders()

    def get_pnl(self, symbol):
        pass #TODO

    def check_close_conditions(self):
        '''Check the order close conditions, the symbol close conditions and the time parameter for closing the positions
        '''

        self.clear_closed_orders()

        # Check PnL stops
        for key, value in self.takeprofit.items():
            if self.get_pnl(key) >= float(value):
                self.close_positions(key)

        for key, value in self.stoploss.items():
            if self.get_pnL(key) <= float(value):
                self.close_positions(key)
        self.clear_closed_orders()

        to_close = []
        for order in self.order_list:
            # Check the order close conditions
            if order.check_stops(self.st.getdatabyname(order.symbol).close[0]) or order.check_timedecay(self.st.datas[0].datetime.datetime(0)):
                to_close.append(order)
        to_close = list(dict.fromkeys(to_close))

        for order in to_close:
            self.close_order(order)
        self.clear_closed_orders()

    def check_order_final_time(self):
        '''Check if it's allowed open new orders.
        Check if parameters are passed and compares the values with dataclient (if activated) or the backtrader strategy.
        '''

        if self.orderfinaltime == None:
            return True

        if self.dataclient == None:

            if self.now.time() >= self.orderfinaltime:
                return False

        else:
            if dt.datetime.now().time() >= self.orderfinaltime:
                return False

        return True

    def check_time_close_orders(self):
        '''Check if parameter with time to close orders is activated, then
        check if time to close all orders
        '''
        if self.timetocloseorders == None:
            return False
        if self.dataclient == None:
            if self.now.time() >= self.timetocloseorders:
                return True
        else:
            if dt.datetime.now().time() >= self.timetocloseorders:
                return True
        return False

    def confirm_close(self, tradeid):
        #TODO
        return True
    
    def close_order(self, order):
        '''Close position means openning a oposite
        position with same parameters
        '''
        if order.executed:
            if not order.closed:
                _order = self.st.close(
                    data = self.st.getdatabyname(order.symbol),
                    price=None, 
                    exectype= Order.Market, 
                    )

            if self.dataclient != None:
                self.confirm_close(symbol)

    def get_time_close_orders(self): #TODO not used
        '''Return the secconds missing to close orders time.
        '''
        if self.timetocloseorders != None:
            return pd.Timedelta(self.now.time() - self.timetocloseorders).total_secconds()
        return -1

    def lit_order(self, order, limit_price, aux_price):
        '''Limit if Touched Order (IB only)
        '''
        if not self._check_state():
            return None
        self._add_order(order)

        args = {
                'orderType':'LIT',
                'lmtPrice':limit_price,
                'auxPrice':aux_price,
                }

        if order.side == LONG:
            _order = self.st.buy(
                    size = order.lot,
                    tradeid = order._id,
                    valid = valid,
                    **args
                    )
            return _order

        elif order.side == SHORT:
            _order = self.st.sell(
                    size = order.lot,
                    tradeid = order._id,
                    valid = valid,
                    **args
                    )
            return _order
        else:
            raise DirectionNotFound()

    def limit_order(self, order, price, valid = None):
        '''Execute Limit Order
        '''
        if not self._check_state():
            return None
        self._add_order(order)

        if order.side == LONG:
            _order = st.buy(
                    data= self.st.getdatabyname(order.symbol),
                    size = order.lot,
                    price = price,
                    exectype = Order.Limit,
                    tradeid = order._id,
                    valid = valid,
                    )
            return _order

        elif order.side == SHORT:
            _order = st.sell(
                    data = self.st.getdatabyname(order.symbol),
                    size = order.lot,
                    price = price,
                    exectype = Order.Limit,
                    tradeid = order._id,
                    valid = valid,
                    )
            return _order
        else:
            raise DirectionNotFound()
    
    def market_order(self, order):
        '''Execute market order with already given parameters
        '''
        if not self._check_state():
            return None
        self._add_order(order)

        if order.side == LONG:
            _order = self.st.buy( 
                    size= order.lot,
                    price=None, 
                    exectype=Order.Market, 
                    tradeid=order._id, 
                    )
            return _order

        elif order.side == SHORT:
            _order = self.st.sell(
                    size= order.lot,
                    price=None, 
                    exectype=Order.Market, 
                    tradeid=order._id, 
                    )
            return _order

        else:
            raise DirectionNotFound()

    def print_status(self):
        '''Print
        '''
        if self.dataclient != None:
            df = pd.DataFrame({
                'Data Client':str(self.dataclient),
                'Account Number':str(self.account_number)}, index=[0])
            print(tabulate(df))

        df = pd.DataFrame({
            'Open Orders':len(self.order_list),
            'Closed Orders':len(self.order_history),
            'Daily Orders':len(self.daily_orders),
            #TODO 'Time to next order'
            }, index=[0])

        print(tabulate(df))

    def protection_order(self, order, price, valid = None):
        '''Market with Protection Order (IB only)
        '''
        if not self._check_state():
            return None
        self._add_order(order)

        args = {
                'orderType':'MKT PRT',
                'auxPrice':price,
                }
        if order.side == LONG:
            _order = self.st.buy(
                    size = order.lot,
                    tradeid = order._id,
                    valid = valid,
                    **args
                    )
            return _order

        elif order.side == SHORT:
            _order = self.st.sell(
                    size = order.lot,
                    tradeid = order._id,
                    valid = valid,
                    **args
                    )
            return _order
        else:
            raise DirectionNotFound()

    def reset(self):
        '''Reset parameters.
        '''
        self.daily_orders = []
        self.short_daily_orders = 0
        self.long_daily_orders = 0
    
    def set_orders_start_time(self, value):
        '''Time of day when orders are allowed
        '''
        self.orderstarttime = value

    def set_orders_final_time(self, value):
        '''Time of day when orders are not allowed
        '''
        self.orderfinaltime = value

    def set_orders_close_time(self, value):
        '''Time of day to close the orders
        '''
        self.timetocloseorders = value

    def set_time_between_orders(self, value):
        '''Minimum time to send another order
        '''
        self.timebetweenorders = value

    def show_orders_number(self):
        '''Show the open orders number and the closed orders number.
        '''
        if dataclient != None:
            #TODO
            return 0
        else:
            return len(self.order_list)

    def show_closed_orders(self):
        if dataclient != None:
            con, exe, rep = self.dataclient.getcompletedorders()
        else:
            pass
        #TODO

    def set_executed(self, tradeid, price, datetime):
        for i in range(len(self.order_list)-1, -1, -1):
            if self.order_list[i]._id == tradeid:
                self.order_list[i]._set_executed(price, datetime)
                break
    
    def set_takeprofit(self, _dict):
        '''Set take profit for data name. This is different from the stops
        of the order. The take profit of Order Management object is compared with PnL of the symbol.
        '''
        self.takeprofit.update(_dict)

    def set_stoploss(self, _dict):
        '''Set stop loss for data name.
        '''
        self.stoploss.update(_dict)

    def summary(self):
        '''Account summary. For dataclient only
        '''
        if self.dataclient != None:
            return self.dataclient.getaccountsummary(self.account_number)
        return None

    def stop(self):
        '''Print all orders when algorithm stop
        '''
        if self.dataclient != None:
            self.dataclient.close()
        for order in self.order_list:
            order.print_order()

        open_orders = pd.DataFrame()
        if len(self.order_list) > 0:

            for order in self.order_list:
                open_orders = open_orders.append(order.as_dataframe())
        output_fn = 'open_orders'+str(dt.datetime.utcnow()).replace('-','')+'.csv'

        if open_orders.size > 0:
            du.save_data(dataframe= open_orders, 
                    output_filename=output_fn)

        order_his = pd.DataFrame()
        if len(self.order_history) > 0:

            for order in self.order_history:
                order_his = order_his.append(order.as_dataframe())
        output_fn = 'closed_orders_'+str(pd.Timestamp(dt.datetime.now())).replace('-','').replace(' ', '').replace(':','')+'.csv'
        du.save_data(dataframe=order_his, output_filename=output_fn)


    def stop_order(self, order, trigger_price, valid = None):
        '''Execute Stop Order
        '''
        if not self._check_state():
            return None
        self._add_order(order)

        if order.side == LONG:
            _order = self.st.buy(
                    data = st.getdatabyname(order.symbol),
                    size = order.lot,
                    price = trigger_price,
                    exectype = Order.Stop,
                    tradeid = order._id,
                    valid = valid,
                    )
            return _order

        elif order.side == SHORT:
            _order = self.st.sell(
                    data = st.getdatabyname(order.symbol),
                    size = order.lot,
                    price = trigger_price,
                    exectype = Order.Stop,
                    tradeid = order._id,
                    valid = valid,
                    )
            return _order
        else:
            raise DirectionNotFound()

    def stoplimit_order(self, order, trigger_price, limit_price, valid=None):
        '''Execute Limit Order at Trigger Price
        '''
        if not self._check_state():
            return None
        self._add_order(order)

        if order.side == LONG:
            _order = st.buy(
                    data = st.getdatabyname(order.symbol),
                    size = order.lot,
                    price = trigger_price,
                    pricelimit = limit_price,
                    exectype = Order.StopLimit,
                    tradeid = order._id,
                    valid = valid,
                    )
            return _order

        elif order.side == SHORT:
            _order = st.sell(
                    data = st.getdatabyname(order.symbol),
                    size = order.lot,
                    price = trigger_price,
                    pricelimit = limit_price,
                    exectype = Order.StopLimit,
                    tradeid = order._id,
                    valid = valid,
                    )
            return _order
        else:
            raise DirectionNotFound()

    def update_orders(self):
        if self.dataclient != None:
            positions = self.dataclient.getpositions()
        #TODO
    
    def _add_order(self, order):
        '''Internal function for adding orders to the orders lists
        '''
        if order != None:
            self.order_list.append(order)
            self.daily_orders.append(order)
            if order.side == LONG:
                self.long_daily_orders += 1
            elif order.side == SHORT:
                self.short_daily_orders += 1

    def _check_state(self):
        '''Check if time parameters allow open a new order.
        This function is called just before sending a new order.
        '''
        if self.dataclient == None:
            # If dataclient is deactivated then use backtrader time
            self._lastordertime = self.st.datas[0].datetime.datetime(0)
        else:
            self._lastordertime = dt.datetime.now()

        if self.orderstarttime != None:

            if self.now.time() < self.orderstarttime:
                return False

        if self.orderfinaltime != None:
            if self.now.time() > self.orderfinaltime:
                return False

        if not self.check_last_trade_time():
            return False

        return True

class OrderHandler(object):
    '''Stores order parameters and order state information. Managed with Order Management object.
    
       Parameters:

       - id

       - lots

       - side

       - symbol
    '''

    def __init__(self, id, lots, side, symbol):

        self._id = id
        self.symbol = symbol
        self.lot = lots
        self.side = side # LONG or SHORT
    
        self.executed = False # If order was executed
        self.closed = False   # If order was closed

        # Time parameter
        self.time_decay = None

        # Internal vars
        self._stoploss = None # Absolute value of stop loss
        self._takeprofit = None
        self._filled_time = None
        self._filled_price = None 

    def check_stops(self, close):
        '''Check if stops is not none and compare
        with current price. Return True if any of stops
        is reached
        '''
        if self._stoploss is not None:

            if self.side == LONG:
                if close <= self._stoploss:
                    return True

            elif self.side == SHORT:
                if close >= self._stoploss:
                    return True
            else:
                DirectionNotFound()

        if self._takeprofit is not None:

            if self.side == LONG:
                if close >= self._takeprofit:
                    return True

            elif self.side == SHORT:
                if close <= self._takeprofit:
                    return True

            else:
                DirectionNotFound()
        return False

    def check_timedecay(self, now):
        '''Time decay is the time for closing order after the order is executed. Return True if it's time to close the order
        '''
        if self._filled_time is not None:
            if self.time_decay is not None:

                if pd.Timedelta(pd.Timestamp(now) - pd.Timestamp(self._filled_time)).seconds >= self.time_decay:
                    return True

        return False

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
            'executed price':str(self._filled_price),
            'executed_time':str(self._filled_time),
            'stoploss':str(self._stoploss),
            'takeprofit':str(self._takeprofit),
            'time_decay':str(self.time_decay),
            'closed':self.closed,
            }, index=[self.symbol])
    
    def _set_executed(self, price, datetime):
        '''Internal function for saving execution parameters.
        '''
        self.executed = True
        self._filled_time = datetime
        self._filled_price = price

