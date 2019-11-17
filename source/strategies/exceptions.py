# -*- coding: utf-8 -*-

import backtrader.errors as bterr

class DirectionNotFound(bterr.BacktraderError):
    pass

class TradeModeNotFound(bterr.BacktraderError):
    pass

class OrderNotExecuted(bterr.BacktraderError):
    pass

class StopsCalculationError(bterr.BacktraderError):
    pass
