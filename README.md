# mediumArticle6

The univ3lib.py file uses blocks.csv to get the correct blocks to request data from the graph about historical yields from UniswapV3.

printBlocksForDates.js: Gets correct blocks for certain dates and store them in the blocks.csv file. You will need an apiKey from infura that is set in the config.json file. You can use other endpoints to connect to the ethereum network.

The excel files call univ3lib.py an univ2lib.py to request Uniswap historical yield data from theGraph

The excel files need xlwings installed to call the python scripts. (https://docs.xlwings.org/en/stable/installation.html)

When requesting data from the graph, request in batches of 200 at most, otherwise theGraph will fail to respond.

Requesting UniV3 historical yield data from the graph queries all positions at the pool at a specific block. Therefore, it will take a long time for pools with a large number of positions like USDC-ETH and possibly fail due to overloading theGraph with too many requests. Since you can only request for a small batch of positions at a time from theGraph.


