#!/usr/bin/env python3

import xlwings as xw

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import math
import time
import datetime
import sys
import json

# seed the pseudorandom number generator
from random import random


client = Client(
    transport=RequestsHTTPTransport(
        url='https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2',
        verify=True,
        retries=5,
    ))

#We'll do 200 days for now
def getHistoricalYields(sheetName, colName0, colName1, colName2, colName3, colName4, colName5, colName6, colName7, colName8, colName9, rowNum, poolId, daysBack, startNum) :
	wb = xw.Book.caller()
	sht = wb.sheets[sheetName]

	#poolId = "0xbb2b8038a1640196fbe3e38816f3e67cba72d940"

	pool_query_historical = """query get_pairDayDatas("""
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
		pool_query_body = pool_query_body + """ day{}: pairDayData(id: $pair_id{}) {{
			date
			reserve0
			reserve1
			reserveUSD
			dailyVolumeUSD
			totalSupply
			dailyTxns
		}}""".format(i, i)
		variables["pair_id{}".format(i)] = poolId + "-{}".format(startNum + i)
		i += 1

	pool_query_historical = pool_query_historical + pool_query_heading + """) { 
		""" + pool_query_body + """
		}"""

	try:
		response = client.execute(gql(pool_query_historical), variable_values=variables)

		r = rowNum
		tradeDate = 0
		reserve0 = 0
		reserve1 = 0
		totalSupply = 0
		reserveUSD = 0
		i = 0
		while _daysBack > 0 :
			_daysBack -= 1
			rowNumStr = "{}".format(r)
			if response["day{}".format(i)] is None :
				sht.range(colName0 + rowNumStr).value = datetime.datetime.fromtimestamp(tradeDate)

				sht.range(colName1 + rowNumStr).value = reserve0
				sht.range(colName2 + rowNumStr).value = reserve1
				sht.range(colName3 + rowNumStr).value = totalSupply
				sht.range(colName4 + rowNumStr).value = 0

				sht.range(colName5 + rowNumStr).value = reserveUSD
				sht.range(colName6 + rowNumStr).value = 0
				sht.range(colName7 + rowNumStr).value = 0
				sht.range(colName8 + rowNumStr).value = 0
				sht.range(colName9 + rowNumStr).value = startNum + i
			else:
				tradeDate = int(response["day{}".format(i)]["date"])
				reserve0 = float(response["day{}".format(i)]["reserve0"])
				reserve1 = float(response["day{}".format(i)]["reserve1"])
				reserveUSD = float(response["day{}".format(i)]["reserveUSD"])
				dailyVolumeUSD = float(response["day{}".format(i)]["dailyVolumeUSD"])
				totalSupply = float(response["day{}".format(i)]["totalSupply"])
				dailyTxns = int(response["day{}".format(i)]["dailyTxns"])
				feesUSD = (dailyVolumeUSD) * 0.003
				sht.range(colName0 + rowNumStr).value = datetime.datetime.fromtimestamp(tradeDate)

				sht.range(colName1 + rowNumStr).value = reserve0
				sht.range(colName2 + rowNumStr).value = reserve1
				sht.range(colName3 + rowNumStr).value = totalSupply
				sht.range(colName4 + rowNumStr).value = dailyTxns

				sht.range(colName5 + rowNumStr).value = reserveUSD
				sht.range(colName6 + rowNumStr).value = dailyVolumeUSD
				sht.range(colName7 + rowNumStr).value = feesUSD
				sht.range(colName8 + rowNumStr).value = feesUSD * 365 / reserveUSD
				sht.range(colName9 + rowNumStr).value = startNum + i
				
			tradeDate = tradeDate + 60 * 60 * 24
			r += 1
			i += 1
	except Exception as ex:
		print("got exception while querying pair data:", ex)
		exit(-1)


