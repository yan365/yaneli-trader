# -*- coding: utf-8 -*-

import sys
sys.path.append('../')

from dataclient import *
import matplotlib.pyplot as plt

HOST = '127.0.0.1'
PORT = 7497
CLIENT_ID = 1234

TIMEFRAME = '1 day'
DURATION = '100 D'

CONTRACTS = {
        'TWTR': Stock('TWTR', 'SMART', 'USD'),
        'TSLA': Stock('TSLA', 'SMART', 'USD'),
        'AMD': Stock('AMD', 'SMART', 'USD'),
        'INTC': Stock('INTC', 'SMART', 'USD'),
        }

if __name__ == '__main__':

    client = IBDataClient(HOST, PORT, CLIENT_ID)

    # Download bar data
    datas = {}
    for key, contract in CONTRACTS.items():
        datas[key] = client.getdata_fromct(contract, timeframe=TIMEFRAME, duration=DURATION)

    positive = {}
    negative = {}
    bars_number = {}
    price_change = {}
    efficiency_pos = {}
    efficiency_neg = {}
    for key, data in datas.items():

        for bar in data:
            if bar['Open'] < bar['Close']:
                positive[key] += 1
            if bar['Open'] > bar['Close']:
                negative[key] += 1
        bar_numbers[key] = len(data)
        price_change[key] = data['Open'].iloc[0] - data['Close'].iloc[data.size]
        efficiency_pos[key] = positive[key]/bar_numbers[key]
        efficiency_neg[key] = negative[key]/bar_numbers[key] 

    print(positive)
    print(negative)
    print(bars_number)
    print(price_change)

    for key, data in datas.items():
        print('\n%s Report:' % key)
        print('Duration: %s    Timeframe: %s' % (DURATION, TIMEFRAME))
        print('Price Change: %5f' % price_change[key])
        print('Positive Candles: %d' % positive[key])
        print('Negative Candles: %d' % negative[key])
        print('(High Candles)/(Price Change) = %.5f' % efficiency[key])
        print('(Low Candles)/(Price Change) = %.5f' % efficiency[key])


