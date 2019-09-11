import pandas as pd
import numpy as np
import datetime as dt
import time

from supportFunctions import *
from chargingFunctions import *
from mainFunction import runSimulation
from stylingFunctions import styleDF
from graphFunctions import *

# SELECT PARAMETERS
outputFolder = "results/"
company = "BritishGas"
schedule = "shift3"
hasBreak = 0
fleetType = 12
rcType = 0
runTime = 24*5                              # (UNITS:  HRS)
startTime = readTime("2019-01-01 06:00:00") # (FORMAT: DATETIME)

# READ IN NECESSARY CSV FILES
allShiftsDF = pd.read_csv("csv/schedules/" + schedule + ".csv", sep=";", index_col=None)
drivingDF = pd.read_csv("csv/driving/constantDriving.csv", sep=";", index_col=None)
pricesDF = pd.read_csv("csv/prices.csv", sep=";", index_col=None)
pricesDF = pricesDF.loc[pricesDF.company == company]
breaksDF = pd.read_csv("csv/breaks.csv", sep=";", index_col=None)
breaksDF = breaksDF.loc[breaksDF.id == hasBreak]
fleetDF = pd.read_csv("csv/fleetData.csv", sep=";", index_col=None)
fleetData = fleetDF.loc[fleetDF.index == fleetType]
rcDF = pd.read_csv("csv/rcData.csv", sep=";", index_col=None)
rcData = rcDF.loc[rcDF.index == rcType]

# dumbDF, dumbRC, dumbCost = runSimulation(startTime, runTime, rcData,
#                         fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, dumbCharge)

# leaveTDF, leaveTRC, leaveTCost = runSimulation(startTime, runTime, rcData,
#                         fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, smartCharge_leavetime)

# battDF, battRC, battCost = runSimulation(startTime, runTime, rcData,
#                         fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, smartCharge_batt)

# smartDF, smartRC, smartCost = runSimulation(startTime, runTime, rcData,
#                         fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, smartCharge_battOverLeavetime)

# costDF, costRC, costCost = runSimulation(startTime, runTime, rcData,
#                         fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, costSensitiveCharge)

extraDF, extraRC, extraCost = runSimulation(startTime, runTime, rcData,
                        fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, extraCharge)
styleDF(extraDF).to_excel('results/fleet' + str(fleetType) + '_case5_gold.xlsx')

# resultDF = pd.DataFrame(columns=['dumbRC','leaveTRC','battRC','smartRC','costRC','extraRC',
#                                 'dumbCost','leaveTCost','battCost','smartCost','costCost','extraCost'])

# resultDF = resultDF.append({
#     'dumbRC':dumbRC,
#     'leaveTRC':leaveTRC,
#     'battRC':battRC,
#     'smartRC':smartRC,
#     'costRC':costRC,
#     'extraRC':extraRC,
#     'dumbCost':dumbCost,
#     'leaveTCost':leaveTCost,
#     'battCost':battCost,
#     'smartCost':smartCost,
#     'costCost':costCost,
#     'extraCost':extraCost
# }, ignore_index=True)

# ###############################################################
# # SAVE TO EXCEL (ONLY RUN WHEN ALL ALGORITHMS ARE UNCOMMENTED)
# # NOTE: CREATE AN OUTPUT FOLDER FIRST
# ###############################################################
# # open writer
# writer = pd.ExcelWriter(outputFolder + "fleet" + str(fleetType) + "_case5.xlsx")
# # write files
# styleDF(dumbDF).to_excel(writer, sheet_name="dumb")
# styleDF(leaveTDF).to_excel(writer, sheet_name="leavetime")
# styleDF(battDF).to_excel(writer, sheet_name="batt")
# styleDF(smartDF).to_excel(writer, sheet_name="smart")
# styleDF(costDF).to_excel(writer, sheet_name="cost")
# styleDF(extraDF).to_excel(writer, sheet_name="extra")
# resultDF.to_excel(writer, sheet_name="results")
# # close writer
# writer.save()

# total_cars = 4
# total_algos = 6

# for car in range(total_cars):
#     result = pd.concat([getCarDF(dumbDF, 'dumb', car),
#                         getCarDF(leaveTDF, 'leavetime', car),
#                         getCarDF(battDF, 'batt', car),
#                         getCarDF(smartDF, 'smart', car),
#                         getCarDF(costDF, 'cost', car),
#                         getCarDF(extraDF, 'extra', car)])
#     compareAlgo(outputFolder+schedule, result, car, total_algos, company)

# compareCars(outputFolder+schedule, dumbDF, 'dumb', total_cars, company)
# compareCars(outputFolder+schedule, leaveTDF, 'leavetime', total_cars, company)
# compareCars(outputFolder+schedule, battDF, 'batt', total_cars, company)
# compareCars(outputFolder+schedule, smartDF, 'smart', total_cars, company)
# compareCars(outputFolder+schedule, costDF, 'cost', total_cars, company)
# compareCars(outputFolder+schedule, extraDF, 'extra', total_cars, company)
