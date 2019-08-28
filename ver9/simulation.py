import pandas as pd
import numpy as np
import datetime as dt
import time
from chargingFunctions import *
from stylingFunctions import styleDF
from graphFunctions import *

# SELECT RAPID CHARGE INFORMATION
rcDuration = 30     # RAPID CHARGE DURATION (MINUTES)
rcPerc = 20         # WHAT PERCENTAGE TO START RAPID CHARGING (%)
rcRate = 50         # RATE OF RAPID CHARGING (KW/HR)

# CHOOSE START TIME AND RUN TIME
startTime = readTime("2019-01-01 06:00:00")
runTime = 24*5

# CHOOSE PARAMETERS
outputFolder = "results_test/"
company = "BritishGas"
schedule = "shift2"
mpkw = "HighMpkwLowSD"
hasBreak = 0
fleetType = 0

# READ IN NECESSARY CSV FILES
allShiftsDF = pd.read_csv("csv/schedules/" + schedule + ".csv", sep=";", index_col=None)
drivingDF = pd.read_csv("csv/driving/" + mpkw + ".csv", sep=";", index_col=None)
pricesDF = pd.read_csv("csv/prices.csv", sep=";", index_col=None)
pricesDF = pricesDF.loc[pricesDF.company == company]
breaksDF = pd.read_csv("csv/breaks.csv", sep=";", index_col=None)
breaksDF = breaksDF.loc[breaksDF.id == hasBreak]
fleetDF = pd.read_csv("csv/fleetData.csv", sep=";", index_col=None)
fleetData = fleetDF.loc[fleetDF.index == fleetType]

time_ = dt.datetime.now()
dumbDF, dumbRC, dumbCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                        fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF,
                        dumbCharge)

leavetimeDF, leavetimeRC, leavetimeCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                        fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF,
                        smartCharge_leavetime)

battDF, battRC, battCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                        fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF,
                        smartCharge_batt)

smartDF, smartRC, smartCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
                        fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF,
                        smartCharge_battOverLeavetime)

costDF, costRC, costCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate, 
                        fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF,
                        costSensitiveCharge)
print((dt.datetime.now()-time_).total_seconds())

###############################################################
# SAVE TO EXCEL (ONLY RUN WHEN ALL ALGORITHMS ARE UNCOMMENTED)
# NOTE: CREATE AN OUTPUT FOLDER FIRST
###############################################################
# open writer
writer = pd.ExcelWriter(outputFolder + "fleet" + str(fleetType) + "_case3.xlsx")
# write files
styleDF(dumbDF).to_excel(
    writer, sheet_name="dumb")
styleDF(leavetimeDF).to_excel(
    writer, sheet_name="leavetime")
styleDF(battDF).to_excel(
    writer, sheet_name="batt")
styleDF(smartDF).to_excel(
    writer, sheet_name="smart")
styleDF(costDF).to_excel(
    writer, sheet_name="cost")
# close writer
writer.save()

# total_cars = 4
# total_algos = 5

# for car in range(total_cars):
#     result = pd.concat([getCarDF(dumbDF, 'dumb', car),
#                         getCarDF(leavetimeDF, 'leavetime', car),
#                         getCarDF(battDF, 'batt', car),
#                         getCarDF(smartDF, 'smart', car),
#                         getCarDF(costDF, 'cost', car)])
#     compareAlgo(outputFolder, schedule + "_" + company + "_" + mpkw, result, car, total_algos, company)

# compareCars(outputFolder, schedule + "_" + company + "_" + mpkw, dumbDF, 'dumb', total_cars, company)
# compareCars(outputFolder, schedule + "_" + company + "_" + mpkw, leavetimeDF, 'leavetime', total_cars, company)
# compareCars(outputFolder, schedule + "_" + company + "_" + mpkw, battDF, 'batt', total_cars, company)
# compareCars(outputFolder, schedule + "_" + company + "_" + mpkw, smartDF, 'smart', total_cars, company)
# compareCars(outputFolder, schedule + "_" + company + "_" + mpkw, costDF, 'cost', total_cars, company)
