import numpy as np
import math
import geopy
from geopy.distance import VincentyDistance
import time
from chunks import chunks
from supportFunctions import *


##################################################
# FUNCTIONS WHICH SUPPORT DRIVING
##################################################

# CHECK WHETHER IT IS A NON CHARGING BREAK
def breakTime(time, breaksDF):
    breakStart = getData(breaksDF, 'startBreak')
    breakEnd = getData(breaksDF, 'endBreak')

    if not breakStart == "None":
        if readTime(breakStart) <= time.time() < readTime(breakEnd):
            return True

# DECREASE BATTERY WHILE DRIVING NORMALLY
def decreaseBatt(car, carDataDF, driveDataByCar, ind, nonChargingBreak):
    # READ PARAMETERS
    batt = carDataDF.loc[car, 'battkW']
    battSize = carDataDF.loc[car, 'battSize']
    drivingValues = driveDataByCar['0'].shape[0]

    # GET VALUE FOR MILEAGE AND MPKW
    if nonChargingBreak: mileage = 0
    else:                mileage = driveDataByCar[str(car % 4)].loc[ind % drivingValues, 'mileage']
    mpkw = driveDataByCar[str(car % 4)].loc[ind % drivingValues, 'mpkw']

    # CALCULATE RATE OF BATT DECREASE
    kwphr = mileage/mpkw

    # SET INPUTS FOR SIMULATION DF
    chargeDiff = round(-kwphr/chunks, 2)
    costPerCharge = 0

    # UPDATE BATTERY AND TOTAL DISTANCE OF CAR (IN MILES)
    carDataDF.loc[car,'battkW'] = batt - (kwphr/chunks)
    carDataDF.loc[car, 'totalDistance'] += (mileage/chunks)

    return carDataDF, kwphr, chargeDiff, costPerCharge

# RAPID CHARGE VEHICLE
def rapidCharge(car, carDataDF, rcRate, rcPrice, totalCost):
    # READ BATTERY and BATTERY SIZE
    batt = carDataDF.loc[car, 'battkW']
    battSize = carDataDF.loc[car, 'battSize']

    # CALCULATE BATTERY INCREASE
    if batt + rcRate/chunks > battSize: RCbattIncrease = battSize - batt
    else:                               RCbattIncrease = rcRate/chunks

    # UPDATE RAPID CHARGE COUNT AND TOTAL COST
    rcCost = rcPrice * RCbattIncrease
    totalCost += rcCost

    # UPDATE BATTERY AND TOTAL COST
    carDataDF.loc[car,'battkW'] = batt + RCbattIncrease
    carDataDF.loc[car,'totalCost'] += rcCost

    # SET INPUTS FOR SIMULATION DF
    chargeDiff = round(RCbattIncrease, 2)
    costPerCharge = round(rcCost, 2)

    return carDataDF, totalCost, chargeDiff, costPerCharge

# PREDICT BATTERY NEEDED TILL VEHICLE ENTERS DEPOT
def predictBattNeeded(car, hrsLeft, buffer, driveDataByCar, ind):
    # READ TOTAL NUMBER OF DRIVING VALUES
    drivingValues = driveDataByCar['0'].shape[0]
    # SET BUFFER FOR BATTERY NEEDED
    battNeeded = buffer
    # FIND TIME SLOTS REMAINING FOR DRIVE
    chunksLeft = int(hrsLeft * chunks)

    for i in range(chunksLeft):
        # GET VALUE FOR MILEAGE AND MPKW
        mileage = driveDataByCar[str(car % 4)].loc[(i + ind) % drivingValues, 'mileage']
        mpkw = driveDataByCar[str(car % 4)].loc[(i + ind) % drivingValues, 'mpkw']
        # CALCULATE RATE OF BATT DECREASE
        kwphr = mileage/mpkw
        # INCREMENT BATTERY NEEDED
        battNeeded += kwphr/chunks

    return battNeeded


#########################################################################
# LOOK AT CARS OUTSIDE THE DEPOT
#   FOR CARS THAT NEED RAPID CHARGING: RAPID CHARGE
#   FOR CARS THAT DON'T NEED RAPID CHARGING: DECREASE BATT
#########################################################################
def driving(time, carDataDF, driveDataByCar, breaksDF, rcData, sim, ind):
    # EXTRACT RAPID CHARGE DATA
    rcPrice = getData(rcData, 'rcPrice')        # PRICE PER KW OF RAPID CHARGE (£ PER KW)
    rcPerc = getData(rcData, 'rcPerc')          # WHAT PERCENTAGE TO START RAPID CHARGING (%)
    rcRate = getData(rcData, 'rcRate')          # RATE OF RAPID CHARGING (KW/HR)

    # FIND CARS OUTSIDE OF DEPOT
    drivingCarsDF = carDataDF.loc[carDataDF["inDepot"]==0]

    # GET OTHER PARAMETERS
    drivingValues = driveDataByCar['0'].shape[0]
    nonChargingBreak = breakTime(time, breaksDF)
    totalCost = carDataDF['totalCost'].sum()

    for rows in range(len(drivingCarsDF)):
        car = drivingCarsDF.index[rows]

        # READ VEHICLE PARAMETERS
        batt = carDataDF.loc[car, 'battkW']
        battSize = carDataDF.loc[car, 'battSize']
        rcChunks = carDataDF.loc[car,'rcChunks']

        # FIND BATTERY NEEDED BY VEHICLE
        hrsLeft = (readTime(carDataDF.loc[car, 'latestEndShift']) - time).total_seconds()/3600
        buffer = battSize * 10/100
        battNeeded = predictBattNeeded(car, hrsLeft, buffer, driveDataByCar, ind)

        # IF CAR HAS BEEN RAPID CHARGING AND STILL NEEDS RAPID CHARGING, RAPID CHARGE
        if (rcChunks > 0) and (batt < battNeeded < battSize):
            # RAPID CHARGE VEHICLE
            carDataDF, totalCost, chargeDiff, costPerCharge = rapidCharge(car, carDataDF, rcRate, rcPrice, totalCost)
            # UPDATE RC PARAMETERS
            carDataDF.loc[car,'rcChunks'] += 1
            # LABEL EVENT
            event = 'RC'

        # IF CAR HASN'T BEEN RAPID CHARGING BUT NEEDS RAPID CHARGING, RAPID CHARGE
        elif (batt < battSize*rcPerc/100) and (batt < battNeeded < battSize):
            # RAPID CHARGE VEHICLE
            carDataDF, totalCost, chargeDiff, costPerCharge = rapidCharge(car, carDataDF, rcRate, rcPrice, totalCost)
            # UPDATE RC PARAMETERS
            if rcChunks == 0: carDataDF.loc[car,'rcCount'] += 1
            carDataDF.loc[car,'rcChunks'] += 1
            # LABEL EVENT
            event = 'RC'

        # IF CAR DOESN'T NEED RAPID CHARGING, DECREASE BATT (DRIVE):
        else:
            # DECREASE BATTERY OF VEHICLE
            carDataDF, kwphr, chargeDiff, costPerCharge = decreaseBatt(car, carDataDF, driveDataByCar, ind, nonChargingBreak)
            # UPDATE RAPID CHARGE CHUNKS
            carDataDF.loc[car,'rcChunks'] = 0
            # UPDATE EVENT
            event = 'wait' if kwphr == 0.0 else 'drive'

        # UPDATE SIMULATION ACCORDINGLY
        # time, car, chargeDiff, batt, event, costPerCharge, totalCost
        sim += [[time, car, chargeDiff, round(batt, 2), event, costPerCharge, round(totalCost, 2)]]

    return carDataDF, sim