# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
import datetime as dt
from market_profile import MarketProfile, MarketProfileSlice

def generateprofiles(dataframe, ticksize=0.5, valuearea = 0.7, 
        mp_mode='tpo', save_fig=True, name=''):
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

        -name (default: '')
        Optional argument for prefix name
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
        filename = name+'_'+mp_mode+'_'+str(dataframe['datetime'].iloc[
                    dataframe['datetime'].size-1])+'_'+\
                    str(dataframe['datetime'].iloc[0])
        filename.replace(' ','_').replace(':','').replace('.','')+'.png'
        fig.figure.savefig(filename)
    return profile, mp_slice

def parsedata(data, from_date=None, to_date=None, size_limit=60*60*24):
    '''Get data from backtrader cerebro and convert
    in a pandas dataframe. The columns names are changed for
    compatibility with Market Profile library. The dataframe 
    can be filtered by date and size.
    '''
    timestamp = []
    datetime = []
    
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

def parsedataframe(dataframe, from_date=None, to_date=None, size_limit=60*60*24):
    '''Get data from backtrader cerebro and convert
    in a pandas dataframe. The columns names are changed for
    compatibility with Market Profile library. The dataframe 
    can be filtered by date and size.
    '''
    timestamp = []
    datetime = []
    
    # Define maximum size of data
    _size = size_limit if dataframe.size > size_limit else dataframe.size
    

    dataframe['Close'] = dataframe['Close'].astype('float')
    #dataframe['Volume'] = dataframe['Volume'].astype('float')

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

def save_data(dataframe, output_filename='out.csv', sep=',', **kwargs):
    args = {
            'path_or_buf':output_filename,
            'sep':sep,
            'header':True,
            'index':False,
            }
    args.update(kwargs)
    dataframe.to_csv(**args)

def plot_orders(data, orders, dataname='plotdata'):
    '''Plot close data with orders parameters
    '''
    title = dataname

    plt.clf()
    plt.plot(data['Close'], linewidth=1)
    plt.title([title])
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
    
    #TODO save figure
    #plt.show()

def plot_data(dataframe, y_axis='close', **kwargs):
    args = {
            'y':y_axis,
            }
    args.update(kwargs)
    fig = dataframe.plot(**args)
    fig.figure.show()
    util.barplot(dataframe)

