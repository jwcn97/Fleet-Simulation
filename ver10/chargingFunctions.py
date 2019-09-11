import pandas as pd
import numpy as np
import time
from chunks import chunks
from supportFunctions import *

######################################################
# FUNCTIONS WHICH SUPPORT CHARGING
######################################################

# ALLOCATE AN AVAILABLE CHARGE PT OR SELECT CURRENT CHARGE PT
def findChargePt(carDataDF, car, chargePtDF):
    # SELECT AVAILABLE CHARGE PTS
    availablePts = chargePtDF.loc[chargePtDF['inUse'] != 1]
    chargePt = carDataDF.loc[car, 'chargePt']

    # IF CAR IS NOT ON A CHARGE PT, PLUG INTO FIRST AVAILABLE CHARGE PT
    if np.isnan(chargePt) and len(availablePts) > 0:
        pt = availablePts.index[0]
        # print("car "+str(car)+" plugged into CP "+str(pt))
        availablePts = availablePts.drop(pt, axis=0)

        # UPDATE CHARGE PT DF and CAR DATA DF
        chargePtDF.loc[pt, 'inUse'] = 1
        carDataDF.loc[car, 'chargePt'] = pt

    # IF CAR HAS A CHARGE PT, PT = CHARGE PT, ELSE PT = NAN
    else:
        pt = chargePt

    return pt, carDataDF, chargePtDF

# IN SORTED ORDER, CALCULATE PRIORITY RATIO AND ASSIGN CHARGE
def priorityCharge(priorityRows, availablePower, carDataDF, chargePtDF):
    # CONVERT LIST INTO DATAFRAME AND SORT BY PRIORITY
    priorities = pd.DataFrame.from_records(priorityRows, columns=['car','priority','battLeft','pt'])
    priorities = priorities.sort_values(by=['priority'], ascending=False)
    priorities = priorities.reset_index(drop=True)

    # CALCULATE THE SUM OF PRIORITY VALUES
    prioritySum = sum(priorities.priority)
    
    # FOR EVERY CAR:
    for row in range(0, len(priorities)):
        # READ IN DATA FOR SELECTED CAR
        car = priorities.loc[row, 'car']
        batt = carDataDF.loc[car, 'battkW']
        battSize = carDataDF.loc[car, 'battSize']
        battLeft = priorities.loc[row, 'battLeft']
        priority = priorities.loc[row, 'priority']
        pt = priorities.loc[row, 'pt']

        # READ MAX RATE
        maxRate = chargePtDF.loc[pt, 'maxRate']
        chargeRate = 0

        # CALCULATE CHARGE RATE USING PRIORITY/SUM OF PRIORITIES
        if prioritySum == 0.0: chargeRate = 0
        else:                  chargeRate = (priority/prioritySum)*availablePower

        # IF CHARGE RATE EXCEEDS MAX RATE:
        if chargeRate > maxRate: chargeRate = maxRate
        # IF CHARGE RATE EXCEEDS CHARGE NEEDED:
        if chargeRate/chunks > battLeft: chargeRate = battLeft*chunks

        # ADJUST REMAINING AVAILABLE POWER AND PRIORITY SUM
        availablePower -= chargeRate
        prioritySum -= priority

        # UPDATE CHARGE RATE
        carDataDF.loc[car, 'chargeRate'] = chargeRate

    return carDataDF

# CHARGE VEHICLE FOR ONE HOUR
def charge(time, carDataDF, depot, simulationDF, pricesDF):
    # GET TOTAL COST OF ALL VEHICLES
    totalCost = carDataDF['totalCost'].sum()

    # FOR EVERY CAR IN THE DEPOT
    for index in range(len(depot)):
        car = depot[index]

        # READ IN BATTERY, BATTERY SIZE AND CHARGE RATE
        batt = carDataDF.loc[car,'battkW']
        battSize = carDataDF.loc[car,'battSize']
        chargeRate = carDataDF.loc[car,'chargeRate']

        # DETERMINE EVENT STATUS
        if chargeRate > 0:     event = "charge"
        elif batt == battSize: event = "full"
        else:                  event = "wait"

        # TAKE INTO ACCOUNT VEHICLES REACHING FULL BATTERY
        if batt + chargeRate/chunks >= battSize:
            chargeRate = (battSize-batt)*chunks

        # FIND PRICE OF CHARGE AT TIME
        #   * Read in start and end times of green zone
        lowTariffStartHr = getData(pricesDF, 'startGreenZone')
        lowTariffEndHr = getData(pricesDF, 'endGreenZone')
        #   * Read in current time without date
        timeHr = readTime(str(time.time()))

        # USE APPROPRIATE PRICING BASED ON CURRENT TIME
        if readTime(lowTariffStartHr) <= timeHr < readTime(lowTariffEndHr):
            price = float(getData(pricesDF, 'priceGreenZone'))
        else:
            price = float(getData(pricesDF, 'priceRedZone'))

        # CALCULATE COST OF CHARGE AND ADD THIS TO TOTAL COST
        costOfCharge = (chargeRate*price)/chunks
        totalCost += costOfCharge

        # APPEND DATA TO SIMULATION DATA
        simulationDF = simulationDF.append({
            'time': time,
            'car': car,
            'chargeDiff': round(chargeRate/chunks, 2),
            'batt': round(batt, 2),
            'event': event,
            'costPerCharge': round(costOfCharge, 2) if chargeRate > 0 else 0,
            'totalCost': round(totalCost, 2)
        }, ignore_index=True)

        # ASSIGN UPDATED BATTERY KW
        carDataDF.loc[car, 'battkW'] = batt + chargeRate/chunks

        # ASSIGN UPDATED TOTAL COST
        carTotalCost = carDataDF.loc[car, 'totalCost']
        carDataDF.loc[car, 'totalCost'] = carTotalCost + costOfCharge

    return carDataDF, simulationDF


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

    # ***** CALCULATE PRIORITY FOR EACH CAR AND APPEND TO A LIST *****
    for cars in range(0, len(depot)):
        carNum = depot[cars]

        # GET BATTERY AND BATTERY SIZE
        batt = carDataDF.loc[carNum, 'battkW']
        battSize = carDataDF.loc[carNum, 'battSize']

        # ONLY CONSIDER VEHICLES WITHOUT FULL BATTERY
        if batt < battSize:
            # ALLOCATE CHARGE PT IF CAR DOESN'T HAVE ONE
            pt, carDataDF, chargePtDF = findChargePt(carDataDF, carNum, chargePtDF)

            # FIND THE START TIME OF NEXT SHIFT
            nextStart = nextShiftStart(carNum, carDataDF, shiftsByCar)

            # CALCULATE TIME LEFT AND BATT NEEDED
            hrsLeft = ((rereadTime(nextStart) - rereadTime(time)).total_seconds())/(60*60)
            battLeft = battSize-batt

            # PREVENT VEHICLE FROM CHARGING IF IT IS NOT ATTACHED TO A CHARGE POINT
            if np.isnan(pt): prior = 0.0
            else:            prior = battLeft/(hrsLeft**2)

            # LET PRIORITY = BATTLEFT/TIME LEFT, APPEND TO LIST
            priorityRows.append([carNum, prior, battLeft, pt])

    # IN SORTED ORDER, CALCULATE PRIORITY RATIO AND CHARGE
    carDataDF = priorityCharge(priorityRows, availablePower, carDataDF, chargePtDF)

    return carDataDF

##############################################
# INCREASE BATT DURING CHARGE (COST SENSITIVE)
##############################################
# PRIORITY = BATT NEEDED/TIME LEFT IN DEPOT
# IF CAR WILL CHARGE OVER LOW TARIFF ZONE:
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

        # GET BATTERY AND BATTERY SIZE
        batt = carDataDF.loc[carNum, 'battkW']
        battSize = carDataDF.loc[carNum, 'battSize']

        # ONLY CONSIDER VEHICLES WITHOUT FULL BATTERY
        if batt < battSize:
            # ALLOCATE CHARGE PT IF CAR DOESN'T HAVE ONE
            pt, carDataDF, chargePtDF = findChargePt(carDataDF, carNum, chargePtDF)

            # FIND THE START TIME OF NEXT SHIFT
            nextStart = nextShiftStart(carNum, carDataDF, shiftsByCar)

            # CALCULATE TIME LEFT AND BATT NEEDED
            hrsLeft = ((rereadTime(nextStart) - rereadTime(time)).total_seconds())/(60*60)
            battLeft = battSize-batt

            # IF TIME IS BEFORE LOW TARIFF ZONE,
            # AND IF CAR WILL BE CHARGING THROUGHOUT WHOLE OF LOW TARIFF ZONE
            # AND IF VEHICLE IS STILL WAITING FOR THE EXTRA CHARGING:
            if (time < lowTariffStart) and (nextStart > lowTariffStart):
                # DELAY CHARGING UNTIL IT'S TIME TO EXTRA CHARGE
                prior = 0.0
            # IF VEHICLE IS NOT ATTACHED TO A CHARGE POINT
            elif np.isnan(pt):
                # PREVENT VEHICLE FROM CHARGING
                prior = 0.0
            else:
                # ASSIGN PRIORITY
                prior = battLeft/(hrsLeft**2)

            # LET PRIORITY = BATTLEFT/TIME LEFT, APPEND TO LIST
            priorityRows.append([carNum, prior, battLeft, pt])

    # IN SORTED ORDER, CALCULATE PRIORITY RATIO AND CHARGE
    carDataDF = priorityCharge(priorityRows, availablePower, carDataDF, chargePtDF)

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

        # GET BATTERY AND BATTERY SIZE
        batt = carDataDF.loc[carNum, 'battkW']
        battSize = carDataDF.loc[carNum, 'battSize']

        # ONLY CONSIDER VEHICLES WITHOUT FULL BATTERY
        if batt < battSize:
            # ALLOCATE CHARGE PT IF CAR DOESN'T HAVE ONE
            pt, carDataDF, chargePtDF = findChargePt(carDataDF, carNum, chargePtDF)

            # FIND THE START TIME OF NEXT SHIFT
            nextStart = nextShiftStart(carNum, carDataDF, shiftsByCar)

            # CALCULATE TIME LEFT AND BATT NEEDED
            hrsLeft = ((rereadTime(nextStart) - rereadTime(time)).total_seconds())/(60*60)
            battLeft = battSize-batt

            # IF TIME IS BEFORE LOW TARIFF ZONE,
            # AND IF CAR WILL BE CHARGING THROUGHOUT WHOLE OF LOW TARIFF ZONE
            # AND IF VEHICLE IS STILL WAITING FOR THE EXTRA CHARGING:
            if (time < lowTariffStart) and (nextStart > lowTariffStart) and (eventChange[1] != "extraCharging"):
                # DELAY CHARGING UNTIL IT'S TIME TO EXTRA CHARGE
                prior = 0.0
            # IF VEHICLE IS NOT ATTACHED TO A CHARGE POINT
            elif np.isnan(pt):
                # PREVENT VEHICLE FROM CHARGING
                prior = 0.0
            else:
                # ASSIGN PRIORITY
                prior = battLeft/(hrsLeft**2)

            # LET PRIORITY = BATTLEFT/TIME LEFT, APPEND TO LIST
            priorityRows.append([carNum, prior, battLeft, pt])

    # IN SORTED ORDER, CALCULATE PRIORITY RATIO AND CHARGE
    carDataDF = priorityCharge(priorityRows, availablePower, carDataDF, chargePtDF)

    return carDataDF
