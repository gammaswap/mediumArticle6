#!/usr/bin/env python3

import xlwings as xw
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import math
import time
import datetime
import csv
import os
import random

TICK_BASE = 1.0001

# ... (Other import statements)

# Function to initialize GraphQL client
def initialize_graphql_client():
    return Client(
        transport=RequestsHTTPTransport(
            url='https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3',
            verify=True,
            retries=5,
        )
    )

# Function to perform a GraphQL query
def perform_graphql_query(client, query, variables=None):
    try:
        return client.execute(gql(query), variable_values=variables)
    except Exception as ex:
        print(f"GraphQL query failed: {ex}")
        exit(-1)

# Function to calculate tick to price
def tick_to_price(tick):
    return TICK_BASE ** tick

# Function for standard normal variate using Box-Muller transform
def random_bm(mu, sigma):
    u = 0
    v = 0
    while u == 0:
        u = random.random()
    while v == 0:
        v = random.random()
    mag = sigma * math.sqrt(-2.0 * math.log(u))
    return mag * math.cos(2.0 * math.pi * v) + mu

# ... (Other functions)

# Main function to run the script
def main():
    client = initialize_graphql_client()

    # Example usage of perform_graphql_query
    query = """query get_positions($num_skip: Int, $pool_id: ID!) {
        pool(id: $pool_id) {
            id
            token0 {
                symbol
                decimals
            }
            token1 {
                symbol
                decimals
            }
        }
    }"""
    variables = {"num_skip": 0, "pool_id": "your_pool_id"}
    response = perform_graphql_query(client, query, variables)
    
    # ... (Other parts of your script)

# Run the main function if this script is executed
if __name__ == "__main__":
    main()
  
