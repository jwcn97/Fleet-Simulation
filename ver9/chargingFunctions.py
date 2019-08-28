import pandas as pd
import numpy as np
import datetime as dt
import time

# CHOOSE NUMBER OF CHUNKS IN AN HOUR
#   e.g. 3 chunks would divide the hour into 20-min shifts
chunks = 4

from supportFunctions import *

#################################
# INCREASE BATT DURING CHARGE
#################################
def dumbCharge(time, carDataDF, depot, shiftsByCar, 
               availablePower, simulationDF, chargePtDF,
               pricesDF, totalCost):
    # SELECT CARS IN DEPOT THAT ARE NOT FULLY CHARGED
    needChargeDF = carDataDF.loc[(carDataDF['inDepot'] == 1) &
                                 (carDataDF['battkW'] < carDataDF['battSize'])]

    # FOR CARS IN DEPOT:
    for cars in range(len(needChargeDF)):
        car = needChargeDF.index[cars]
        # ALLOCATE AVAILABLE CHARGE PT IF CAR DOESN'T HAVE ONE
        pt, carDataDF, chargePtDF = findChargePt(carDataDF, car, chargePtDF)

    # SELECT CARS IN DEPOT WITH VALID CHARGE PTS
    chargeDF = carDataDF.loc[(carDataDF['inDepot'] == 1) &
                             (carDataDF['battkW'] < carDataDF['battSize']) &
                             (~carDataDF['chargePt'].isna())]

    # IF THERE ARE CARS WITH VALID CHARGE POINTS THAT REQUIRE CHARGING
    if len(chargeDF) > 0:
        # SPLIT CHARGE RATE EQUALLY BETWEEN CARS THAT ARE CHARGING
        if len(chargeDF) <= len(chargePtDF): splitChargeRate = availablePower/len(chargeDF)
        else:                                splitChargeRate = availablePower/len(chargePtDF)

        # CHARGE SELECTED CARS IN DEPOT
        for cars in range(len(chargeDF)):
            car = chargeDF.index[cars]

            # LET CHARGE RATE = SPLIT CHARGE RATE
            chargeRate = splitChargeRate

            # ALLOCATE CHARGE PT IF CAR DOESN'T HAVE ONE
            pt, carDataDF, chargePtDF = findChargePt(carDataDF, car, chargePtDF)

            # IF CAR HAS A VALID CHARGE PT
            if not np.isnan(pt):
                # LIMIT CHARGE RATE TO MAX RATE OF CHARGE PT
                maxRatePt = chargePtDF.loc[pt, 'maxRate']
                if maxRatePt < chargeRate: chargeRate = maxRatePt

            # IF NO CHARGE PTS AVAILABLE, DON'T CHARGE
            else: chargeRate = 0

            # UPDATE CHARGE RATE
            carDataDF.loc[car, 'chargeRate'] = chargeRate

    return carDataDF, chargePtDF, totalCost

#########################################
# INCREASE BATT DURING CHARGE (LEAVETIME)
#########################################
def smartCharge_leavetime(time, carDataDF, depot, shiftsByCar, 
                          availablePower, simulationDF, chargePtDF,
                          pricesDF, totalCost):
    # CREATE A LIST FOR CARS AND THEIR LEAVETIMES (TIME UNTIL CAR LEAVSE DEPOT)
    leaveTList = []

    # # ***** FIND LEAVETIMES AND APPEND TO A LIST *****
    for cars in range(0, len(depot)):
        car = depot[cars]

        # FIND THE START TIME OF NEXT SHIFT
        nextStart = nextShiftStart(car, carDataDF, shiftsByCar)

        # CALCULATE TIME LEFT UNTIL CAR LEAVES AND APPEND TO LIST
        hrsLeft = ((rereadTime(nextStart) - rereadTime(time)).total_seconds())/(60*60)
        leaveTList.append([car, hrsLeft])

    # ***** CONVERT LIST INTO DATAFRAME AND SORT *****
    leaveTimes = pd.DataFrame.from_records(leaveTList, columns=['car','hrsLeft'])
    leaveTimes = leaveTimes.sort_values(by=['hrsLeft'])
    leaveTimes = leaveTimes.reset_index(drop=True)

    # ***** CHARGE CARS IN SORTED ORDER *****
    for row in range(0, len(leaveTimes)):
        # READ IN DATA FOR SELECTED CAR
        car = leaveTimes.loc[row, 'car']
        batt = carDataDF.loc[car, 'battkW']
        battSize = carDataDF.loc[car, 'battSize']
        chargePt = carDataDF.loc[car, 'chargePt']

        # IF CAR BATT IS NOT 100%, CHARGE CAR
        if batt < battSize:
            # ALLOCATE CHARGE PT IF CAR DOESN'T HAVE ONE
            pt, carDataDF, chargePtDF = findChargePt(carDataDF, car, chargePtDF)
            chargeRate = 0

            # IF CAR HAS A VALID CHARGE PT:
            if not np.isnan(pt):
                # READ MAX RATE
                maxRate = chargePtDF.loc[pt, 'maxRate']
                # CALCULATE THE ENERGY LEFT IF CAR WAS CHARGED AT MAX
                energyLeft = availablePower - maxRate

                # IF THERE IS ENOUGH ENERGY FOR MAX RATE, CHARGE CAR AT MAX
                if energyLeft >= 0:
                    chargeRate = maxRate

                # IF THERE ISN'T ENOUGH FOR MAX RATE, CHARGE USING REMAINING POWER
                elif energyLeft < 0 and energyLeft > -maxRate:
                    chargeRate = availablePower

                # IF VEHICLE IS PLUGGED IN BUT NOT ALLOCATED CHARGE
                else:
                    chargeRate = 0

            # UPDATE CHARGE RATE
            carDataDF.loc[car, 'chargeRate'] = chargeRate

            # ADJUST AVAILABLE POWER
            availablePower -= chargeRate

    return carDataDF, chargePtDF, totalCost

######################################
# INCREASE BATT DURING CHARGE (BATT)
######################################
def smartCharge_batt(time, carDataDF, depot, shiftsByCar, 
                     availablePower, simulationDF, chargePtDF,
                     pricesDF, totalCost):
    # CREATE A LIST FOR CARS AND THEIR BATT NEEDED
    battNeededList = []

    # ***** FOR ALL CARS, FIND BATT NEEEDED UNTIL FULLY CHARGED *****
    for cars in range(0, len(depot)):
        carNum = depot[cars]

        # CALCULATE BATTERY NEEDED AND APPEND TO LIST
        battLeft = abs(carDataDF.loc[carNum,'battSize']-carDataDF.loc[carNum,'battkW'])
        battNeededList.append([carNum, battLeft])

    # ***** CONVERT LIST INTO DATAFRAME AND SORT *****
    battNeeded = pd.DataFrame.from_records(battNeededList, columns=['car','battLeft'])
    battNeeded = battNeeded.sort_values(by=['battLeft'], ascending=False)
    battNeeded = battNeeded.reset_index(drop=True)

    # ***** CHARGE CARS IN SORTED ORDER *****
    for row in range(0, len(battNeeded)):
        # READ IN DATA FOR SELECTED CAR
        car = battNeeded.loc[row, 'car']
        batt = carDataDF.loc[car, 'battkW']
        battSize = carDataDF.loc[car, 'battSize']
        chargePt = carDataDF.loc[car, 'chargePt']

        # IF CAR BATT IS NOT 100%, CHARGE CAR
        if batt < battSize:
            # ALLOCATE CHARGE PT IF CAR DOESN'T HAVE ONE
            pt, carDataDF, chargePtDF = findChargePt(carDataDF, car, chargePtDF)
            chargeRate = 0

            # IF CAR HAS A VALID CHARGE PT
            if not np.isnan(pt):
                # READ MAX RATE
                maxRate = chargePtDF.loc[pt, 'maxRate']
                # CALCULATE THE ENERGY LEFT IF CAR WAS CHARGED AT MAX
                energyLeft = availablePower - maxRate

                # IF THERE IS ENOUGH ENERGY FOR MAX RATE, CHARGE CAR AT MAX
                if energyLeft >= 0:
                    chargeRate = maxRate

                # IF THERE ISN'T ENOUGH FOR MAX RATE,  CHARGE USING REMAINING POWER
                elif energyLeft < 0 and energyLeft > -maxRate:
                    chargeRate = availablePower

                # IF VEHICLE IS PLUGGED IN BUT NOT ALLOCATED CHARGE
                else:
                    chargeRate = 0

            # UPDATE CHARGE RATE
            carDataDF.loc[car, 'chargeRate'] = chargeRate

            # ADJUST AVAILABLE POWER
            availablePower -= chargeRate

    return carDataDF, chargePtDF, totalCost

############################################
# INCREASE BATT DURING CHARGE (SUPER SMART)
############################################
# PRIORITY = BATT NEEDED/TIME LEFT IN DEPOT
# CHARGE RATE = (PRIORITY/SUM OF ALL PRIORITIES)*AVAILABLE POWER
def smartCharge_battOverLeavetime(time, carDataDF, depot, shiftsByCar,
                     availablePower, simulationDF, chargePtDF,
                     pricesDF, totalCost):
    # CREATE A LIST FOR CARS AND THEIR LEAVETIMES AND BATT NEEDED
    priorityRows = []

    # ***** FIND LEAVETIMES AND BATT NEEDED AND APPEND TO A LIST *****
    for cars in range(0, len(depot)):
        car = depot[cars]

        # FIND THE START TIME OF NEXT SHIFT
        nextStart = nextShiftStart(car, carDataDF, shiftsByCar)

        # CALCULATE TIME LEFT AND BATT NEEDED
        hrsLeft = ((rereadTime(nextStart) - rereadTime(time)).total_seconds())/(60*60)
        battLeft = carDataDF.loc[car,'battSize']-carDataDF.loc[car,'battkW']

        # LET PRIORITY = BATT LEFT/TIME LEFT, APPEND TO LIST
        priorityRows.append([car, battLeft/hrsLeft, battLeft])

    # CONVERT LIST INTO DATAFRAME AND SORT BY PRIORITY
    leaveTimes = pd.DataFrame.from_records(priorityRows, columns=['car','priority','battLeft'])
    leaveTimes = leaveTimes.sort_values(by=['priority'], ascending=False)
    leaveTimes = leaveTimes.reset_index(drop=True)

    # CALCULATE THE SUM OF PRIORITY VALUES
    prioritySum = sum(leaveTimes.priority)

    # ***** IN SORTED ORDER, CALCULATE PRIORITY RATIO AND CHARGE *****
    # FOR EVERY CAR:
    for row in range(0, len(leaveTimes)):
        # READ IN DATA FOR SELECTED CAR
        car = leaveTimes.loc[row, 'car']
        batt = carDataDF.loc[car, 'battkW']
        battSize = carDataDF.loc[car, 'battSize']
        battLeft = leaveTimes.loc[row, 'battLeft']
        priority = leaveTimes.loc[row, 'priority']

        # IF CAR BATT IS NOT 100%, CHARGE CAR
        if batt < battSize:
            # ALLOCATE CHARGE PT IF CAR DOESN'T HAVE ONE
            pt, carDataDF, chargePtDF = findChargePt(carDataDF, car, chargePtDF)
            chargeRate = 0

            # IF CAR HAS A VALID CHARGE PT
            if not np.isnan(pt):
                # READ MAX RATE
                maxRate = chargePtDF.loc[pt, 'maxRate']

                # CALCULATE CHARGE RATE USING PRIORITY/SUM OF PRIORITIES
                chargeRate = (priority/prioritySum)*availablePower

                # IF CHARGE RATE EXCEEDS MAX RATE:
                if chargeRate > maxRate: chargeRate = maxRate
                # IF CHARGE RATE EXCEEDS CHARGE NEEDED:
                if chargeRate > battLeft*chunks: chargeRate = battLeft*chunks

            # ADJUST REMAINING AVAILABLE POWER AND PRIORITY SUM
            availablePower -= chargeRate
            prioritySum -= priority

            # UPDATE CHARGE RATE
            carDataDF.loc[car, 'chargeRate'] = chargeRate

    return carDataDF, chargePtDF, totalCost

##############################################
# INCREASE BATT DURING CHARGE (COST SENSITIVE)
##############################################
# PRIORITY = BATT NEEDED/TIME LEFT IN DEPOT
# IF CAR WILL CHARGE OVER GREEN ZONE:
    # DELAY CHARGING UNTIL START GREEN ZONE STARTS (PRIORITY = 0)
# CHARGE RATE = (PRIORITY/SUM OF ALL PRIORITIES)*AVAILABLE POWER
def costSensitiveCharge(time, carDataDF, depot, shiftsByCar,
                        availablePower, simulationDF, chargePtDF,
                        pricesDF, totalCost):
    # CREATE A LIST FOR CARS AND THEIR LEAVETIME AND BATT NEEDED
    priorityRows = []

    # DEFINE NEXT GREEN ZONE
    greenStart, greenEnd = nextGreenZone(time, pricesDF)

    # ***** CALCULATE PRIORITY FOR EACH CAR AND APPEND TO A LIST *****
    for cars in range(0, len(depot)):
        carNum = depot[cars]

        # FIND THE START TIME OF NEXT SHIFT
        nextStart = nextShiftStart(carNum, carDataDF, shiftsByCar)

        # CALCULATE TIME LEFT AND BATT NEEDED
        hrsLeft = ((rereadTime(nextStart) - rereadTime(time)).total_seconds())/(60*60)
        battLeft = carDataDF.loc[carNum,'battSize']-carDataDF.loc[carNum,'battkW']
        prior = battLeft/hrsLeft

        # IF GREEN ZONE HASN'T STARTED YET,
        # AND IF CAR WILL BE CHARGING THROUGHOUT WHOLE OF GREEN ZONE:
        if (time < greenStart) and (nextStart >= greenEnd):
            # DELAY CHARGING UNTIL GREEN ZONE
            prior = 0.0

        # LET PRIORITY = BATTLEFT/TIME LEFT, APPEND TO LIST
        priorityRows.append([carNum, prior, battLeft])

    # CONVERT LIST INTO DATAFRAME AND SORT BY PRIORITY
    leaveTimes = pd.DataFrame.from_records(priorityRows, columns=['car','priority','battLeft'])
    leaveTimes = leaveTimes.sort_values(by=['priority'], ascending=False)
    leaveTimes = leaveTimes.reset_index(drop=True)

    # CALCULATE THE SUM OF PRIORITY VALUES
    prioritySum = sum(leaveTimes.priority)

    # ***** IN SORTED ORDER, CALCULATE PRIORITY RATIO AND CHARGE *****
    # FOR EVERY CAR:
    for row in range(0, len(leaveTimes)):
        # READ IN DATA FOR SELECTED CAR
        car = leaveTimes.loc[row, 'car']
        batt = carDataDF.loc[car, 'battkW']
        battSize = carDataDF.loc[car, 'battSize']
        battLeft = leaveTimes.loc[row, 'battLeft']
        priority = leaveTimes.loc[row, 'priority']

        # IF CAR BATT IS NOT 100%, CHARGE CAR
        if batt < battSize:
            # ALLOCATE CHARGE PT IF CAR DOESN'T HAVE ONE
            pt, carDataDF, chargePtDF = findChargePt(carDataDF, car, chargePtDF)
            chargeRate = 0

            # IF CAR HAS A VALID CHARGE PT
            if not np.isnan(pt):
                # READ MAX RATE
                maxRate = chargePtDF.loc[pt, 'maxRate']

                # CALCULATE CHARGE RATE USING PRIORITY/SUM OF PRIORITIES
                if prioritySum == 0.0: chargeRate = 0
                else:                  chargeRate = (priority/prioritySum)*availablePower

                # IF CHARGE RATE EXCEEDS MAX RATE:
                if chargeRate > maxRate: chargeRate = maxRate
                # IF CHARGE RATE EXCEEDS CHARGE NEEDED:
                if chargeRate > battLeft*chunks: chargeRate = battLeft*chunks

            # ADJUST REMAINING CHARGE CAPACITY AND PRIORITY SUM
            availablePower -= chargeRate
            prioritySum -= priority

            # ADJUST TO-CHARGE DF WITH CHARGE RATE
            carDataDF.loc[car, 'chargeRate'] = chargeRate

    return carDataDF, chargePtDF, totalCost

#################################################################################################################################

############################################
# RUN SIMULATION FROM SEPARATE FILE
############################################
def runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate, 
                  fleetData, driveDataDF, allShiftsDF, breaksDF, pricesDF,
                  algo):

    # INITIALISE MAIN DATAFRAMES WITH DATA AT START TIME
    #   Get data from csv inputs
    carData, chargePtData = getLists(fleetData)

    #   Choose column names
    carCols = ["battkW","inDepot","battSize","chargePt","chargeRate","rcChunks","shiftIndex","latestStartShift","latestEndShift"]
    cpCols = ["maxRate","inUse"]
    simCols = ["time","car","chargeDiff","batt","event","costPerCharge","totalCost"]

    #   Initialise dataframes
    carDataDF = pd.DataFrame.from_records(carData, columns=carCols)
    chargePtDF = pd.DataFrame.from_records(chargePtData, columns=cpCols)
    simulationDF = pd.DataFrame(columns=simCols)

    depot = []
    driveDataByCar = {}
    for car in range(0, len(carDataDF)):
        # APPEND CARS INTO DEPOT AT START TIME
        if carDataDF.loc[car,'inDepot']: depot.append(car)
        # CREATE LIBRARY FOR DRIVING DATA
        findData = driveDataDF.loc[driveDataDF['car']==car]
        dataNoIndex = findData.reset_index(drop=True)
        driveDataByCar['%s' % car] = dataNoIndex
    
    # CREATE LIBRARY FOR SHIFTS BY CAR
    shiftsByCar = unpackShifts(carDataDF, allShiftsDF)
    # RETRIEVE AVAILABLE POWER FROM FLEET DATA
    availablePower = getData(fleetData, 'availablePower')

    rcCount = 0             # INITIALISE A COUNTER FOR RAPID CHARGES
    totalCost = 0           # INITIALISE A COUNTER FOR TOTAL COST
    time = startTime        # CHOOSE START TIME

    # RUN SIMULATION FOR ALL OF RUN TIME
    for i in range(0, runTime*chunks):
        # INITIALISE A VARIABLE TO CHECK FOR EVENT CHANGES
        eventChange = False

        # *** RUN FUNCTIONS THAT INCLUDE WILL RECOGNISE CHANGES IN EVENTS ***
        eventChange, carDataDF, depot, chargePtDF = inOutDepot(time, carDataDF, shiftsByCar, depot, chargePtDF, eventChange)
        eventChange = readFullBattCars(time, carDataDF, simulationDF, totalCost, eventChange)
        eventChange = readTariffChanges(time, pricesDF, eventChange)

        # *** RUN FUNCTIONS AFFECTING CARS OUTSIDE THE DEPOT ***
        # DECREASE BATT/RAPID CHARGE CARS OUTSIDE THE DEPOT
        carDataDF, rcCount, simulationDF, totalCost = driving(time, carDataDF, driveDataByCar, breaksDF, 
                                                            rcCount, rcDuration, rcPerc, rcRate, 
                                                            simulationDF, i, totalCost)

        # *** RUN FUNCTIONS AFFECTING CARS IN THE DEPOT ***
        # IF THERE IS AN EVENT and THERE ARE CARS THAT REQUIRE CHARGING
        # RUN CHARGING ALGORITHM
        if (eventChange == True) and (len(depot) > 0):
            carDataDF, chargePtDF, totalCost = algo(time, carDataDF, depot, shiftsByCar, 
                                                    availablePower, simulationDF, chargePtDF, 
                                                    pricesDF, totalCost)

        # CHARGE/READ WAITING CARS IN THE DEPOT
        carDataDF, simulationDF, chargePtDF, totalCost = charge(time, carDataDF, depot, 
                                                simulationDF, chargePtDF, 
                                                pricesDF, totalCost)

        # FORMAT TOTAL COST COLUMN IN SIMULATION DF
        simulationDF = adjustTotalCost(time, simulationDF)

        # INCREMENT TIME OF SIMULATION
        time = incrementTime(time)

    return simulationDF, rcCount, totalCost
