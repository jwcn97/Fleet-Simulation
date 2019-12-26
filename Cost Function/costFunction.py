import pandas as pd
import numpy as np
import math
from sim import *

def rcMultiplier(address):
    # cpList = list of CPs within 6miles of the address
    # rcProb = cpList/(max possible CPs)
    # rcIssues = (number of CPs in cpList with issues)/cpList
    # rcAvailable = (available CPs in cpList)/cpList
    
    rcProb, rcIssues, rcAvailable = 0.4, 0.9, 0.8
    
    return 1/(rcProb * rcIssues * rcAvailable)

def costFunction(cpsNum, cpfNum, carNum, rcProb):
    ########################### SIMULATION PARAMETERS ###########################
    days = 5 * 52
    
    # charge parameters
    battSize = 38 # nissan leaf
    mile_range = 115 # 95 - 200 mi
    cpsRate, cpfRate, rcRate = 3, 7, 22 # kw/hr

    depotLimit = 35
    
    # fixed cost
    cpsCost, cpfCost = 300, 650
    carCost, depotCost = 29255, 30000
    
    # variable cost
    lowTariff, highTariff = 0.05, 0.14
    period = "00:30:00-04:30:00"
    rcTariff, connectionFee = 0.39, 1
    rcCostMultiplier = 1/(rcProb * 0.9 * 0.8)
    # rcCostMultiplier = rcMultiplier('depot address')
    
    ########################### RUN SIMULATION ###########################
    carData, depotNum = runSimulation("shift3", (cpsNum,cpsRate), (cpfNum,cpfRate),
                                      (lowTariff,highTariff,period),
                                      carNum, battSize, depotLimit)

    ########################### CALCULATE COST ###########################
    # OCTOPUS: LT Period (12:30 ~ 16:30), LT price: £0.05, HT price: £0.14
    # ECOTRICITY: RC price: £0.39
    
    # FIXED COST
    cpTotal = (cpsNum * cpsCost) + (cpfNum * cpfCost)
    carTotal = carNum * carCost
    depotTotal = depotNum * depotCost

    # VARIABLE COST
    chargeCost = carData.kwSupplied * highTariff
    rcCost = (carData.toRC * rcTariff) + (carData.connection * connectionFee)

    return cpTotal + carTotal + depotTotal + days*(chargeCost + rcCost * rcCostMultiplier)

def gradient_descent(cars, limit):
    # define limits
    start_cps, end_cps = 3, 10
    start_cpf, end_cpf = 3, 10
    # set minimum
    min_cps = start_cps
    min_cpf = start_cpf
    min_cost = costFunction(start_cps, start_cpf, cars, limit)

    # Run the gradient
    for cpsNum in range(start_cps, end_cps+1):
        for cpfNum in range(start_cpf, end_cpf+1):
            # compute cost
            cost = costFunction(cpsNum, cpfNum, cars, limit)
            # update values if min is found
            if cost < min_cost:
                min_cps, min_cpf = cpsNum, cpfNum
                min_cost = cost
    
    # Return minimum combination of values
    return min_cps, min_cpf, min_cost

display = pd.DataFrame(columns=['cars', 'rcProb', 'slow CPs', 'fast CPs', 'min cost'])

# define limits
min_cars, max_cars, c_inc = 15, 30, 5
min_limit, max_limit, limit_inc = 35, 44, 2

limit = [0.1,0.2,0.3,0.4,0.5]
min_limit, max_limit, limit_inc = 0,4,1

for cars in range(min_cars, max_cars+1, c_inc):
    for i in range(min_limit, max_limit+1, limit_inc):
        cps, cpf, cost = gradient_descent(cars, limit[i])
        display = display.append({
            'cars': cars,
            'rcProb': limit[i],
            'slow CPs': cps,
            'fast CPs': cpf,
            'min cost': cost
        }, ignore_index=True)

display.to_csv('test.csv')