import pandas as pd
import numpy as np
import datetime as dt
import time
from simFunctionsVer9 import *

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

pricesDF = pd.read_csv("csv/prices.csv", sep=";", index_col=None)
fleetDF = pd.read_csv("csv/fleetData.csv", sep=";", index_col=None)

def costDifference(df, batt_size):
    original = df.totalCost.iloc[-1]
    extra = df.iloc[-4:].batt.apply(lambda x: batt_size-x).sum()*0.1788
    return original + extra

import glob
for priceType in range(0,2):
    for drives in glob.glob('csv/driving/*.csv'):
        for fleetType in range(0,6):
            for schedules in glob.glob('csv/schedules/*.csv'):
                company = pricesDF.loc[priceType, 'company']
                mpkw = drives.split("\\")[1][0:-4]
                schedule = schedules.split("\\")[1][:-4]
                print("\n" + schedule + "_" + company + "_" + mpkw + "_fleetType" + str(fleetType))
                print("----------------------------------------")
                
                allShiftsDF = pd.read_csv("csv/schedules/" + schedule + ".csv", sep=";", index_col=None)
                drivingDF = pd.read_csv("csv/driving/" + mpkw + ".csv", sep=";", index_col=None)
                fleetData = fleetDF.loc[fleetDF.index == fleetType]
                print("   finish importing data")

                dumb_sim, dumbRC = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                                    fleetData, drivingDF, allShiftsDF, pricesDF, company,
                                    dumbCharge)
                print("   finish dumb charging")

                smart_leavetime_sim, smart_leavetimeRC = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                                    fleetData, drivingDF, allShiftsDF, pricesDF, company,
                                    smartCharge_leavetime)
                print("   finish leavetime charging")

                smart_batt_sim, smart_battRC = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                                    fleetData, drivingDF, allShiftsDF, pricesDF, company,
                                    smartCharge_batt)
                print("   finish battleft charging")

                smart_sim, smartRC = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                                    fleetData, drivingDF, allShiftsDF, pricesDF, company,
                                    smartCharge_battOverLeavetime)
                print("   finish battleft/leavetime charging")

                cost_sim, costRC = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                                    fleetData, drivingDF, allShiftsDF, pricesDF, company,
                                    costSensitiveCharge)
                print("   finish cost-sensitive charging")

                # get the battery size and relevent costs
                batt_size = dumb_sim.iloc[0].batt
                dumb_cost = costDifference(dumb_sim, batt_size)
                leavetime_cost = costDifference(smart_leavetime_sim, batt_size)
                batt_cost = costDifference(smart_batt_sim, batt_size)
                smart_cost = costDifference(smart_sim, batt_size)
                cost_cost = costDifference(cost_sim, batt_size)

                performance = performance.append({
                    'price': company,
                    'mpkw': mpkw,
                    'fleetType': fleetType,
                    'schedule': int(schedule[-1]),
                    'dumbRC': dumbRC,
                    'leavetimeRC': smart_leavetimeRC,
                    'battRC': smart_battRC,
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
performance.to_excel("performance2.xlsx")
