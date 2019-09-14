
# Strategies

## Fade System

#### The strategy aims to capture price movements above or bellow the previous days VALUE AREA or HIGH LOW RANGE. The objective is to FADE (Counter trade) fast moving volatility price action based on the timeseries STD value using a pyramid sequence of trades to accumulate positions and improve the ‘average position’ price. 

#### The area to trade must be above or below the previous VAH, VAL, High, Low. The respective entry is determined from where the previous day closing price was relative to these parameters. 

#### For example, if the previous close is within close range (‘X percent’) of the VAH or VAL then the trade will only initiate above or bellow the previous day HIGH or LOW extreme instead. 

#### Entry sequence orders follow a fixed minimum ‘$ value’ between orders. In an example where entry sequence is [1,2,3 ,1,2,3] than each order will be a minimum $ between entries. The spacing between entry sequence is determined from the ‘nth ‘day ATR for the product. IE ATR for gold is $16 then spacing of sequence is some multiple of the ATR/ (number of trades in sequence). 

#### Exit is a single order for total position size. In the above example exit price will be 1503 for a total of 12 Gold contracts.


# Utils

 * OrderHandler

