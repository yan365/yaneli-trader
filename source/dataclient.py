# -*- coding: utf-8 -*-

from ib_insync import *
import datetime as dt
import pandas as pd

HOST = '127.0.0.1'
PORT = 7497
CLIENT_ID = '1234'

FOREX = 'Forex'
FUTURES = 'Futures'
INDEX = 'Index'
OPTION = 'Option'
STOCK = 'Stock'

class IBDataClient:
    '''Client with functions to handle data
    '''

    def __init__(self, host, port, clientid):
        self.client = IB()
        self.client.connect(host, port, clientid)

    def getdata(self, symbol, symboltype, exchange='IDEALPRO', 
            currency='USD', timeframe='1 secs', duration='1 D', 
            **kwargs):
        '''Download data and return as Data Frame
        '''

        contract_args = {
                'symbol':symbol,
                'symboltype':symboltype,
                'exchange':exchange,
                'currency':currency,
                }
        contract = self.getcontract(**contract_args)

        data_args = {
                'contract':contract,
                'barSizeSetting':timeframe,
                'durationStr':duration,
                'endDateTime':'',
                'whatToShow':'MIDPOINT',
                'useRTH':True,
                }
        data_args.update(kwargs)

        data = self.client.reqHistoricalData(**data_args)
        dataframe = util.df(data)
        return dataframe

    def getdata_dt(self, symbol, symboltype, exchange='IDEALPRO', 
            currency='USD', timeframe='1 secs', 
            fromdate= dt.datetime(2015,1,1), 
            todate= dt.datetime.now(), **kwargs):
        '''Download data and return as Data Frame
        '''
        durationstr = self._secs_duration(fromdate) + ' S'

        contract_args = {
                'symbol':symbol,
                'symboltype':symboltype,
                'exchange':exchange,
                'currency':currency,
                }
        contract = self.getcontract(**contract_args)

        data_args = {
                'contract':contract,
                'barSizeSetting':timeframe,
                'durationStr':durationstr,
                'endDateTime':todate,
                'whatToShow':'MIDPOINT',
                'useRTH':True,
                }
        data_args.update(kwargs)

        data = self.client.reqHistoricalData(**data_args)
        dataframe = util.df(data)
        return dataframe

    def earliestbar(self, symbol, symboltype, exchange, **kwargs):
        '''Get oldest bar date
        '''
        contract = self.getcontract(symbol, symboltype, **{'exchange':exchange})
        args = {
                'contract':contract,
                'whatToShow':'MIDPOINT',
                'useRTH':True,
                }

        args.update(kwargs)
        return self.client.reqHeadTimeStamp(**args)

    def getcontract(self, symbol, symboltype, **kwargs):

        args = dict()

        if symboltype == FOREX:

            if 'currency' in kwargs.keys():
                args.update({'currency':kwargs.pop('currency')})
            if 'exchange' in kwargs.keys():
                args.update({'exchange':kwargs.pop('exchange')})
            if 'conId' in kwargs.keys():
                args.update({'conId': kwargs.pop('conId')})
            if 'localSymbol' in kwargs.keys():
                args.update({'localSymbol': kwargs.pop('localSymbol')})
            if 'tradingClass' in kwargs.keys():
                args.update({'tradingClass':kwargs.pop('tradingClass')})

            return Forex(symbol, **args)

        elif symboltype == FUTURES:

            if 'currency' in kwargs.keys():
                args.update({'currency':kwargs.pop('currency')})
            if 'exchange' in kwargs.keys():
                args.update({'exchange':kwargs.pop('exchange')})
            if 'localSymbol' in kwargs.keys():
                args.update({'localSymbol': kwargs.pop('localSymbol')})
            if 'lastTradeDateOrContractMonth' in kwargs.keys():
                args.update({'lastTradeDateOrContractMonth': 
                    kwargs.pop('lastTradeDateOrContractMonth')})

            return Future(symbol, **args)

        elif symboltype == STOCK:
            
            if 'currency' in kwargs.keys():
                args.update({'currency':kwargs.pop('currency')})
            if 'exchange' in kwargs.keys():
                args.update({'exchange':kwargs.pop('exchange')})
            if 'conId' in kwargs.keys():
                args.update({'conId': kwargs.pop('conId')})
            if 'primaryExchange' in kwargs.keys():
                args.update({'primaryExchange': 
                    kwargs.pop('primaryExchange')})
            if 'localSymbol' in kwargs.keys():
                args.update({'localSymbol': kwargs.pop('localSymbol')})
            if 'tradingClass' in kwargs.keys():
                args.update({'tradingClass':kwargs.pop('tradingClass')})

            return Stock(symbol, **args)

        elif symboltype == INDEX:

            if 'currency' in kwargs.keys():
                args.update({'currency':kwargs.pop('currency')})
            if 'exchange' in kwargs.keys():
                args.update({'exchange':kwargs.pop('exchange')})
            if 'conId' in kwargs.keys():
                args.update({'conId': kwargs.pop('conId')})
            if 'localSymbol' in kwargs.keys():
                args.update({'localSymbol':kwargs.pop('localSymbol')})

            return Index(symbol, **args)

        elif symboltype == OPTION:

            if 'exchange' in kwargs.keys():
                args.update({'exchange':kwargs.pop('exchange')})
            if 'tradingClass' in kwargs.keys():
                args.update({'tradingClass':kwargs.pop('tradingClass')})
            if 'conId' in kwargs.keys():
                args.update({'conId': kwargs.pop('conId')})
            if 'right' in kwargs.keys():
                args.update({'right':kwargs.pop('right')})
            if 'strike' in kwargs.keys():
                args.update({'strike':kwargs.pop('strike')})
            if 'multiplier' in kwargs.keys():
                args.update({'multiplier':kwargs.pop('multiplier')})
            if 'localSymbol' in kwargs.keys():
                args.update({'localSymbol':kwargs.pop('localSymbol')})
            if 'lastTradeDateOrContractMonth' in kwargs.keys():
                args.update({'lastTradeDateOrContractMonth': 
                    kwargs.pop('lastTradeDateOrContractMonth')})

            return Option(symbol, **args)
        else:
            raise ('Symbol Type not found')

    def positions(self):
        print(self.client.positions())

    def gettickers(self, contract):
        self.client.reqMktData(contract)
        print(self.client.tickers())

    def close(self):
        self.client.disconnect()

    def _secs_duration(self, datetime):
        '''Get total seconds from datetime parameter to
        current time
        '''
        _datetime = pd.Timestamp(dt.datetime.now()) - pd.Timestamp(datetime)
        return str(int(_datetime.total_seconds()))


'''Shortcut to download and save data
'''
def run(args=None, **kwargs):
    import datautils
    output_fn = kwargs.pop('outputfile')
    ib_client = IBDataClient(
            kwargs.pop('host'), 
            kwargs.pop('port'),
            kwargs.pop('clientid'))
    dataframe = ib_client.getdata(**kwargs)
    datautils.save_data(dataframe, output_filename=output_fn)
    ib_client.close()

