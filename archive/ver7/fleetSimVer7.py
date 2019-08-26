import pandas as pd
import numpy as np
import datetime as dt
import time
from simFunctionsVer7 import *
from simVisualsVer7 import *

# READ IN NECESSARY CSV FILES
outputFolder = "results_test/"
schedule = "shift3"
price = "BG"
mpkw = "LowMpkwLowSD"
allShiftsDF = pd.read_csv("csv/schedules/" + schedule + ".csv", sep=";", index_col=None)
pricesDF = pd.read_csv("csv/prices/prices" + price + ".csv", sep=";", index_col=None)
drivingDF = pd.read_csv("csv/driving/drivingData" + mpkw + ".csv", sep=";", index_col=None)
fleetData = pd.read_csv("csv/fleetData.csv", sep=";", index_col=None)
fleetData = selectCase(fleetData, {'mediumCars':4,'fastChargePts':2})

# CHOOSE START TIME AND RUN TIME
startTime = readTime("2019-01-01 06:00:00")
runTime = 24*5

showDF, dumb_sim, dumbRC = runSimulation(startTime, runTime, fleetData, 
                        drivingDF, allShiftsDF, pricesDF, dumbCharge)
showDF.to_excel('test.xlsx')

showDF, smart_leavetime_sim, smart_leavetimeRC = runSimulation(startTime, runTime, fleetData, 
                        drivingDF, allShiftsDF, pricesDF, smartCharge_leavetime)
showDF.to_excel('test2.xlsx')

showDF, smart_batt_sim, smart_battRC = runSimulation(startTime, runTime, fleetData, 
                        drivingDF, allShiftsDF, pricesDF, smartCharge_batt)
showDF.to_excel('test3.xlsx')

showDF, smart_sim, smartRC = runSimulation(startTime, runTime, fleetData, 
                        drivingDF, allShiftsDF, pricesDF, superSmartCharge)
showDF.to_excel('test4.xlsx')

showDF, cost_sim, costRC = runSimulation(startTime, runTime, fleetData, 
                        drivingDF, allShiftsDF, pricesDF, costSensitiveCharge)
showDF.to_excel('test5.xlsx')

# total_cars = 4
# total_algos = 5

# for car in range(total_cars):
#     result = pd.concat([getCarDF(dumb_sim, 'dumb', car), 
#                         getCarDF(smart_leavetime_sim, 'leavetime', car), 
#                         getCarDF(smart_batt_sim, 'batt', car), 
#                         getCarDF(smart_sim, 'smart', car),
#                         getCarDF(cost_sim, 'cost', car)])
#     compareAlgo(outputFolder, schedule + "_" + price + "_" + mpkw, result, car, total_algos)

# compareCars(outputFolder, schedule + "_" + price + "_" + mpkw, dumb_sim, 'dumb', total_cars)
# compareCars(outputFolder, schedule + "_" + price + "_" + mpkw, smart_leavetime_sim, 'leavetime', total_cars)
# compareCars(outputFolder, schedule + "_" + price + "_" + mpkw, smart_batt_sim, 'batt', total_cars)
# compareCars(outputFolder, schedule + "_" + price + "_" + mpkw, smart_sim, 'smart', total_cars)
# compareCars(outputFolder, schedule + "_" + price + "_" + mpkw, cost_sim, 'cost', total_cars)