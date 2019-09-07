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
def dumbCharge(time, carDataDF, depot, shiftsByCar, availablePower, chargePtDF, pricesDF, eventChange):
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

    return carDataDF

#########################################
# INCREASE BATT DURING CHARGE (LEAVETIME)
#########################################
def smartCharge_leavetime(time, carDataDF, depot, shiftsByCar, availablePower, chargePtDF, pricesDF, eventChange):
    # CREATE A LIST FOR CARS AND THEIR LEAVETIMES (TIME UNTIL CAR LEAVSE DEPOT)
    leaveTList = []

    # ***** FIND LEAVETIMES AND APPEND TO A LIST *****
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

    return carDataDF

######################################
# INCREASE BATT DURING CHARGE (BATT)
######################################
def smartCharge_batt(time, carDataDF, depot, shiftsByCar, availablePower, chargePtDF, pricesDF, eventChange):
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

    return carDataDF

############################################
# INCREASE BATT DURING CHARGE (SUPER SMART)
############################################
# PRIORITY = BATT NEEDED/TIME LEFT IN DEPOT
# CHARGE RATE = (PRIORITY/SUM OF ALL PRIORITIES)*AVAILABLE POWER
def smartCharge_battOverLeavetime(time, carDataDF, depot, shiftsByCar, availablePower, chargePtDF, pricesDF, eventChange):
    # CREATE A LIST FOR CARS AND THEIR PRIORITY AND BATT NEEDED
    priorityRows = []

    # ***** FIND PRIORITY AND BATT NEEDED AND APPEND TO A LIST *****
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
    priorities = pd.DataFrame.from_records(priorityRows, columns=['car','priority','battLeft'])
    priorities = priorities.sort_values(by=['priority'], ascending=False)
    priorities = priorities.reset_index(drop=True)

    # IN SORTED ORDER, CALCULATE PRIORITY RATIO AND CHARGE
    carDataDF = priorityCharge(priorities, availablePower, carDataDF, chargePtDF)

    return carDataDF

##############################################
# INCREASE BATT DURING CHARGE (COST SENSITIVE)
##############################################
# PRIORITY = BATT NEEDED/TIME LEFT IN DEPOT
# IF CAR WILL CHARGE OVER WHOLE OF LOW TARIFF ZONE:
    # DELAY CHARGING UNTIL START LOW TARIFF ZONE STARTS (PRIORITY = 0)
# CHARGE RATE = (PRIORITY/SUM OF ALL PRIORITIES)*AVAILABLE POWER
def costSensitiveCharge(time, carDataDF, depot, shiftsByCar, availablePower, chargePtDF, pricesDF, eventChange):
    # DEFINE NEXT LOW TARIFF ZONE
    lowTariffStart, lowTariffEnd = nextLowTariffZone(time, pricesDF)
    
    # CREATE A LIST FOR CARS AND THEIR LEAVETIME AND BATT NEEDED
    priorityRows = []

    # ***** CALCULATE PRIORITY FOR EACH CAR AND APPEND TO A LIST *****
    for cars in range(0, len(depot)):
        carNum = depot[cars]

        # FIND THE START TIME OF NEXT SHIFT
        nextStart = nextShiftStart(carNum, carDataDF, shiftsByCar)

        # CALCULATE TIME LEFT AND BATT NEEDED
        hrsLeft = ((rereadTime(nextStart) - rereadTime(time)).total_seconds())/(60*60)
        battLeft = carDataDF.loc[carNum,'battSize']-carDataDF.loc[carNum,'battkW']
        prior = battLeft/hrsLeft

        # IF LOW TARIFF ZONE HASN'T STARTED YET,
        # AND IF CAR WILL BE CHARGING THROUGHOUT WHOLE OF LOW TARIFF ZONE:
        if (time < lowTariffStart) and (nextStart >= lowTariffEnd):
            # DELAY CHARGING UNTIL LOW TARIFF ZONE STARTS
            prior = 0.0

        # LET PRIORITY = BATTLEFT/TIME LEFT, APPEND TO LIST
        priorityRows.append([carNum, prior, battLeft])

    # CONVERT LIST INTO DATAFRAME AND SORT BY PRIORITY
    leaveTimes = pd.DataFrame.from_records(priorityRows, columns=['car','priority','battLeft'])
    leaveTimes = leaveTimes.sort_values(by=['priority'], ascending=False)
    leaveTimes = leaveTimes.reset_index(drop=True)

    # IN SORTED ORDER, CALCULATE PRIORITY RATIO AND CHARGE
    carDataDF = priorityCharge(leaveTimes, availablePower, carDataDF, chargePtDF)

    return carDataDF

##############################################
# INCREASE BATT DURING CHARGE (COST SENSITIVE)
##############################################
# PRIORITY = BATT NEEDED/TIME LEFT IN DEPOT
# IF CAR WILL CHARGE OVER WHOLE OF LOW TARIFF ZONE:
    # DELAY CHARGING UNTIL START LOW TARIFF ZONE STARTS (PRIORITY = 0)
# CHARGE RATE = (PRIORITY/SUM OF ALL PRIORITIES)*AVAILABLE POWER
def costSensitiveCharge2(time, carDataDF, depot, shiftsByCar, availablePower, chargePtDF, pricesDF, eventChange):
    # DEFINE NEXT LOW TARIFF ZONE
    lowTariffStart, lowTariffEnd = nextLowTariffZone(time, pricesDF)
    
    # CREATE A LIST FOR CARS AND THEIR LEAVETIME AND BATT NEEDED
    priorityRows = []

    # ***** CALCULATE PRIORITY FOR EACH CAR AND APPEND TO A LIST *****
    for cars in range(0, len(depot)):
        carNum = depot[cars]

        # FIND THE START TIME OF NEXT SHIFT
        nextStart = nextShiftStart(carNum, carDataDF, shiftsByCar)

        # CALCULATE TIME LEFT AND BATT NEEDED
        hrsLeft = ((rereadTime(nextStart) - rereadTime(time)).total_seconds())/(60*60)
        battLeft = carDataDF.loc[carNum,'battSize']-carDataDF.loc[carNum,'battkW']
        prior = battLeft/hrsLeft

        # IF LOW TARIFF ZONE HASN'T STARTED YET,
        # AND IF CAR WILL BE CHARGING THROUGHOUT LOW TARIFF ZONE:
        if (time < lowTariffStart) and (nextStart > lowTariffStart):
            # DELAY CHARGING UNTIL LOW TARIFF ZONE STARTS
            prior = 0.0

        # LET PRIORITY = BATTLEFT/TIME LEFT, APPEND TO LIST
        priorityRows.append([carNum, prior, battLeft])

    # CONVERT LIST INTO DATAFRAME AND SORT BY PRIORITY
    leaveTimes = pd.DataFrame.from_records(priorityRows, columns=['car','priority','battLeft'])
    leaveTimes = leaveTimes.sort_values(by=['priority'], ascending=False)
    leaveTimes = leaveTimes.reset_index(drop=True)

    # IN SORTED ORDER, CALCULATE PRIORITY RATIO AND CHARGE
    carDataDF = priorityCharge(leaveTimes, availablePower, carDataDF, chargePtDF)

    return carDataDF

##############################################
# INCREASE BATT DURING CHARGE (EXTRA)
##############################################
# PRIORITY = BATT NEEDED/TIME LEFT IN DEPOT
# THERE WILL BE A FUNCTION (READ EXTRA CHARGING) TO LOOK INTO NEXT LOW TARIFF ZONE AND SEE WHETHER VEHICLES NEED EXTRA CHARGING
#   IF YES, IT WILL STATE THAT AN EVENT HAS HAPPENED SO THAT THE ALGORITHM WILL RUN
#   IT WILL ALSO RETURN THE TIME VEHICLES NEED TO CHARGE
# CHARGE VEHICLE WHEN THE TIME COMES
# CHARGE RATE = (PRIORITY/SUM OF ALL PRIORITIES)*AVAILABLE POWER
def extraCharge(time, carDataDF, depot, shiftsByCar, availablePower, chargePtDF, pricesDF, eventChange):
    # DEFINE NEXT LOW TARIFF ZONE
    lowTariffStart, lowTariffEnd = nextLowTariffZone(time, pricesDF)

    # CREATE A LIST FOR CARS AND THEIR LEAVETIME AND BATT NEEDED
    priorityRows = []

    # ***** CALCULATE PRIORITY FOR EACH CAR AND APPEND TO A LIST *****
    for cars in range(0, len(depot)):
        carNum = depot[cars]

        # FIND THE START TIME OF NEXT SHIFT
        nextStart = nextShiftStart(carNum, carDataDF, shiftsByCar)

        # CALCULATE TIME LEFT AND BATT NEEDED
        hrsLeft = ((rereadTime(nextStart) - rereadTime(time)).total_seconds())/(60*60)
        battLeft = carDataDF.loc[carNum,'battSize']-carDataDF.loc[carNum,'battkW']
        prior = battLeft/hrsLeft

        # IF TIME IS BEFORE LOW TARIFF ZONE,
        # AND IF CAR WILL BE CHARGING THROUGHOUT WHOLE OF LOW TARIFF ZONE
        # AND IF VEHICLE IS STILL WAITING FOR THE EXTRA CHARGING:
        if (time < lowTariffStart) and (nextStart > lowTariffStart) and (eventChange[1] != "extraCharging"):
            # DELAY CHARGING UNTIL IT'S TIME TO EXTRA CHARGE
            prior = 0.0

        # LET PRIORITY = BATTLEFT/TIME LEFT, APPEND TO LIST
        priorityRows.append([carNum, prior, battLeft])

    # CONVERT LIST INTO DATAFRAME AND SORT BY PRIORITY
    leaveTimes = pd.DataFrame.from_records(priorityRows, columns=['car','priority','battLeft'])
    leaveTimes = leaveTimes.sort_values(by=['priority'], ascending=False)
    leaveTimes = leaveTimes.reset_index(drop=True)

    # IN SORTED ORDER, CALCULATE PRIORITY RATIO AND CHARGE
    carDataDF = priorityCharge(leaveTimes, availablePower, carDataDF, chargePtDF)

    return carDataDF

##############################################
# INCREASE BATT DURING CHARGE (PREDICTIVE)
##############################################
# PRIORITY = BATT NEEDED/TIME LEFT IN DEPOT
# PREDICTS SPECIFICALLY HOW MUCH CHARGE EACH VEHICLE WILL GET DURING LOW TARIFF PERIOD
#   DETERMINES WHETHER IT IS WORTH WAITING FOR LOW TARIFF PERIOD
# CHARGE RATE = (PRIORITY/SUM OF ALL PRIORITIES)*AVAILABLE POWER
def predictiveCharge(time, carDataDF, depot, shiftsByCar, availablePower, chargePtDF, pricesDF, eventChange):
    # DEFINE NEXT LOW TARIFF ZONE
    lowTariffStart, lowTariffEnd = nextLowTariffZone(time, pricesDF)
    
    # CREATE A LIST FOR CARS AND THEIR LEAVETIME AND BATT NEEDED
    priorityRows = []

    # STORE INOUTDEPOT EVENTS DURING LOW TARIFF ZONE
    gzStatus = getGZStatus(depot, carDataDF, shiftsByCar, lowTariffStart, lowTariffEnd)
    
    # ***** CALCULATE PRIORITY FOR EACH CAR AND APPEND TO A LIST *****
    for cars in range(0, len(depot)):
        carNum = depot[cars]

        # FIND THE START TIME OF NEXT SHIFT
        nextStart = nextShiftStart(carNum, carDataDF, shiftsByCar)

        # CALCULATE TIME LEFT AND BATT NEEDED
        hrsLeft = ((rereadTime(nextStart) - rereadTime(time)).total_seconds())/(60*60)
        battLeft = carDataDF.loc[carNum,'battSize']-carDataDF.loc[carNum,'battkW']
        prior = battLeft/hrsLeft

        # IF LOW TARIFF ZONE HASN'T STARTED YET,
        # AND IF CAR WILL BE CHARGING THROUGHOUT LOW TARIFF ZONE:
        if (time < lowTariffStart) and (nextStart > lowTariffStart):
            # DELAY CHARGING UNTIL LOW TARIFF ZONE
            prior = 0.0

        # DETERMINE WHETHER VEHICLE IS ABLE TO FULLY CHARGE IN LOW TARIFF ZONE
        carTimes = gzStatus.loc[(gzStatus.car == carNum)]
        if (len(carTimes) > 0) and (len(depot) == len(carDataDF)):
            carIn, carOut = carTimes.iloc[:,0]
            toCalculate = gzStatus.loc[(gzStatus.time <= carOut) & (gzStatus.time >= carIn)]
            toCalculate = toCalculate.groupby('time').sum()
            
            chargeAvailable = 0
            carsInDepot = 0
            for i in range(len(toCalculate)-1):
                durationHrs = (toCalculate.index[i+1] - toCalculate.index[i]).total_seconds()/(3600)
                carsInDepot += toCalculate['inDepot'][i]
                chargeAvailable += availablePower*durationHrs/carsInDepot

            if chargeAvailable < battLeft: prior = battLeft/hrsLeft

        # LET PRIORITY = BATTLEFT/TIME LEFT, APPEND TO LIST
        priorityRows.append([carNum, prior, battLeft])

    # CONVERT LIST INTO DATAFRAME AND SORT BY PRIORITY
    leaveTimes = pd.DataFrame.from_records(priorityRows, columns=['car','priority','battLeft'])
    leaveTimes = leaveTimes.sort_values(by=['priority'], ascending=False)
    leaveTimes = leaveTimes.reset_index(drop=True)

    # IN SORTED ORDER, CALCULATE PRIORITY RATIO AND CHARGE
    carDataDF = priorityCharge(leaveTimes, availablePower, carDataDF, chargePtDF)

    return carDataDF

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
        eventChange = (False, None)

        # *** RUN FUNCTIONS THAT INCLUDE WILL RECOGNISE CHANGES IN EVENTS ***
        eventChange, carDataDF, depot, chargePtDF = inOutDepot(time, carDataDF, shiftsByCar, depot, chargePtDF, eventChange)
        eventChange, carDataDF = readFullBattCars(time, carDataDF, simulationDF, totalCost, eventChange)
        eventChange = readTariffChanges(time, pricesDF, eventChange)
        eventChange = readExtraCharging(time, pricesDF, depot, carDataDF, shiftsByCar, availablePower, eventChange)

        # *** RUN FUNCTIONS AFFECTING CARS OUTSIDE THE DEPOT ***
        # DECREASE BATT/RAPID CHARGE CARS OUTSIDE THE DEPOT
        carDataDF, rcCount, simulationDF, totalCost = driving(time, carDataDF, driveDataByCar, breaksDF, 
                                                            rcCount, rcDuration, rcPerc, rcRate, 
                                                            simulationDF, i, totalCost)

        # *** RUN FUNCTIONS AFFECTING CARS IN THE DEPOT ***
        # IF THERE IS AN EVENT and THERE ARE CARS THAT REQUIRE CHARGING
        # RUN CHARGING ALGORITHM
        if (eventChange[0] == True) and (len(depot) > 0):
            carDataDF = algo(time, carDataDF, depot, shiftsByCar, availablePower, chargePtDF, pricesDF, eventChange)

        # CHARGE/READ WAITING CARS IN THE DEPOT
        carDataDF, simulationDF, totalCost = charge(time, carDataDF, depot, simulationDF, pricesDF, totalCost)

        # FORMAT TOTAL COST COLUMN IN SIMULATION DF
        simulationDF = adjustTotalCost(time, simulationDF)

        # INCREMENT TIME OF SIMULATION
        time = incrementTime(time)

    return simulationDF, rcCount, totalCost
