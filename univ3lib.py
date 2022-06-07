#!/usr/bin/env python3

import xlwings as xw

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import math
import time
import datetime
import sys
import json
import csv
import os

# seed the pseudorandom number generator
#from random import seed
from random import random

TICK_BASE = 1.0001

pool_query = """query get_positions($num_skip: Int, $pool_id: ID!) {
  pool(id: $pool_id) {
    id
    token0{
      symbol
      decimals
    }
    token1{
      symbol
      decimals
    }
  }
}"""

def tick_to_price(tick):
    return TICK_BASE ** tick

client = Client(
    transport=RequestsHTTPTransport(
        url='https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3',
        verify=True,
        retries=5,
    ))

#Standard Normal variate using Box-Muller transform.
def random_bm(mu, sigma):
    u = 0
    v = 0
    while(u == 0): 
        u = random() #Converting [0,1) to (0,1)
    while(v == 0): 
        v = random()
    mag = sigma * math.sqrt( -2.0 * math.log( u ) )
    return mag * math.cos( 2.0 * math.pi * v ) + mu
    #return mag * math.sin( 2.0 * math.pi * v ) + mu; //alternatively

def calcImpLoss(lowerLimit, upperLimit, px):
    r = math.sqrt(upperLimit/lowerLimit)

    a1 = (math.sqrt(r) - px)/(px + 1)
    a2 = (math.sqrt(r) / (math.sqrt(r) - 1)) * (2*math.sqrt(px)/(px + 1) - 1)
    a3 = (math.sqrt(r) * px - 1)/(px + 1)

    if(px < 1/r):
        return a3
    elif(px > r): 
        return a1
    
    return a2;

def calcExpImpLoss(rangePerc, yearlySigma) :
    upperPx = 1 + rangePerc
    lowerPx = 1/upperPx
    dailySigma = yearlySigma/math.sqrt(365)
    impLossSum = 0
    numTries = 10000
    mu = 0
    for i in range(numTries) :
        t = 1
        W = random_bm(0, 1) * math.sqrt(t-0)
        X = (math.log(1 + mu) - 0.5 * math.pow(math.log(1 + dailySigma), 2)) * t + math.log(1 + dailySigma) * W
        _px = math.exp(X)
        impLossSum += calcImpLoss(lowerPx, upperPx, _px)

    return impLossSum/numTries

def calExpectedCost(rowNum, rangeCol, sigmaCol, costCol) :
    wb = xw.Book.caller()
    sht = wb.sheets["UniV3Monitor"]

    rangePerc = float(sht.range(rangeCol + rowNum).value)
    sigma = float(sht.range(sigmaCol + rowNum).value)

    meanImpLoss = calcExpImpLoss(rangePerc, sigma)

    sht.range(costCol + rowNum).value = meanImpLoss


#returns dictionary of array [timeStr, blockNumber, timestamp] indexed numerically in increments of 1, starting at 0, from blocks.csv file
def getBlocks(fileName, startIdx, endIdx) :
    blocks = {}
    with open(fileName, 'r') as file:
        reader = csv.reader(file)
        first = True;
        i = 0;
        j = 0;
        for row in reader:
            if first :
                first = False;
                continue;
            if j >= startIdx and j <= endIdx :
                blocks[i] = row;
                print(row)
                i += 1
            j += 1

    _blocks = {};
    j = 0;
    while i > 0:
        _blocks[j] = blocks[i-1];
        i -= 1;
        j += 1;
    return _blocks;

def getActiveLiquidity(positions, currentTick) :
    active_positions_liquidity = 0
    for item in positions:
        tick_lower = int(item["tickLower"]["tickIdx"])
        tick_upper = int(item["tickUpper"]["tickIdx"])
        liquidity = int(item["liquidity"])
        id = int(item["id"])
        if tick_lower < currentTick < tick_upper:
            active_positions_liquidity += liquidity
    return active_positions_liquidity

def getHistoricalActiveLiquidity(sheetName, colName0, colName1, colName2, colName3, colName4, colName5, colName6, colName7, colName8, colName9, rowNum, poolId, startIdx, periods) :
    #poolId = "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8"
    #sht = 0;
    wb = xw.Book.caller()
    sht = wb.sheets[sheetName]
    
    foldername = os.path.dirname(wb.fullname)
    blocks = getBlocks(foldername + "\\blocks.csv", startIdx, startIdx + periods) #dictionary of [timeStr, blockNumber, timestamp]

    decimals0num = 0;
    decimals1num = 0;

    try:
        response = client.execute(gql(pool_query), variable_values={"pool_id": poolId})
        decimals0num = int(response['pool']['token0']['decimals']);
        decimals1num = int(response['pool']['token1']['decimals']);
    except Exception as ex:
        print("got exception while querying pool data:", ex)
        exit(-1)

    getHistoricalActiveLiquidityPart(sht, colName0, colName1, colName2, colName3, colName4, colName5, colName6, colName7, colName8, colName9, rowNum, poolId, startIdx, blocks, decimals0num, decimals1num)

def getHistoricalActiveLiquidityPart(sht, colName0, colName1, colName2, colName3, colName4, colName5, colName6, colName7, colName8, colName9, rowNum, poolId, startIdx, blocks, decimals0num, decimals1num) :

    position_query_historical = """query get_positions($pool_id: ID! """
    position_query_heading = "";
    position_query_body = "";

    pool_query_historical = """query get_pools($pool_id: ID! """
    pool_query_heading = "";
    pool_query_body = "";

    variables = {"pool_id": poolId}
    variablesPos = {"pool_id": poolId}

    i = 0
    posKeys = {}
    persBackTemp = len(blocks)
    while persBackTemp > 0:
        persBackTemp -= 1
        position_query_heading = position_query_heading + (", $num_skip{} : Int!, $bn{} : Int!").format(i, i)
        position_query_body = position_query_body + """ pos{}: positions(skip: $num_skip{}, where:{{pool: $pool_id, liquidity_gt: 0}}, block:{{number: $bn{}}}) {{
            id
            tickLower {{ tickIdx }}
            tickUpper {{ tickIdx }}
            liquidity
        }}""".format(i, i, i)
        posKeys[i] = "pos{}".format(i)
        pool_query_heading = pool_query_heading + (", $bn{} : Int!").format(i)
        pool_query_body = pool_query_body + """ pol{}: pool(id: $pool_id, block:{{number: $bn{}}}) {{
            tick
            volumeUSD
            volumeToken0
            volumeToken1
            feesUSD
        }}""".format(i, i)
        variables["bn{}".format(i)] = int(blocks[i][1])
        variablesPos["bn{}".format(i)] = int(blocks[i][1])
        variablesPos["num_skip{}".format(i)] = 0
        i += 1

    position_query_historical = position_query_historical + position_query_heading + """) { 
    """ + position_query_body + """
     }"""
    pool_query_historical = pool_query_historical + pool_query_heading + """) { 
    """ + pool_query_body + """
     }"""

    activeLiq = {}
    numSkips = [0] * i
    currTick = {}
    try:
        response = client.execute(gql(pool_query_historical), variable_values=variables)
        r = rowNum
        first = True
        prevVolumeUSD = 0
        prevVolumeToken0 = 0
        prevVolumeToken1 = 0
        prevFeesUSD = 0
        j = i
        idx = startIdx + 1
        while i > 0 :
            currTick["pol{}".format(i-1)] = int(response["pol{}".format(i-1)]["tick"])
            if first :
                prevVolumeUSD = float(response["pol{}".format(i-1)]["volumeUSD"])
                prevVolumeToken0 = float(response["pol{}".format(i-1)]["volumeToken0"])
                prevVolumeToken1 = float(response["pol{}".format(i-1)]["volumeToken1"])
                prevFeesUSD = float(response["pol{}".format(i-1)]["feesUSD"])
                first = False
            else :
                rowNumStr = "{}".format(r)
                volumeUSD = float(response["pol{}".format(i-1)]["volumeUSD"])
                volumeToken0 = float(response["pol{}".format(i-1)]["volumeToken0"])
                volumeToken1 = float(response["pol{}".format(i-1)]["volumeToken1"])
                feesUSD = float(response["pol{}".format(i-1)]["feesUSD"])
                sht.range(colName0 + rowNumStr).value = datetime.datetime.fromtimestamp(int(blocks[i-1][2]))
                sht.range(colName1 + rowNumStr).value = volumeUSD - prevVolumeUSD
                sht.range(colName2 + rowNumStr).value = volumeToken0 - prevVolumeToken0
                sht.range(colName3 + rowNumStr).value = volumeToken1 - prevVolumeToken1
                sht.range(colName4 + rowNumStr).value = feesUSD - prevFeesUSD
                sht.range(colName9 + rowNumStr).value = idx
                prevVolumeUSD = volumeUSD
                prevVolumeToken0 = volumeToken0
                prevVolumeToken1 = volumeToken1
                prevFeesUSD = feesUSD
                r += 1
                idx += 1
            i -= 1
        
        while True:
            response = client.execute(gql(position_query_historical), variable_values=variablesPos)

            # reset the query
            position_query_historical = """query get_positions($pool_id: ID! """
            position_query_heading = ""
            position_query_body = ""

            items = posKeys.copy().items()
            itemsLen = len(items)
			
            if itemsLen == 0 :
                break
            for k, v in items :
                if len(response[v]) == 0:
                    itemsLen -= 1
                    del posKeys[k]
                    del variablesPos["bn{}".format(k)]
                    del variablesPos["num_skip{}".format(k)]
                    continue
                numSkips[k] += len(response[v])
                variablesPos["num_skip{}".format(k)] = numSkips[k]
                if v in activeLiq : 
                    activeLiq[v] += getActiveLiquidity(response[v], currTick["pol{}".format(k)])
                else:
                    activeLiq[v] = getActiveLiquidity(response[v], currTick["pol{}".format(k)])

                position_query_heading = position_query_heading + (", $num_skip{} : Int!, $bn{} : Int!").format(k, k)
                position_query_body = position_query_body + """ pos{}: positions(skip: $num_skip{}, where:{{pool: $pool_id, liquidity_gt: 0}}, block:{{number: $bn{}}}) {{
                    id
                    tickLower {{ tickIdx }}
                    tickUpper {{ tickIdx }}
                    liquidity
                }}""".format(k, k, k)
            #break
            if itemsLen == 0 :
                break
            position_query_historical = position_query_historical + position_query_heading + """) { 
            """ + position_query_body + """
             }"""

        decimalsDiff = decimals1num - decimals0num

        r = rowNum
        while j > 0 :
            if first :
                rowNumStr = "{}".format(r)
                sht.range(colName5 + rowNumStr).value = float(activeLiq["pos{}".format(j-1)])
                sht.range(colName6 + rowNumStr).value = numSkips[j-1]
                priceC = tick_to_price(currTick["pol{}".format(j-1)])
                adjusted_priceC = priceC / (10 ** (decimalsDiff))
                sht.range(colName7 + rowNumStr).value = adjusted_priceC
                sht.range(colName8 + rowNumStr).value = adjusted_priceC = 1/adjusted_priceC
                r += 1
            else:
                first = True
            j -= 1
        
    except Exception as ex:
        print("got exception while querying pool data:", ex)
        exit(-1)


def getHistoricalYields(sheetName, colName0, colName1, colName2, colName3, colName4, colName5, colName6, colName7, colName8, colName9, colName10, colName11, colName12, colName13, rowNum, poolId, daysBack, startNum) :
    wb = xw.Book.caller()
    sht = wb.sheets[sheetName]

    #poolId = "0xbb2b8038a1640196fbe3e38816f3e67cba72d940"
    res = sheetName + " " + colName0 + " " + colName1 + " " + colName2 + " " + colName3 + " " + colName4 + " {} " + poolId + " {}"

    pool_query_historical = """query get_poolDayDatas("""
    pool_query_heading = "";
    pool_query_body = "";

    variables = {}

    i = 0
    firstNum = True
    _daysBack = daysBack
    while daysBack > 0:
        daysBack -= 1
        if firstNum :
            firstNum = False
            pool_query_heading = pool_query_heading + ("$pair_id{} : ID!").format(i)
        else :    
            pool_query_heading = pool_query_heading + (", $pair_id{} : ID!").format(i)
        pool_query_body = pool_query_body + """ day{}: poolDayData(id: $pair_id{}) {{
            date
            liquidity
            tvlUSD
            volumeUSD
            feesUSD
            txCount
            token0Price
            token1Price
            open
            high
            low
            close
        }}""".format(i, i)
        variables["pair_id{}".format(i)] = poolId + "-{}".format(startNum + i)#18387
        #variables["pair_id{}".format(i)] = poolId + "-{}".format(19112 + i)
        i += 1

    pool_query_historical = pool_query_historical + pool_query_heading + """) { 
     """ + pool_query_body + """
      }"""
    
    try:
        response = client.execute(gql(pool_query_historical), variable_values=variables)

        r = rowNum
        tradeDate = 0
        liquidity = 0
        tvlUSD = 0
        volumeUSD = 0
        feesUSD = 0
        txCount = 0
        token0Price = 0
        token1Price = 0
        op = 0
        hi = 0
        lo = 0
        cl = 0
        i = 0
        while _daysBack > 0 :
            _daysBack -= 1
            rowNumStr = "{}".format(r)
            if response["day{}".format(i)] is None :
                print("is none")
                sht.range(colName0 + rowNumStr).value = datetime.datetime.fromtimestamp(tradeDate)

                sht.range(colName1 + rowNumStr).value = liquidity
                sht.range(colName2 + rowNumStr).value = tvlUSD
                sht.range(colName3 + rowNumStr).value = 0
                sht.range(colName4 + rowNumStr).value = 0

                sht.range(colName5 + rowNumStr).value = 0
                sht.range(colName6 + rowNumStr).value = token0Price
                sht.range(colName7 + rowNumStr).value = token1Price
                sht.range(colName8 + rowNumStr).value = cl
                sht.range(colName9 + rowNumStr).value = cl
                sht.range(colName10 + rowNumStr).value = cl
                sht.range(colName11 + rowNumStr).value = cl
                sht.range(colName12 + rowNumStr).value = 0
                sht.range(colName13 + rowNumStr).value = startNum + i
            else:
                tradeDate = int(response["day{}".format(i)]["date"])
                liquidity = float(response["day{}".format(i)]["liquidity"])
                tvlUSD = float(response["day{}".format(i)]["tvlUSD"])
                volumeUSD = float(response["day{}".format(i)]["volumeUSD"])
                feesUSD = float(response["day{}".format(i)]["feesUSD"])
                txCount = int(response["day{}".format(i)]["txCount"])
                token0Price = float(response["day{}".format(i)]["token0Price"])
                token1Price = float(response["day{}".format(i)]["token1Price"])
                op = float(response["day{}".format(i)]["open"])
                hi = float(response["day{}".format(i)]["high"])
                lo = float(response["day{}".format(i)]["low"])
                cl = float(response["day{}".format(i)]["close"])
                sht.range(colName0 + rowNumStr).value = datetime.datetime.fromtimestamp(tradeDate)

                sht.range(colName1 + rowNumStr).value = liquidity
                sht.range(colName2 + rowNumStr).value = tvlUSD
                sht.range(colName3 + rowNumStr).value = volumeUSD
                sht.range(colName4 + rowNumStr).value = feesUSD

                sht.range(colName5 + rowNumStr).value = txCount
                sht.range(colName6 + rowNumStr).value = token0Price
                sht.range(colName7 + rowNumStr).value = token1Price

                sht.range(colName8 + rowNumStr).value = op
                sht.range(colName9 + rowNumStr).value = hi
                sht.range(colName10 + rowNumStr).value = lo
                sht.range(colName11 + rowNumStr).value = cl

                if tvlUSD > 0 :
                    sht.range(colName12 + rowNumStr).value = feesUSD * 365 / tvlUSD
                else :
                    sht.range(colName12 + rowNumStr).value = 0

                sht.range(colName13 + rowNumStr).value = startNum + i
            tradeDate = tradeDate + 60 * 60 * 24
            r += 1
            i += 1
    except Exception as ex:
        print("got exception while querying pair data:", ex)
        exit(-1)

