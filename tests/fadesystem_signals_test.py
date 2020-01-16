# -*- coding: utf-8 -*-

import sys
sys.path.append('../source/')

import time
from strategies.fadesystemsignals import *
from dataclient import *
from datautils import *
from ib_insync import *

HOST = '127.0.0.1'
PORT = 7497
CLIENTID = 1234

SLEEP_TIME = 60 * 5

MP_VALUE_AREA = 0.7

STD_THRESHOLD = {
        'EUR':0.005,
        'GBP':0.005,
        'AMD':0.1,
        'TSLA':0.1,
        'TWTR':0.1,
        }

MIN_PRICE_CHANGE = {
        'EUR':0.005,
        'GBP':0.005,
        'AMD':0.1,
        'TSLA':0.1,
        'TWTR':0.1,
        }

FOREX_SYMBOLS = [
        Forex('EURUSD','IDEALPRO', 'EUR'),
        Forex('GBPUSD', 'IDEALPRO', 'GBP'),
        ]

STOCK_SYMBOLS = [
        Stock('AMD', 'SMART', 'USD'),
        Stock('TSLA', 'SMART', 'USD'),
        Stock('TWTR', 'SMART', 'USD'),
        ]

def create_trade_signals(dataclient):
    trade_signals = dict()

    for stock in STOCK_SYMBOLS:
        _ticksize = dataclient.getticksize(stock)
        trade_signals.update({stock.symbol:TradeSignalsHandler(
            dataname=stock.symbol,
            valuearea = MP_VALUE_AREA,
            ticksize = _ticksize,
            std_threshold = STD_THRESHOLD[stock.symbol],
            min_pricechange = MIN_PRICE_CHANGE[stock.symbol],
            )})

    for forex in FOREX_SYMBOLS:
        _ticksize = dataclient.getticksize(forex)
        trade_signals.update({forex.symbol:TradeSignalsHandler(
            dataname=forex.symbol,
            valuearea = MP_VALUE_AREA,
            ticksize = _ticksize,
            std_threshold = STD_THRESHOLD[forex.symbol],
            min_pricechange = MIN_PRICE_CHANGE[forex.symbol],
            )})

    return trade_signals

def get_datas(dataclient, duration='1 D', timeframe='1 min'):

    datas = dict()

    for stock in STOCK_SYMBOLS:
        datas.update({stock.symbol: 
            dataclient.getdata_fromct(stock, timeframe=timeframe, duration=duration)})

    for forex in FOREX_SYMBOLS:
        datas.update({forex.symbol:
            dataclient.getdata_fromct(forex, timeframe=timeframe, duration=duration)})

    return datas

def new_day(last_cycle):
    return last_cycle.day != dt.datetime.now().day

def getdates():
    '''
    Get the start and the end of previous day
    '''
    now = dt.datetime.now()
    init_day = dt.datetime.timestamp(pd.Timestamp(dt.datetime(now.year, now.month, now.day-1)))
    end_day = dt.datetime.timestamp(pd.Timestamp(dt.datetime(now.year, now.month, now.day)))
    return init_day, end_day

def calc_std(data, period=6):
    '''Standard deviation calculation
    '''
    return data['Close'][-period:].std()

if __name__ == '__main__':
    
    # create data client
    client = IBDataClient(HOST, PORT, CLIENTID)

    # create signals handler for each contract
    signals = create_trade_signals(client)

    # initialize market profile data
    mp_data = get_datas(client, duration='2 D')
    fromdate, todate = getdates()

    # generate market profile
    for key, value in signals.items():
        signals[key].generate_mp(parsedataframe(mp_data[key], 
            from_date=fromdate,
            to_date=todate), dataname=key)
    
    # main loop
    while True:

        last_cycle = dt.datetime.now()
        datas = get_datas(client)

        if new_day(last_cycle):
            fromdate, todate = getdates()
            mp_data = get_datas(client, duration='2 D')
            for key, value in signals.items():
                print('[ Downloading %s Market Profile Data ]' % key)
                signals[key].generate_mp(parsedataframe(mp_data[key],
                    from_date=fromdate,
                    todate=todate), dataname=key)
                signals[key].set_signal_mode()

        data5min = get_datas(client, duration='1 D', timeframe='5 mins')
        for key, value in datas.items():

            print('[ Downloading %s 5 min Data ]' % key)
            # give values to signal handler compute status
            signals[key].next(
                    value['datetime'].iloc[0],
                    calc_std(data5min[key]),
                    value['Open'].iloc[0],
                    value['High'].iloc[0],
                    value['Low'].iloc[0],
                    value['Close'].iloc[0]
                    )

            # get current signal (None, Long, Short)
            signal = signals[key].checksignals()
            if signal == LONG:
                print('\n[ LONG SIGNAL ] %s  %s' % (key, pd.Timestamp(dt.datetime.now())))
                signals[key].print_status()

            elif signal == SHORT:
                print('\n[ SHORT SIGNAL ] %s  %s ' % (key, pd.Timestamp(dt.datetime.now())))
                signals[key].print_status()

        time.sleep(SLEEP_TIME - (dt.datetime.now().timestamp() - last_cycle.timestamp()))

