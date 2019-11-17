#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('../source/')

from dataclient import *
import datetime as dt
from tabulate import tabulate

HOST = '127.0.0.1'
PORT = 7497
CLIENT_ID = 1234

SYMBOL = 'EURUSD'

client = IBDataClient(HOST, PORT, CLIENT_ID)

acc = client.getaccountsummary()
print("\nGet Account Summary")
print(tabulate(acc, headers='keys', tablefmt='psql', showindex=False))

contract_eurusd = getcontract(SYMBOL, FOREX)

print('\nMarket Rules')
marketrules = client.getmarketrules(contract_eurusd)
print(tabulate(marketrules, headers='keys', tablefmt='psql', showindex=False))

print('\nGet Tick Size')
ticksize = client.getticksize_df(contract_eurusd)
print(tabulate(ticksize, headers='keys', tablefmt='psql', showindex=False))

print('\nGet fills (Contract, Execution, Report)')
contract, execution, report = client.getfills()
print(tabulate(contract, headers='keys', tablefmt='psql', showindex=True))
print(tabulate(execution, headers='keys', tablefmt='psql', showindex=True))
print(tabulate(report, headers='keys', tablefmt='psql', showindex=True))

print('\nGet Positions')
pos, con = client.getpositions()
print(tabulate(pos, headers='keys', tablefmt='psql', showindex=True))
print(tabulate(con, headers='keys', tablefmt='psql', showindex=True))

print('\nGet Positions (Filtered)')
pos, con = client.getpositions(SYMBOL)
print(tabulate(pos, headers='keys', tablefmt='psql', showindex=False))
print(tabulate(con, headers='keys', tablefmt='psql', showindex=False))

client.close()

