import pandas as pd
import numpy as np
import datetime as dt
import time

# CHOOSE NUMBER OF CHUNKS IN AN HOUR
#   e.g. 3 chunks would divide the hour into 20-min shifts
chunks = 2

from supportFunctions import *

#################################
# INCREASE BATT DURING CHARGE
#################################
def dumbCharge(carDataDF, depot, shiftsByCar, time,
               availablePower, simulationDF, chargePtDF, toChargeDF,
               pricesDF, company, totalCost):
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

            # UPDATE TO-CHARGE DF
            toChargeDF.loc[car, 'chargeRate'] = chargeRate

        # FOR CARS IN DEPOT THAT ARE FULLY CHARGED

    return carDataDF, chargePtDF, toChargeDF, totalCost

#########################################
# INCREASE BATT DURING CHARGE (LEAVETIME)
#########################################
def smartCharge_leavetime(carDataDF, depot, shiftsByCar, time,
                          availablePower, simulationDF, chargePtDF, toChargeDF,
                          pricesDF, company, totalCost):
    # IF THERE ARE CARS IN THE DEPOT
    if len(depot) > 0:

        # CREATE A LIST FOR CARS AND THEIR LEAVETIMES (TIME UNTIL CAR LEAVSE DEPOT)
        leaveTList = []

        # # ***** FIND LEAVETIMES AND APPEND TO A LIST *****
        for cars in range(0, len(depot)):
            car = depot[cars]

            # READ INDEX OF LATEST SHIFT AND INDEX OF THE LAST SHIFT
            shiftIndex = carDataDF.loc[car, 'shiftIndex']
            lastShiftIndex = len(shiftsByCar[str(car)])
            # IF NEXT SHIFT EXISTS, TAKE START TIME OF NEXT SHIFT
            if (shiftIndex + 1) < lastShiftIndex:
                nextStart = shiftsByCar[str(car)].loc[shiftIndex+1, 'startShift']

            # IF SHIFT INDEX GOES BEYOND LAST SHIFT, TAKE ARBITRARY LEAVETIME
            else:
                lastStart = shiftsByCar[str(car)].loc[lastShiftIndex-1, 'startShift']
                lastDay = readTime(lastStart).date() + dt.timedelta(days=1)
                nextStart = readTime(str(lastDay) + " 23:59:59")

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

                # ADJUST TO-CHARGE DF WITH CHARGE RATE
                toChargeDF.loc[car, 'chargeRate'] = chargeRate

                # ADJUST AVAILABLE POWER
                availablePower -= chargeRate

    return carDataDF, chargePtDF, toChargeDF, totalCost

######################################
# INCREASE BATT DURING CHARGE (BATT)
######################################
def smartCharge_batt(carDataDF, depot, shiftsByCar, time,
                     availablePower, simulationDF, chargePtDF, toChargeDF,
                     pricesDF, company, totalCost):
    # IF THERE ARE CARS IN THE DEPOT
    if len(depot) >= 1:

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

                # ADJUST TO-CHARGE DF WITH CHARGE RATE
                toChargeDF.loc[car, 'chargeRate'] = chargeRate

                # ADJUST AVAILABLE POWER
                availablePower -= chargeRate

    return carDataDF, chargePtDF, toChargeDF, totalCost

############################################
# INCREASE BATT DURING CHARGE (SUPER SMART)
############################################
# PRIORITY = BATT NEEDED/TIME LEFT IN DEPOT
# CHARGE RATE = (PRIORITY/SUM OF ALL PRIORITIES)*AVAILABLE POWER
def smartCharge_battOverLeavetime(carDataDF, depot, shiftsByCar, time,
                     availablePower, simulationDF, chargePtDF, toChargeDF,
                     pricesDF, company, totalCost):
    # IF THERE ARE CARS IN THE DEPOT
    if len(depot) >= 1:

        # CREATE A LIST FOR CARS AND THEIR LEAVETIMES AND BATT NEEDED
        priorityRows = []

        # ***** FIND LEAVETIMES AND BATT NEEDED AND APPEND TO A LIST *****
        for cars in range(0, len(depot)):
            car = depot[cars]

            # READ INDEX OF LATEST SHIFT AND INDEX OF THE LAST SHIFT
            shiftIndex = carDataDF.loc[car, 'shiftIndex']
            lastShiftIndex = len(shiftsByCar[str(car)])
            # IF NEXT SHIFT EXISTS, TAKE START TIME OF NEXT SHIFT
            if (shiftIndex + 1) < lastShiftIndex:
                nextStart = shiftsByCar[str(car)].loc[shiftIndex+1, 'startShift']

            # IF SHIFT INDEX GOES BEYOND LAST SHIFT, TAKE ARBITRARY LEAVETIME
            else:
                lastStart = shiftsByCar[str(car)].loc[lastShiftIndex-1, 'startShift']
                lastDay = readTime(lastStart).date() + dt.timedelta(days=1)
                nextStart = readTime(str(lastDay) + " 23:59:59")

            # CALCULATE TIME LEFT AND BATT NEEDED
            hrsLeft = ((rereadTime(nextStart) - rereadTime(time)).total_seconds())/(60*60)
            battLeft = carDataDF.loc[car,'battSize']-carDataDF.loc[car,'battkW']

            # LET PRIORITY = BATT LEFT/TIME LEFT, APPEND TO LIST
            priorityRows.append([car, battLeft/hrsLeft, battLeft])

        # ***** CONVERT LIST INTO DATAFRAME AND SORT BY PRIORITY *****
        leaveTimes = pd.DataFrame.from_records(priorityRows, columns=['car','priority','battLeft'])
        leaveTimes = leaveTimes.sort_values(by=['priority'], ascending=False)
        leaveTimes = leaveTimes.reset_index(drop=True)

        # ***** IN SORTED ORDER, CALCULATE PRIORITY RATIO AND CHARGE *****
        # CALCULATE THE SUM OF PRIORITY VALUES
        prioritySum = sum(leaveTimes.priority)

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

                # ADJUST TO-CHARGE DF WITH CHARGE RATE
                toChargeDF.loc[car, 'chargeRate'] = chargeRate

    return carDataDF, chargePtDF, toChargeDF, totalCost

##############################################
# INCREASE BATT DURING CHARGE (COST SENSITIVE)
##############################################
# PRIORITY = BATT NEEDED/TIME LEFT IN DEPOT
# IF CAR WILL CHARGE OVER GREEN ZONE:
    # DELAY CHARGING UNTIL START GREEN ZONE STARTS (PRIORITY = 0)
# CHARGE RATE = (PRIORITY/SUM OF ALL PRIORITIES)*AVAILABLE POWER
def costSensitiveCharge(carDataDF, depot, shiftsByCar, time,
                        availablePower, simulationDF, chargePtDF, toChargeDF,
                        pricesDF, company, totalCost):
    # IF THERE ARE CARS IN THE DEPOT
    if len(depot) >= 1:

        # CREATE A LIST FOR CARS AND THEIR LEAVETIME AND BATT NEEDED
        priorityRows = []

        # ***** CALCULATE PRIORITY FOR EACH CAR AND APPEND TO A LIST *****
        for cars in range(0, len(depot)):
            carNum = depot[cars]

            # READ INDEX OF LATEST SHIFT AND INDEX OF THE LAST SHIFT
            shiftIndex = carDataDF.loc[carNum, 'shiftIndex']
            lastShiftIndex = len(shiftsByCar[str(carNum)])
            # IF NEXT SHIFT EXISTS, TAKE START TIME OF NEXT SHIFT
            if (shiftIndex + 1) < lastShiftIndex:
                nextStart = readTime(shiftsByCar[str(carNum)].loc[shiftIndex+1, 'startShift'])

            # IF SHIFT INDEX GOES BEYOND LAST SHIFT, TAKE ARBITRARY LEAVETIME
            else:
                lastStart = shiftsByCar[str(carNum)].loc[lastShiftIndex-1, 'startShift']
                lastDay = readTime(lastStart).date() + dt.timedelta(days=1)
                nextStart = readTime(str(lastDay) + " 23:59:59")

            # CALCULATE TIME LEFT AND BATT NEEDED
            hrsLeft = ((rereadTime(nextStart) - rereadTime(time)).total_seconds())/(60*60)
            battLeft = carDataDF.loc[carNum,'battSize']-carDataDF.loc[carNum,'battkW']
            prior = battLeft/hrsLeft

            # ***** DELAY CHARGING FOR CARS THAT ARE IN DEPOT DURING THE GREEN ZONE *****
            # READ IN START AND END TIMES OF GREEN ZONE
            greenStartHr = pricesDF.loc[pricesDF['company']==company, 'startGreenZone'].to_string(index=False)[1:]
            greenEndHr = pricesDF.loc[pricesDF['company']==company, 'endGreenZone'].to_string(index=False)[1:]

            # IF GREEN ZONE RUNS OVERNIGHT:
            if (readTime(greenStartHr) > readTime(greenEndHr)):
                # GREEN START = CURRENT DAY + GREEN ZONE START TIME
                greenStart = readTime(str(time.date()) + " " + greenStartHr)
                # GREEN END = NEXT DAY + GREEN END TIME
                greenEnd = readTime(str(time.date() + dt.timedelta(days=1)) + " " + greenEndHr)

            # IF GREEN ZONE DOESN'T RUN OVERNIGHT, CONSIDER CASE WHERE TIME IS PAST MIDNIGHT
            else:
                # CALCULATE DIFFERENCE GREEN ZONE START TIME AND MIDNIGHT
                arbGreenStart = dt.datetime.combine(dt.date.today(), readTime(greenStartHr))
                arbMidnight = dt.datetime.combine(dt.date.today(), readTime("00:00:00"))
                gap = arbGreenStart - arbMidnight

                # GREEN START = (TIME-GAP) + 1 DAY + GREEN ZONE START TIME
                greenStart = readTime(str((time-gap).date() + dt.timedelta(days=1)) + " " + greenStartHr)
                # GREEN END = (TIME-GAP) + 1 DAY + GREEN ZONE END TIME
                greenEnd = readTime(str((time-gap).date() + dt.timedelta(days=1)) + " " + greenEndHr)

            # IF GREEN ZONE HASN'T STARTED YET,
            # AND IF CAR WILL BE CHARGING THROUGHOUT WHOLE OF GREEN ZONE:
            if (time < greenStart) and (nextStart >= greenEnd):
                # DELAY CHARGING UNTIL GREEN ZONE
                prior = 0.0

            # LET PRIORITY = BATTLEFT/TIME LEFT, APPEND TO LIST
            priorityRows.append([carNum, prior, battLeft])

        # ***** CONVERT LIST INTO DATAFRAME AND SORT BY PRIORITY *****
        leaveTimes = pd.DataFrame.from_records(priorityRows, columns=['car','priority','battLeft'])
        leaveTimes = leaveTimes.sort_values(by=['priority'], ascending=False)
        leaveTimes = leaveTimes.reset_index(drop=True)

        # ***** IN SORTED ORDER, CALCULATE PRIORITY RATIO AND CHARGE *****
        # CALCULATE THE SUM OF PRIORITY VALUES
        prioritySum = sum(leaveTimes.priority)

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
                toChargeDF.loc[car, 'chargeRate'] = chargeRate

    return carDataDF, chargePtDF, toChargeDF, totalCost

#################################################################################################################################

############################################
# RUN SIMULATION FROM SEPARATE FILE
############################################
def runSimulation(startTime, runTime, RCduration, RCperc,
                  fleetData, driveDataDF, allShiftsDF, pricesDF, company,
                  algo):

    # INITIALISE MAIN DATAFRAMES WITH DATA AT START TIME
    #   Get data from csv inputs
    carData, chargePtData = getLists(fleetData)

    #   Choose column names
    carCols = ["battkW","inDepot","battSize","chargePt","shiftIndex","latestStartShift","latestEndShift"]
    cpCols = ["maxRate","inUse"]
    simCols = ["time","car","chargeDiff","batt","event","costPerCharge","totalCost"]
    tcCols = ["car","chargeRate"]

    #   Initialise dataframes
    carDataDF = pd.DataFrame.from_records(carData, columns=carCols)
    chargePtDF = pd.DataFrame.from_records(chargePtData, columns=cpCols)
    simulationDF = pd.DataFrame(columns=simCols)

    #   Create rows for every car in toChargeDF
    toChargeDFrows = []
    for i in range(len(carDataDF)):
        toChargeDFrows.append([i, 0])
    #   Initialise toChargeDF
    toChargeDF = pd.DataFrame(toChargeDFrows, columns=tcCols)

    # APPEND CARS INTO DEPOT AT START TIME
    depot = []
    for car in range(0, len(carDataDF)):
        if carDataDF.loc[car,'inDepot']: depot.append(car)

    # CREATE LIBRARY FOR SHIFTS BY CAR
    shiftsByCar = unpackShifts(carDataDF, allShiftsDF)

    # CREATE LIBRARY FOR DRIVING DATA
    driveDataByCar = {}
    for car in range(0, len(carDataDF)):
        findData = driveDataDF.loc[driveDataDF['car']==car]
        dataNoIndex = findData.reset_index(drop=True)
        driveDataByCar['%s' % car] = dataNoIndex

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
        carDataDF, depot, chargePtDF, toChargeDF, eventChange = inOutDepot(carDataDF, shiftsByCar, time, depot, chargePtDF, toChargeDF, eventChange)
        toChargeDF, eventChange = readFullBattCars(carDataDF, simulationDF, toChargeDF, time, totalCost, eventChange)
        eventChange = readTariffChanges(time, pricesDF, company, eventChange)

        # *** RUN FUNCTIONS AFFECTING CARS OUTSIDE THE DEPOT ***
        # DECREASE BATT/RAPID CHARGE CARS OUTSIDE THE DEPOT
        carDataDF, rcCount, simulationDF, totalCost = driving(carDataDF, time, rcCount, RCduration, RCperc, simulationDF, driveDataByCar, i, totalCost)

        # *** RUN FUNCTIONS AFFECTING CARS IN THE DEPOT ***
        # IF THERE IS AN EVENT, RUN CHARGING ALGORITHM
        if eventChange == True:
            carDataDF, chargePtDF, toChargeDF, totalCost = algo(carDataDF, depot, shiftsByCar, time, availablePower, simulationDF, chargePtDF, toChargeDF, pricesDF, company, totalCost)

        # CHARGE/READ WAITING CARS IN THE DEPOT
        carDataDF, simulationDF, chargePtDF, totalCost = charge(carDataDF, depot, simulationDF, time, chargePtDF, toChargeDF, pricesDF, company, totalCost)

        # FORMAT TOTAL COST COLUMN IN SIMULATION DF
        simulationDF = adjustTotalCost(time, simulationDF)

        # INCREMENT TIME OF SIMULATION
        time = incrementTime(time)

    return simulationDF, rcCount
