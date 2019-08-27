import pandas as pd
import numpy as np
import datetime as dt
import time
from chargingFunctions import *
from stylingFunctions import styleDF
from graphFunctions import *

# CHOOSE PARAMETERS
company = "BritishGas"
outputFolder = "results_test/"
schedule = "shift1"
mpkw = "HighMpkwLowSD"

# READ IN NECESSARY CSV FILES
allShiftsDF = pd.read_csv("csv/schedules/" + schedule + ".csv", sep=";", index_col=None)
drivingDF = pd.read_csv("csv/driving/" + mpkw + ".csv", sep=";", index_col=None)
pricesDF = pd.read_csv("csv/prices.csv", sep=";", index_col=None)
fleetDF = pd.read_csv("csv/fleetData.csv", sep=";", index_col=None)
fleetData = fleetDF.loc[fleetDF.index == 0]

# SELECT RAPID CHARGE INFORMATION
rcDuration = 30     # RAPID CHARGE DURATION (MINUTES)
rcPerc = 20         # WHAT PERCENTAGE TO START RAPID CHARGING (%)
rcRate = 50         # RATE OF RAPID CHARGING (KW/HR)

# CHOOSE START TIME AND RUN TIME
startTime = readTime("2019-01-01 06:00:00")
runTime = 24*5

# dumb_sim, dumbRC = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
#                         fleetData, drivingDF, allShiftsDF, pricesDF, company,
#                         dumbCharge)

# smart_leavetime_sim, smart_leavetimeRC = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
#                         fleetData, drivingDF, allShiftsDF, pricesDF, company,
#                         smartCharge_leavetime)

# smart_batt_sim, smart_battRC = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
#                         fleetData, drivingDF, allShiftsDF, pricesDF, company,
#                         smartCharge_batt)

# smart_sim, smartRC = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
#                         fleetData, drivingDF, allShiftsDF, pricesDF, company,
#                         smartCharge_battOverLeavetime)

cost_sim, costRC = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate, 
                        fleetData, drivingDF, allShiftsDF, pricesDF, company,
                        costSensitiveCharge)

# total_cars = 4
# total_algos = 5

# for car in range(total_cars):
#     result = pd.concat([getCarDF(dumb_sim, 'dumb', car),
#                         getCarDF(smart_leavetime_sim, 'leavetime', car),
#                         getCarDF(smart_batt_sim, 'batt', car),
#                         getCarDF(smart_sim, 'smart', car),
#                         getCarDF(cost_sim, 'cost', car)])
#     compareAlgo(outputFolder, schedule + "_" + company + "_" + mpkw, result, car, total_algos, company)

# compareCars(outputFolder, schedule + "_" + company + "_" + mpkw, dumb_sim, 'dumb', total_cars, company)
# compareCars(outputFolder, schedule + "_" + company + "_" + mpkw, smart_leavetime_sim, 'leavetime', total_cars, company)
# compareCars(outputFolder, schedule + "_" + company + "_" + mpkw, smart_batt_sim, 'batt', total_cars, company)
# compareCars(outputFolder, schedule + "_" + company + "_" + mpkw, smart_sim, 'smart', total_cars, company)
# compareCars(outputFolder, schedule + "_" + company + "_" + mpkw, cost_sim, 'cost', total_cars, company)
