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

    # Calculate Variance
    variances = {}
    for key, data in datas.items():
        variances[key] = data['Close'].var()
        # Variance of Moving Average
        variances[key+'_MA'] = moving_averages[key].var()

    # Calculate Covariance Matrix
    close_dict = {}
    for key, data in datas.items():
        close_dict[key] = data['Close']
    close_dataframe = pd.DataFrame(close_dict)
    cov_matrix = close_dataframe.cov()

    print(cov_matrix)



