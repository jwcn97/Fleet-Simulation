import pandas as pd
import numpy as np
import datetime as dt
import time
from chargingFunctions import *

# SELECT RAPID CHARGE INFORMATION
rcDuration = 30     # RAPID CHARGE DURATION (MINUTES)
rcPerc = 20         # WHAT PERCENTAGE TO START RAPID CHARGING (%)
rcRate = 50         # RATE OF RAPID CHARGING (KW/HR)

# CHOOSE START TIME AND RUN TIME
startTime = readTime("2019-01-01 06:00:00")
runTime = 24*5

# initialise data frame
performance = pd.DataFrame(columns=['price','mpkw','fleetType','schedule',
                                    'dumbRC','leavetimeRC','battRC','smartRC','costRC',
                                    'dumbCost','leavetimeCost','battCost','smartCost','costCost'])

priceDF = pd.read_csv("csv/prices.csv", sep=";", index_col=None)
fleetDF = pd.read_csv("csv/fleetData.csv", sep=";", index_col=None)
breakDF = pd.read_csv("csv/breaks.csv", sep=";", index_col=None)

def costDifference(df, batt_size, price):
    original = df.totalCost.iloc[-1]
    extra = df.iloc[-4:].batt.apply(lambda x: batt_size-x).sum()*price
    return original + extra

import glob
for priceType in range(0,2):
    for hasBreak in range(0,3):
        for drives in glob.glob('csv/driving/*.csv'):
            for fleetType in range(0,12):
                for schedules in glob.glob('csv/schedules/*.csv'):
                    company = priceDF.loc[priceType, 'company']
                    mpkw = drives.split("\\")[1][0:-4]
                    schedule = schedules.split("\\")[1][:-4]
                    print("\n" + schedule + "_" + company + "_" + mpkw + "_fleetType" + str(fleetType))
                    print("----------------------------------------")
                    
                    allShiftsDF = pd.read_csv("csv/schedules/" + schedule + ".csv", sep=";", index_col=None)
                    drivingDF = pd.read_csv("csv/driving/" + mpkw + ".csv", sep=";", index_col=None)
                    fleetData = fleetDF.loc[fleetDF.index == fleetType]
                    pricesDF = priceDF.loc[priceDF.company == company]
                    breaksDF = breakDF.loc[breakDF.id == hasBreak]
                    print("   finish importing data")

                    dumbDF, dumbRC, dumbCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                                        fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF,
                                        dumbCharge)
                    print("   finish dumb charging")

                    leavetimeDF, leavetimeRC, leavetimeCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                                        fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF,
                                        smartCharge_leavetime)
                    print("   finish leavetime charging")

                    battDF, battRC, battCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                                        fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF,
                                        smartCharge_batt)
                    print("   finish battleft charging")

                    smartDF, smartRC, smartCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                                        fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF,
                                        smartCharge_battOverLeavetime)
                    print("   finish battleft/leavetime charging")

                    costDF, costRC, costCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                                        fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF,
                                        costSensitiveCharge)
                    print("   finish cost-sensitive charging")

                    # get the battery size and price
                    batt_size = dumbDF.iloc[0].batt
                    price = pricesDF.loc[priceType, 'priceRedZone']
                    
                    # get relevant costs
                    dumb_cost = costDifference(dumbDF, batt_size, price)
                    leavetime_cost = costDifference(leavetimeDF, batt_size, price)
                    batt_cost = costDifference(battDF, batt_size, price)
                    smart_cost = costDifference(smartDF, batt_size, price)
                    cost_cost = costDifference(costDF, batt_size, price)

                    performance = performance.append({
                        'price': company,
                        'mpkw': mpkw,
                        'fleetType': fleetType,
                        'schedule': int(schedule[-1]),
                        'dumbRC': dumbRC,
                        'leavetimeRC': leavetimeRC,
                        'battRC': battRC,
                        'smartRC': smartRC,
                        'costRC': costRC,
                        'dumbCost': dumb_cost,
                        'leavetimeCost': leavetime_cost,
                        'battCost': batt_cost,
                        'smartCost': smart_cost,
                        'costCost': cost_cost
                    }, ignore_index=True)
                    print("   complete")

# save to excel file
performance.to_excel("performance.xlsx")
