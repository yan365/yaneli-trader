# -*- coding: utf-8 -*-

from ib_insync import *
import datetime as dt
import pandas as pd

HOST = '127.0.0.1'
PORT = 7497
CLIENT_ID = '1234'

# Data Client Contract Types
FOREX = 'Forex'
FUTURES = 'Futures'
INDEX = 'Index'
OPTION = 'Option'
STOCK = 'Stock'

def getcontract(symbol, symboltype, **kwargs):
    '''Get contract based on symbol name and contract types.
    '''

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
    
def secs_duration(datetime):
    '''Get total seconds from datetime parameter to current time.
    '''
    _datetime = pd.Timestamp(dt.datetime.now()) - pd.Timestamp(datetime)
    return str(int(_datetime.total_seconds()))

def get_timestamp(_datetime, _format='%Y-%m-%d %H:%M:%S'):
    '''Get timestamp from datetime string
    '''
    return dt.datetime.strptime(_datetime, _format).timestamp()



class IBDataClient:
    '''Client with functions to handle data, get account information, 
    positions and order state, trades executed.
    '''

    def __init__(self, host, port, clientid):
        self.client = IB()
        self.client.connect(host, port, clientid)

    def connected(self):
        '''Check if api client is connected.
        '''
        return self.client.isConnected()

    def close(self):
        '''Disconnect the ib_insync api.
        '''
        self.client.disconnect()

    def getaccountvalues(self):
        av = self.client.accountValues()
        df = pd.DataFrame()
        for account_value in av:
            if account_value.value != '0.00' and \
                    account_value.currency != '':
                df = df.append(pd.DataFrame({
                    'Tag':account_value.tag,
                    'Value':account_value.value,
                    'Currency':account_value.currency}, 
                    index=[0]))
        return df

    def getaccountsummary(self, account=''):
        '''
        '''
        accounts =  self.client.accountSummary(account)
        acc = pd.DataFrame()
        for account in accounts:
            print(account)
            if str(account.value) != '0.00':
                acc = acc.append(pd.DataFrame({
                    'Currency':account.currency,
                    'Tag':account.tag,
                    'Value':account.value,
                    'Model Code':account.modelCode,
                    }, index=[account.tag]))
        return acc

    def getcompletedorders(self, apionly=True):
        '''Request the completed orders and return dataframes with information of
        contracts, executions commission.
        '''
        orders = self.client.reqCompletedOrders(apionly)
        con, exe, rep = [],[],[]
        for order in orders:
            con.append(order[0])
            exe.append(order[1])
            rep.append(order[2])
        contracts= util.df(con)
        executions = util.df(exe)
        reports = util.df(rep)
        return contracts, executions, reports
    
    def getcontractdetails(self, contract):
        '''Return all information available about the contract.
        '''
        return util.df(self.client.reqContractDetails(contract))

    def getdata(self, symbol, symboltype, exchange='IDEALPRO', 
            currency='USD', timeframe='1 secs', duration='1 D', 
            **kwargs):
        '''Download data and return as Data Frame.
        The input parameters 'timeframe' and 'duration' is set in same way of ib_insync api.
        '''

        contract_args = {
                'symbol':symbol,
                'symboltype':symboltype,
                'exchange':exchange,
                'currency':currency,
                }
        contract_args.update(**kwargs)
        contract = getcontract(**contract_args)

        data_args = {
                'contract':contract,
                'barSizeSetting':timeframe,
                'durationStr':duration,
                'endDateTime':'',
                'whatToShow':'MIDPOINT',
                'useRTH':True,
                }
        dataframe = util.df(self.client.reqHistoricalData(**data_args))
        dataframe = dataframe.rename(
                columns={'close':'Close', 
                    'open':'Open',
                    'date':'datetime',
                    'high':'High', 
                    'low':'Low'})
        return dataframe

    def getdata_fromct(self, contract, timeframe='1 secs', duration='1 D'):
        '''Get data with contract as input parameter.
        '''
        data_args = {
                'contract':contract,
                'barSizeSetting':timeframe,
                'durationStr':duration,
                'endDateTime':'',
                'whatToShow':'MIDPOINT',
                'useRTH':True,
                }
        dataframe = util.df(self.client.reqHistoricalData(**data_args))

        dataframe = dataframe.rename(
                columns={'close':'Close', 
                    'open':'Open',
                    'date':'datetime', 
                    'high':'High', 
                    'low':'Low'})
        return dataframe

    def getdata_fromdt(self, symbol, symboltype, exchange='IDEALPRO', 
            currency='USD', timeframe='1 secs', 
            fromdate= dt.datetime(2015,1,1), 
            todate= dt.datetime.now(), **kwargs):

        '''Download data and return as Data Frame. 
        The input parameters 'fromdate' and 'todate' is set in same than backtrader backtests, 
        then is converted internally for ib_insync api input mode.
        '''

        durationstr = self.secs_duration(fromdate) + ' S'

        contract_args = {
                'symbol':symbol,
                'symboltype':symboltype,
                'exchange':exchange,
                'currency':currency,
                }
        contract_args.update(**kwargs)
        contract = getcontract(**contract_args)

        data_args = {
                'contract':contract,
                'barSizeSetting':timeframe,
                'durationStr':durationstr,
                'endDateTime':todate,
                'whatToShow':'MIDPOINT',
                'useRTH':True,
                }
        
        dataframe = util.df(self.client.reqHistoricalData(**data_args))
        dataframe = dataframe.rename(
                columns={'close':'Close', 
                    'open':'Open',
                    'date':'datetime', 
                    'high':'High', 
                    'low':'Low'})
        return dataframe
            

    def getearliestbar(self, symbol, symboltype, exchange, **kwargs):
        '''Get oldest bar date
        '''
        contract = getcontract(symbol, symboltype, exchange, **kwargs)
        args = {
                'contract':contract,
                'whatToShow':'MIDPOINT',
                'useRTH':True,
                }

        return self.client.reqHeadTimeStamp(**args)

    def getexecutions(self):
        '''Request the executions and return dataframes with contracts, executions and commission information.
        '''
        executions = self.client.reqExecutions()
        con, exe, rep = [], [], []
        for execution in executions:
            con.append(execution[0])
            exe.append(execution[1])
            rep.append(execution[2])
        contracts = util.df(con)
        executions = util.df(exe)
        reports = util.df(rep)
        return contracts, executions, reports

    def getfills(self):
        '''Get last fills from client. Return dataframes of contracts, execution and commission.
        '''
        fills = self.client.fills()
        con, exe, rep = [],[],[]
        for fill in fills:
            con.append(fill[0])
            exe.append(fill[1])
            rep.append(fill[2])
        contracts= util.df(con)
        executions = util.df(exe)
        reports = util.df(rep)
        return contracts, executions, reports
    
    def getmarketrules(self, contract):
        '''Get market rules of the contract.
        '''
        details = self.client.reqContractDetails(contract)
        return self.client.reqMarketRule(details[0].marketRuleIds)

    def getpositions(self, symbol=None):
        '''Return tuple with dataframes of positions and contracts.
        If filter input parameter is not None, than it's used for 
        filtering by symbol.
        '''
        positions = self.client.positions()

        df = pd.DataFrame()
        for position in positions:
            df = df.append(pd.DataFrame({
                'Symbol':position[1].symbol,
                'Currency':position[1].currency,
                'conId':str(position[1].conId),
                'localSymbol':str(position[1].localSymbol),
                'Lots':position[2],
                'Average Cost':position[3]}, index=[0]))

        if symbol == None:
            return df

        else:
            return df[ df['Symbol'] == str(symbol) ]

    def getfuturespnl(self, account=''):
        '''Return the Futures PnL of the current state of account, and not from the current session.
        '''
        df = pd.DataFrame()
        summaries = self.client.accountValues()
        for summary in summaries:
            if summary.tag == 'FuturesPNL':
                df = df.append(pd.DataFrame({
                    'Tag': summary.tag,
                    'Value': summary.value,
                    'Currency': summary.currency}, 
                    index=[0]))
        return df

    def getpnl(self, currency):
        av = self.client.accountValues()
        df = pd.DataFrame()
        for account_value in av:
            if account_value.currency == str(currency) and \
                    account_value.tag == 'UnrealizedPnL':
                df = df.append(pd.DataFrame({
                    'Tag':account_value.tag,
                    'Value':account_value.value,
                    'Currency':account_value.currency}, 
                    index=[0]))
        return df

    def getticksize(self, contract):
        '''Get the minimum variation of price (tick size).
        '''
        details = self.client.reqContractDetails(contract)
        return float(details[0].minTick)

    def getticksize_df(self, contract):
        '''Return a dataframe with symbol, contract type, exchange and tick size.
        '''
        details = self.client.reqContractDetails(contract)
        con_str = str(contract).split(',')
        p1 = con_str[0]
        _p1 = p1.split('(')
        type_str = _p1[0]
        symbol_str = _p1[1] 
        p2 = con_str[1]
        _p2 = p2.split('=')
        exchange_str = _p2[1]
        return pd.DataFrame({
            'Symbol':symbol_str.replace("'", ""),
            'Tick Size':details[0].minTick, 
            'Exchange':exchange_str.replace("'", "").replace(")", ""),
            'Contract Type':type_str,
            }, index=[0])


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

