# -*- coding: utf-8 -*-

from ib_insync import *

HOST = '127.0.0.1'
PORT = 7497
CLIENT_ID = '1234'

FOREX = 'Forex'
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
        if symboltype == FOREX:
            return Forex(symbol, 
                    exchange= kwargs['exchange'])
        elif symboltype == STOCK:
            return Stock(symbol, 
                    exchange= kwargs['exchange'],
                    currency= kwargs['currency'])
        else:
            raise ('Symbol Type not found')

    def close(self):
        self.client.disconnect()

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

