# -*- coding: utf-8 -*-

import sys
sys.path.append('../')

from dataclient import *
import matplotlib.pyplot as plt
import numpy as np

HOST = '127.0.0.1'
PORT = 7497
CLIENT_ID = 1234

TIMEFRAME = '1 day'
DURATION = '100 D'

CONTRACTS = {
        'EURUSD':Forex('EURUSD', 'IDEALPRO', 'EUR'),
        }

def calc_hurst(data):
    tau, lagvec = [], []

    for lag in range(2, 20):
        # Price difference with lag
        pdiff = np.subtract(data['Close'][lag:], data['Close'][:-lag])
        # Append the different lags into a vector
        lagvec.append(lag)
        # Calculate variance of difference
        tau.append(np.sqrt(np.std(pdiff)))

    plt.plot(np.log10(lagvec), np.log10(tau))
    plt.show()
    # Linear fit to a double-log graph to get power
    m = np.polyfit(np.log10(lagvec), np.log10(tau), 1)
    # Calculate hurst
    hurst = m[0] * 2
    return hurst

if __main__ == '__main__':

    client = IBDataClient(HOST, PORT, CLIENT_ID)
    
    datas = {}
    for key, contract in CONTRACTS.items():
        datas[key] = client.getdata_fromct(contract, TIMEFRAME, DURATION)

    hurst_values = {}
    for key, data in datas.items():
        hurst_values[key] = calc_hurst(data)

    print(hurst_values)

