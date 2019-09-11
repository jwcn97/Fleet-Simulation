import pandas as pd
import numpy as np
import datetime as dt
import time
from simFunctionsVer8 import *
from simVisualsVer8 import *

# READ IN NECESSARY CSV FILES
outputFolder = "results_test/"
schedule = "shift1"
mpkw = "HighMpkwLowSD"
allShiftsDF = pd.read_csv("csv/schedules/" + schedule + ".csv", sep=";", index_col=None)
drivingDF = pd.read_csv("csv/driving/" + mpkw + ".csv", sep=";", index_col=None)
pricesDF = pd.read_csv("csv/prices.csv", sep=";", index_col=None)
fleetDF = pd.read_csv("csv/fleetData.csv", sep=";", index_col=None)
fleetData = selectCase(fleetDF, {'smallCars':4,'fastChargePts':4})

# SELECT PRICE OPTION
company = "OriginalTest"

# SELECT RAPID CHARGE INFORMATION
RCduration = 30     # RAPID CHARGE DURATION (MINUTES)
RCperc = 20         # WHAT PERCENTAGE TO START RAPID CHARGING (%)

# CHOOSE START TIME AND RUN TIME
startTime = readTime("2019-01-01 06:00:00")
runTime = 24*5

# showDF, dumb_sim, dumbRC = runSimulation(startTime, runTime, RCduration, RCperc,
#                         fleetData, drivingDF, allShiftsDF, pricesDF, company,
#                         dumbCharge)

# showDF, smart_leavetime_sim, smart_leavetimeRC = runSimulation(startTime, runTime, RCduration, RCperc,
#                         fleetData, drivingDF, allShiftsDF, pricesDF, company,
#                         smartCharge_leavetime)

# showDF, smart_batt_sim, smart_battRC = runSimulation(startTime, runTime, RCduration, RCperc,
#                         fleetData, drivingDF, allShiftsDF, pricesDF, company,
#                         smartCharge_batt)

# showDF, smart_sim, smartRC = runSimulation(startTime, runTime, RCduration, RCperc,
#                         fleetData, drivingDF, allShiftsDF, pricesDF, company,
#                         smartCharge_battOverLeavetime)

# showDF, cost_sim, costRC = runSimulation(startTime, runTime, RCduration, RCperc,
#                         fleetData, drivingDF, allShiftsDF, pricesDF, company,
#                         costSensitiveCharge)

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
