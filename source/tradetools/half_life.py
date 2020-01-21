# -*- coding: utf-8 -*-

import sys
sys.path.append('../')

from dataclient import *
import matplotlib.pyplot as plt

HOST = '127.0.0.1'
PORT = 7497
CLIENT_ID = 1234

MOVING_AVERAGE_PERIOD = 8
TIMEFRAME = '1 day'
DURATION = '100 D'

CONTRACTS = {
        'EURUSD':Forex('EURUSD', 'IDEALPRO', 'EUR'),
        }

def calc_moving_average(data, period=8):
    '''Moving Average calculation
    '''
    ma_serie = []
    for i in range(0, data.size-period+1, 1):
        ma_serie.append(df['Close'].iloc[i:i+period].mean())
    print(ma_serie)
    return ma_serie

if __name__ == '__main__':

    client = IBDataClient(HOST, PORT, CLIENT_ID)

    datas = {}
    # Download bar data
    for key, contract in CONTRACTS.items():
        datas[key] = client.getdata_fromct(contract, timeframe=TIMEFRAME, duration=DURATION)

    moving_averages = {}
    # Generate Moving Average series
    for key, data in datas.items():
        moving_averages[key] = calc_moving_average(data, period=MOVING_AVERAGE_PERIOD)

    # Check for Moving Average crossings with Close
    crossings = {}
    for key, serie in moving_averages.items():
        crossing_list = []
        for i in range(0, len(serie), 1):
            if datas[key][i+period] > serie[i] and datas[key][i+period] < serie[i]:
                crossing_list.append(i)
        crossings.update({key: crossing_list})

    i = 1
    for key, serie in moving_averages.items():
        plt.subplot(2, int(len(data)/2+1), i)
        plt.plot(serie)
        plt.plot(datas[key][period:])
        #plt.plot() # TODO plot crossings
        plt.title(key)
        plt.grid(True)
        i += 1

    #TODO calculate crossings average period



