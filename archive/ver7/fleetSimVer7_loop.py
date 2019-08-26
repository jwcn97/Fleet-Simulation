import pandas as pd
import numpy as np
import datetime as dt
import time
from simFunctionsVer7 import *

# CHOOSE START TIME AND RUN TIME
startTime = readTime("2019-01-01 06:00:00")
runTime = 24*5
# initialise data frame
performance = pd.DataFrame(columns=['mpkw','fleetType','schedule',
                                    'dumbRC','leavetimeRC','battRC','smartRC','costRC',
                                    'dumbCost','leavetimeCost','battCost','smartCost','costCost'])

import glob
for prices in glob.glob('csv/prices/*.csv'):
    for drives in glob.glob('csv/driving/*.csv'):
        for fleetType in range(0,6):
            for schedules in glob.glob('csv/schedules/*.csv'):
                schedule = schedules.split("\\")[1][:-4]
                price = prices.split("\\")[1][6:-4]
                mpkw = drives.split("\\")[1][11:-4]
                print("\n" + schedule + "_" + price + "_" + mpkw + "_fleetType" + str(fleetType))
                print("----------------------------------------")
                
                allShiftsDF = pd.read_csv("csv/schedules/" + schedule + ".csv", sep=";", index_col=None)
                pricesDF = pd.read_csv("csv/prices/prices" + price + ".csv", sep=";", index_col=None)
                drivingDF = pd.read_csv("csv/driving/drivingData" + mpkw + ".csv", sep=";", index_col=None)
                fleetData = pd.read_csv("csv/fleetData.csv", sep=";", index_col=None)
                fleetData = fleetData.loc[fleetData.index == fleetType]
                print("   finish importing data")

                showDF, dumb_sim, dumbRC = runSimulation(
                    startTime, runTime, fleetData, 
                    drivingDF, allShiftsDF, pricesDF, dumbCharge)
                print("   finish dumb charging")

                showDF, smart_leavetime_sim, smart_leavetimeRC = runSimulation(
                    startTime, runTime, fleetData, 
                    drivingDF, allShiftsDF, pricesDF, smartCharge_leavetime)
                print("   finish leavetime charging")

                showDF, smart_batt_sim, smart_battRC = runSimulation(
                    startTime, runTime, fleetData, 
                    drivingDF, allShiftsDF, pricesDF, smartCharge_batt)
                print("   finish battleft charging")

                showDF, smart_sim, smartRC = runSimulation(
                    startTime, runTime, fleetData, 
                    drivingDF, allShiftsDF, pricesDF, superSmartCharge)
                print("   finish priority charging")

                showDF, cost_sim, costRC = runSimulation(
                    startTime, runTime, fleetData, 
                    drivingDF, allShiftsDF, pricesDF, costSensitiveCharge)
                print("   finish cost charging")

                performance = performance.append({
                    'mpkw': mpkw,
                    'fleetType': fleetType,
                    'schedule': int(schedule[-1]),
                    'dumbRC': dumbRC,
                    'leavetimeRC': smart_leavetimeRC,
                    'battRC': smart_battRC,
                    'smartRC': smartRC,
                    'costRC': costRC,
                    'dumbCost': dumb_sim.totalCost.iloc[-1],
                    'leavetimeCost': smart_leavetime_sim.totalCost.iloc[-1],
                    'battCost': smart_batt_sim.totalCost.iloc[-1],
                    'smartCost': smart_sim.totalCost.iloc[-1],
                    'costCost': cost_sim.totalCost.iloc[-1]
                }, ignore_index=True)
                print("   complete")

# save to excel file
performance.to_excel("performance.xlsx")