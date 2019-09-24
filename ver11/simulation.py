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
outputFolder = "new_new_results/"
tariff = input("Tariff: ")#"Octopus"
rcNetwork = "Ecotricity"
fleetType = int(input("Fleet Type: "))#0
schedule = input("Shift: ")#"shift1"
hasBreak = 0
caseName = input("Case Name: ")#"case2"
runTime = 24*5                              # (UNITS:  HRS)
startTime = readTime("2019-01-01 06:00:00") # (FORMAT: DATETIME)

# READ IN NECESSARY CSV FILES
allShiftsDF = pd.read_csv("csv/schedules/" + schedule + ".csv", sep=";", index_col=None)
drivingDF = pd.read_csv("csv/driving/constantDriving.csv", sep=";", index_col=None)
pricesDF = pd.read_csv("csv/prices.csv", sep=";", index_col=None)
pricesDF = pricesDF.loc[pricesDF.company == tariff]
breaksDF = pd.read_csv("csv/breaks.csv", sep=";", index_col=None)
breaksDF = breaksDF.loc[breaksDF.id == hasBreak]
fleetDF = pd.read_csv("csv/fleetData.csv", sep=";", index_col=None)
fleetData = fleetDF.loc[fleetDF.index == fleetType]
rcDF = pd.read_csv("csv/rcData.csv", sep=";", index_col=None)
rcData = rcDF.loc[rcDF.company == rcNetwork]
latLongData = pd.read_csv("csv/latLongData.csv", sep=";", index_col=None)

# dumbDF, dumbData = runSimulation(startTime, runTime, rcData, latLongData,
#                         fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, dumbCharge)

# leaveTDF, leaveTData = runSimulation(startTime, runTime, rcData, latLongData,
#                         fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, smartCharge_leavetime)

# smartDF, smartData = runSimulation(startTime, runTime, rcData, latLongData,
#                         fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, smartCharge_battOverLeavetime)

# costDF, costData = runSimulation(startTime, runTime, rcData, latLongData,
#                         fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, costSensitiveCharge)

extraDF, extraData = runSimulation(startTime, runTime, rcData, latLongData,
                        fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, extraCharge)

predictiveDF, predictiveData = runSimulation(startTime, runTime, rcData, latLongData,
                        fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, predictiveCharge)

###############################################################
# SAVE TO EXCEL (ONLY RUN WHEN ALL ALGORITHMS ARE UNCOMMENTED)
# NOTE: CREATE AN OUTPUT FOLDER FIRST
###############################################################
# open writer
writer = pd.ExcelWriter(outputFolder + "fleet" + str(fleetType) + "_" + caseName + ".xlsx")
# write files
# styleDF(dumbDF).to_excel(writer, sheet_name="dumb")
# styleDF(leaveTDF).to_excel(writer, sheet_name="leavetime")
# styleDF(smartDF).to_excel(writer, sheet_name="smart")
# styleDF(costDF).to_excel(writer, sheet_name="cost")
styleDF(extraDF).to_excel(writer, sheet_name="extra")
styleDF(predictiveDF).to_excel(writer, sheet_name="predictive")
# dumbData.to_excel(writer, sheet_name="dumbData")
# leaveTData.to_excel(writer, sheet_name="leavetimeData")
# smartData.to_excel(writer, sheet_name="smartData")
# costData.to_excel(writer, sheet_name="costData")
extraData.to_excel(writer, sheet_name="extraData")
predictiveData.to_excel(writer, sheet_name="predictiveData")
# close writer
writer.save()

# total_cars = 4
# for car in range(total_cars):
#     result = pd.concat([getCarDF(dumbDF, 'dumb', car),
#                         getCarDF(leaveTDF, 'leavetime', car),
#                         getCarDF(battDF, 'batt', car),
#                         getCarDF(smartDF, 'smart', car),
#                         getCarDF(costDF, 'cost', car),
#                         getCarDF(extraDF, 'extra', car),
#                         getCarDF(predictiveDF, 'predictive', car)])
#     compareAlgo(outputFolder + "fleet" + str(fleetType) + "_case2_visuals", result, car, 7, company)
