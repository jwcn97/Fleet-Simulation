import pandas as pd
import numpy as np
import datetime as dt
import time

# CHOOSE NUMBER OF CHUNKS IN AN HOUR
#   e.g. 3 chunks would divide the hour into 20-min shifts
chunks = 3

##############################
# TIME FUNCTIONS
##############################

# CONVERTS TIME INTO DATETIME
def readTime(ti):
    if len(ti) == 5:    read = (dt.datetime.strptime(ti, "%H:%M")).time()
    elif len(ti) == 8:  read = (dt.datetime.strptime(ti, "%H:%M:%S")).time()
    elif len(ti) == 10: read = (dt.datetime.strptime(ti, "%Y-%m-%d")).date()
    else:               read = dt.datetime.strptime(ti, "%Y-%m-%d %H:%M:%S")
    return read

# READS IN A DATETIME AND REFORMATS IT
def rereadTime(ti):
    reread = str(ti)
    read = dt.datetime.strptime(reread, "%Y-%m-%d %H:%M:%S")
    return read

# INCREMENTS TIME BY THE HOUR TO EXECUTE SIMULATION
def incrementTime(ti):
    return (rereadTime(ti) + dt.timedelta(hours=1/chunks))

##############################
# MISC FUNCTIONS
##############################

##################
# Filter based on:
##################
# number of cars
# battery size
# number of fast charge points
def selectCase(df, params):
    for key in params: df = df.loc[df[key] == params[key]]
    return df

# RETRIEVES COLUMN DATA FROM DATAFRAME
def getData(df, col):
    return df[col].values[0]

# GENERATE CAR DATA AND CHARGE POINT DATA
def getLists(df):
    # initialise charge points data
    slow_cps = getData(df, 'slowChargePts')
    fast_cps = getData(df, 'fastChargePts')
    rapid_cps = getData(df, 'rapidChargePts')
    chargePts = slow_cps + fast_cps + rapid_cps
    chargePt_data = ([[22,1]]*rapid_cps + [[7,1]]*fast_cps + [[3,1]]*slow_cps)

    # initialise car data
    smallCars = getData(df, 'smallCars')
    mediumCars = getData(df, 'mediumCars')
    largeCars = getData(df, 'largeCars')
    car_data = [[30,1,30,np.nan]]*smallCars + [[40,1,40,np.nan]]*mediumCars + [[70,1,70,np.nan]]*largeCars
    # assign available charge points to cars
    for cp_id in range(chargePts):
        size = car_data[cp_id][0]
        car_data[cp_id] = [size,1,size,cp_id]

    return car_data, chargePt_data

# ORGANISES DATAFRAME FOR VIEWING
def dfFunction(df, col):
    DF = df.set_index(['time','totalCost',col])
    DF = DF.T.stack().T
    return DF

######################################
# FOR COLOURING CELLS IN SIMULATION DF
######################################

def crColour(val):
    if val > 0: color = 'green'
    elif val == 0: color = 'green'
    else: color = 'red'
    return 'color: %s' % color

def crBackground(val):
    if val > 0: color = '#adfc83'
    elif val == 0: color = '#daed0c'
    else: color = '#fab9b9'
    return 'background-color: %s' % color

def eventBackground(val):
    if val == 'full': color = '#00b200'
    elif val == 'charge': color = '#adfc83'
    elif val == 'drive': color = '#fab9b9'
    elif val == 'wait': color = '#daed0c'
    elif val == 'RC': color = 'red'
    else: color = None
    return 'background-color: %s' % color

def styleDF(df):
    DF = df.style.\
        applymap(crColour, subset=['chargeDiff']).\
        applymap(crBackground, subset=['chargeDiff']).\
        applymap(eventBackground, subset=['event'])
    return DF

########################################
# FORMAT SHIFTS FOR THE DAY INTO LIBRARY (will delete)
########################################
def unpackShifts(carData, allShiftsDF):
    # FORMAT SHIFTS FOR THE DAY
    shiftsByCar = {}
    for cars in range(0, len(carData)):
        # SELECT CELL WITH SHIFT DATA FOR THE CAR AND DAY
        findS = allShiftsDF.loc[(allShiftsDF['car']==cars)]

        # CREATE NEW DATAFRAME FOR UNPACKED SHIFTS
        shiftsDF = pd.DataFrame(columns=["startShift","endShift"])

        # FOR EVERY DAY, UNPACK SHIFTS INTO DATA FRAME
        for day in range(len(findS)):
            # READ IN INFO FOR THE DAY
            dayStr = str(findS.loc[(findS.index[day]), 'day'])
            sList = eval(findS.loc[(findS.index[day]), 'shift'])

            # UNPACK SHIFTS INTO NEW DATAFRAME
            for shift in range(0, len(sList)):
                splitShift = sList[shift].split("-")
                if readTime(splitShift[0]) < readTime(splitShift[1]):
                    startS = dayStr + " " + splitShift[0]
                    endS = dayStr + " " + splitShift[1]
                else:
                    startS = dayStr + " " + splitShift[0]
                    nextDay = readTime(dayStr) + dt.timedelta(days=1)
                    endS = str(nextDay) + " " + splitShift[1]

                newRow = {"startShift" : startS,
                          "endShift" : endS}

                shiftsDF = shiftsDF.append(newRow, ignore_index=True)

        # SORT DATAFRAME AND ASSIGN TO LIBRARY
        shiftsDF = shiftsDF.sort_values(by=['startShift'])
        shiftsDF = shiftsDF.reset_index(drop=True)
        shiftsByCar['%s' % cars] = shiftsDF                             # The value = an empty list

    return shiftsByCar

##############################################
# IMPLEMENT CHANGES AT START AND END OF SHIFTS
##############################################
# WHEN SHIFT STARTS:
    # Remove from depot
    # Let inDepot = 0 in carDataDF
    # If connected to chargePt, remove chargePt

# WHEN SHIFT ENDS:
    # Enter depot
    # Let inDepot = 1 in carDataDF

def inOutDepot(carDataDF, shiftsByCar, time, depot, chargePtDF):
    for car in range(0, len(carDataDF)):
        for shifts in range(0, len(shiftsByCar[str(car)])):
            # READ DATA FOR EVERY ROW IN CarDataDF
            startShiftTime = shiftsByCar[str(car)].loc[shifts, 'startShift']
            endShiftTime = shiftsByCar[str(car)].loc[shifts, 'endShift']

            # IF TIME == THE START OF A SHIFT
            if time == readTime(startShiftTime):
                # EXIT DEPOT
                carDataDF.loc[car,'inDepot'] = 0
                depot.remove(car)

                # REMOVE CHARGE PT IN chargePtDF
                pt = carDataDF.loc[car,'chargePt']
                if not np.isnan(pt):
                    chargePtDF.loc[pt,'inUse'] = np.nan
                    # print("remove charge point "+str(pt))

                # REMOVE CHARGE PT IN carDataDF
                carDataDF.loc[car,'chargePt'] = np.nan

            # IF TIME == THE END OF A SHIFT
            if time == readTime(endShiftTime):
                # ENTER DEPOT
                carDataDF.loc[car,'inDepot'] = 1
                depot.append(car)

    return carDataDF, time, depot, chargePtDF

################################################
# READ CARS WITH FULL BATTERY INTO SIMULATION DF
################################################
def readFullBattCars(carDataDF, simulationDF, time, totalCost):
    # SELECT IDLE VEHICLES
    chargeDF = carDataDF.loc[carDataDF['inDepot'] == 1]
    idleDF = chargeDF.loc[chargeDF['battkW'] == chargeDF['battSize']]
    if len(idleDF) >= 1:
        # LABEL IDLE CARS IN SIMULATION
        for cars in range(len(idleDF)):
            num = idleDF.index[cars]
            batt = carDataDF.loc[num,'battkW']
            simulationDF = simulationDF.append({
                'time': time,
                'car': num,
                'chargeDiff': 0,
                'batt': round(batt, 1),
                'event': 'full',
                'costPerCharge': 0,
                'totalCost': round(totalCost, 2)
            }, ignore_index=True)

    return carDataDF, simulationDF, time

###############################
# DECREASE BATT DURING SHIFT
###############################
def decreaseBatt(carDataDF, shiftsByCar, time, rcCount, simulationDF, driveDataByCar, ind, totalCost):
    # FOR EVERY CAR
    for car in range(len(carDataDF)):
        # READ DATA FOR EVERY ROW IN CarDataDF
        batt = carDataDF.loc[car, 'battkW']
        isC = carDataDF.loc[car, 'inDepot']
        battSize = carDataDF.loc[car, 'battSize']
        mileage = driveDataByCar[str(car)].loc[ind, 'mileage']
        mpkw = driveDataByCar[str(car)].loc[ind, 'mpkw']

        # CALCULATE RATE OF BATT DECREASE
        kwphr = mileage/mpkw

        # SEARCH THROUGH ALL SHIFTS
        for shift in range(0,len(shiftsByCar[str(car)])):
            startS = readTime(shiftsByCar[str(car)].loc[shift, 'startShift'])
            endS = readTime(shiftsByCar[str(car)].loc[shift, 'endShift'])

            # IF SHIFT DOESN'T RUN OVER MIDNIGHT
            if startS < endS:
                # DECREASE BATT DURING SHIFT
                if time >= startS and time < endS:
                    batt = carDataDF.loc[car,'battkW']

                    # CHECK IF BATTERY IS POSITIVE
                    posBatt = ((batt-kwphr/chunks)>0)

                    # UPDATE SIMULATION ACCORDINGLY
                    simulationDF = simulationDF.append({
                        'time': time,
                        'car': car,
                        'chargeDiff': round(-kwphr/chunks, 1),
                        'batt': round(batt, 1),
                        'event': 'drive' if posBatt==True else 'RC',
                        'costPerCharge': 0 if posBatt==True else 6.8,
                        'totalCost': round(totalCost, 2) if posBatt==True
                                     else round((totalCost + 6.8), 2)
                    }, ignore_index=True)
                    batt -= kwphr/chunks

        # RAPID CHARGE OUTSIDE CHARGE CENTRE IF VEHICLE HAS NO BATTERY
        if batt <= 0:
            batt = (carDataDF.loc[car, 'battSize'])*(9/10)
            rcCount += 1
            totalCost += 6.8
            # print("car:" + str(car) + " rapid charge at " + str(time))

        # ASSIGN BATTERY
        carDataDF.loc[car,'battkW'] = batt

    return carDataDF, time, rcCount, simulationDF, totalCost

#############################################################
# ALLOCATE AN AVAILABLE CHARGE PT OR SELECT CURRENT CHARGE PT
#############################################################
def findChargePt(carDataDF, car, chargePtDF):
    # SELECT AVAILABLE CHARGE PTS
    availablePts = chargePtDF.loc[chargePtDF['inUse'] != 1]
    chargePt = carDataDF.loc[car, 'chargePt']

    # IF CAR IS NOT ON A CHARGE PT, PLUG INTO FIRST AVAILABLE CHARGE PT
    if np.isnan(chargePt) and len(availablePts) > 0:
        pt = availablePts.index[0]
        # print("car "+str(car)+" plugged into CP "+str(pt))
        availablePts = availablePts.drop(pt, axis=0)

        # UPDATE chargePtDF and carDataDF
        chargePtDF.loc[pt, 'inUse'] = 1
        carDataDF.loc[car, 'chargePt'] = pt

    # IF CAR HAS A CHARGE PT pt = CHARGE PT, ELSE pt = np.nan
    else:
        pt = chargePt
        # print("car "+str(car)+" has charge pt "+str(pt))

    return pt, carDataDF, chargePtDF

###################################
# CHARGE VEHICLE FOR ONE HOUR
###################################
def charge(carDataDF, carNum, chargeRate, simulationDF, time, chargePtDF, pricesDF, totalCost):
    # READ IN battkW AND battSize FROM carDataDF
    batt = carDataDF.loc[carNum,'battkW']
    battSize = carDataDF.loc[carNum,'battSize']

    # FIND PRICE OF CHARGE AT TIME
    timeStr = str(time.time())
    timeHr = timeStr[:3]+"00:00"
    price = float(pricesDF.loc[pricesDF['hour']==timeHr, 'price'])
    costOfCharge = (chargeRate*price)/chunks
    totalCost += costOfCharge

    # APPEND DATA TO SIMULATION DATA
    simulationDF = simulationDF.append({
        'time': time,
        'car': carNum,
        'chargeDiff': round(chargeRate/chunks, 1),
        'batt': round(batt, 1),
        'event': 'charge' if chargeRate > 0 else 'wait',
        'costPerCharge': round(costOfCharge, 1) if chargeRate > 0 else 0,
        'totalCost': round(totalCost, 2)
    }, ignore_index=True)
    # print("CHARGE")

    # INCREASE BATT PERCENTAGE ACCORDING TO CHARGE RATE
    batt += chargeRate/chunks
    batt = battSize if batt >= battSize else batt
    carDataDF.loc[carNum, 'battkW'] = batt

    return carDataDF, simulationDF, chargePtDF, totalCost


############################################
# CHOOSE MAX TOTAL COST OF THE ROW idk how to explain
############################################
def adjustTotalCost(time, simulationDF):
    # SELECT ROWS IN SIMULATION WHERE TIME == TIME
    selectRows = simulationDF.loc[simulationDF['time']==time]
    maxCost = selectRows['totalCost'].max()
    simulationDF.loc[simulationDF['time']==time, 'totalCost'] = maxCost

    return simulationDF

#################################################################################################################################
# CORE FUNCTIONS

#################################
# INCREASE BATT DURING CHARGE
#################################
def dumbCharge(carDataDF, depot, shiftsByCar, time,
               chargeCapacity, simulationDF, chargePtDF,
               pricesDF, totalCost):
    # SELECT CARS IN DEPOT THAT ARE NOT FULLY CHARGED
    chargeDF = carDataDF.loc[carDataDF['inDepot'] == 1]
    chargeDF = chargeDF.loc[chargeDF['battkW'] < chargeDF["battSize"]]

    # IF THERE ARE CARS THAT REQUIRE CHARGING
    if len(chargeDF) > 0:
        # CALCULATE CHARGE RATE
        if len(chargeDF) <= len(chargePtDF): chargeRate = chargeCapacity/len(chargeDF)
        else:                                chargeRate = chargeCapacity/len(chargePtDF)

        # CHARGE SELECTED CARS IN DEPOT
        for cars in range(len(chargeDF)):
            car = chargeDF.index[cars]
            # ALLOCATE CHARGE PT IF CAR DOESN'T HAVE ONE
            pt, carDataDF, chargePtDF = findChargePt(carDataDF, car, chargePtDF)

            # IF CAR HAS A VALID CHARGE PT
            if not np.isnan(pt):
                # LIMIT CHARGE RATE TO MAX RATE OF CHARGE PT
                maxRatePt = chargePtDF.loc[pt, 'maxRate']
                if maxRatePt < chargeRate: chargeRate = maxRatePt

            # CHARGE
            carDataDF, simulationDF, chargePtDF, totalCost = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF, pricesDF, totalCost)

    return carDataDF, simulationDF, chargePtDF, totalCost

######################################
# INCREASE BATT DURING CHARGE (LEAVETIME)
######################################
def smartCharge_leavetime(carDataDF, depot, shiftsByCar, time,
                          chargeCapacity, simulationDF, chargePtDF,
                          pricesDF, totalCost):
    # IF THERE ARE CARS IN THE DEPOT
    if len(depot) > 0:

        # CREATE A LIST FOR CARS AND THEIR LEAVETIMES
        leaveTList = []

        # FIND THE TIMES WHEN CARS LEAVE THE DEPOT
        for cars in range(0, len(depot)):
            carNum = depot[cars]

            # FIND NEXT SHIFT USING A POINTER TO SEARCH SHIFTS
            #   * Set pointer at 0
            pointer = 0

            #   * Find start time for the first shift at pointer
            startTime = readTime(shiftsByCar[str(carNum)].loc[0, 'startShift'])

            # WHILE START TIME FOR SHIFT < CURRENT TIME, SEARCH NEXT SHIFT
            while startTime < time:
                pointer += 1

                # IF SHIFT EXISTS
                if pointer < len(shiftsByCar[str(carNum)]):
                    # TAKE START TIME OF THE SHIFT
                    startTime = readTime(shiftsByCar[str(carNum)].loc[pointer, 'startShift'])

                # IF POINTER GOES BEYOND LAST SHIFT
                else:
                    # PREVENT TIME FROM EXCEEDING LAST POSSIBLE TIME
                    lastStart = shiftsByCar[str(carNum)].loc[pointer-1, 'startShift']
                    lastDay = readTime(lastStart).date() + dt.timedelta(days=1)
                    startTime = readTime(str(lastDay) + " 23:59:59")

            # CALCULATE TIME UNTIL CAR LEAVES AND APPEND TO LIST
            hrsLeft = abs(rereadTime(startTime) - rereadTime(time))
            leaveTList.append([carNum, hrsLeft])

        # CONVERT LIST INTO DATAFRAME AND SORT
        leaveTimes = pd.DataFrame.from_records(leaveTList, columns=['car','hrsLeft'])
        leaveTimes = leaveTimes.sort_values(by=['hrsLeft'])
        leaveTimes = leaveTimes.reset_index(drop=True)


        # CHARGE CARS IN SORTED ORDER
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

                # IF CAR HAS A VALID CHARGE PT
                if not np.isnan(pt):
                    # READ MAX RATE
                    maxRate = chargePtDF.loc[pt, 'maxRate']
                    energyLeft = chargeCapacity - maxRate

                    # IF ENOUGH CAPACITY FOR FOR MAX RATE, CHARGE CAR AT MAX
                    if energyLeft >= 0:
                        chargeRate = maxRate

                    # IF NOT ENOUGH FOR MAX RATE, CHARGE USING REMAINING POWER
                    elif energyLeft < 0 and energyLeft > -maxRate:
                        chargeRate = chargeCapacity

                    # IF VEHICLE IS PLUGGED IN BUT NOT ALLOCATED CHARGE
                    else:
                        chargeRate = 0

                # CHARGE
                carDataDF, simulationDF, chargePtDF, totalCost = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF, pricesDF, totalCost)
                chargeCapacity -= chargeRate

    return carDataDF, simulationDF, chargePtDF, totalCost

######################################
# INCREASE BATT DURING CHARGE (BATT)
######################################
def smartCharge_batt(carDataDF, depot, shiftsByCar, time,
                     chargeCapacity, simulationDF, chargePtDF,
                     pricesDF, totalCost):
    # IF THERE ARE CARS IN THE DEPOT
    if len(depot) >= 1:

        # CREATE A LIST FOR CARS AND THEIR BATT NEEDED
        battNeededList = []

        # FIND THE BATT NEEEDED UNTIL FULLY CHARGED OF CARS IN THE DEPOT
        for cars in range(0, len(depot)):
            carNum = depot[cars]

            # CALCULATE BATTERY NEEDED AND APPEND TO LIST
            battLeft = abs(carDataDF.loc[carNum,'battSize']-carDataDF.loc[carNum,'battkW'])
            battNeededList.append([carNum, battLeft])

        # CONVERT LIST INTO DATAFRAME AND SORT
        battNeeded = pd.DataFrame.from_records(battNeededList, columns=['car','battLeft'])
        battNeeded = battNeeded.sort_values(by=['battLeft'], ascending=False)
        battNeeded = battNeeded.reset_index(drop=True)

        # CHARGE CARS IN SORTED ORDER
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
                    # TAKE CHARGE RATE AS MAX RATE OF CHARGE PT
                    maxRate = chargePtDF.loc[pt, 'maxRate']
                    energyLeft = chargeCapacity - maxRate

                    # IF ENOUGH CAPACITY FOR MAX RATE, CHARGE CAR AT MAX
                    if energyLeft >= 0:
                        chargeRate = maxRate

                    # IF NOT ENOUGH FOR MAX RATE,  CHARGE USING REMAINING POWER
                    elif energyLeft < 0 and energyLeft > -maxRate:
                        chargeRate = chargeCapacity

                    # IF VEHICLE IS PLUGGED IN BUT NOT ALLOCATED CHARGE
                    else:
                        chargeRate = 0

                # CHARGE
                carDataDF, simulationDF, chargePtDF, totalCost = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF, pricesDF, totalCost)
                chargeCapacity -= chargeRate

    return carDataDF, simulationDF, chargePtDF, totalCost

############################################
# INCREASE BATT DURING CHARGE (SUPER SMART)
############################################
def superSmartCharge(carDataDF, depot, shiftsByCar, time,
                     chargeCapacity, simulationDF, chargePtDF,
                     pricesDF, totalCost):
    # IF THERE ARE CARS IN THE DEPOT
    if len(depot) >= 1:

        # CREATE A LIST FOR CARS AND THEIR LEAVETIME AND BATT NEEDED
        priorityRows = []

        # FIND THE TIMES WHEN CARS LEAVE THE DEPOT
        for cars in range(0, len(depot)):
            carNum = depot[cars]

            # FIND NEXT SHIFT USING A POINTER TO SEARCH SHIFTS
            #   * Set pointer at 0
            pointer = 0

            #   * Find start time for the first shift at pointer
            startTime = readTime(shiftsByCar[str(carNum)].loc[0, 'startShift'])

            # WHILE START TIME FOR SHIFT < CURRENT TIME, SEARCH NEXT SHIFT
            while startTime < time:
                pointer += 1

                # IF SHIFT EXISTS
                if pointer < len(shiftsByCar[str(carNum)]):
                    # TAKE START TIME OF THE SHIFT
                    startTime = readTime(shiftsByCar[str(carNum)].loc[pointer, 'startShift'])

                # IF POINTER GOES BEYOND LAST SHIFT
                else:
                    # PREVENT TIME FROM EXCEEDING LAST POSSIBLE TIME
                    lastStart = shiftsByCar[str(carNum)].loc[pointer-1, 'startShift']
                    lastDay = readTime(lastStart).date() + dt.timedelta(days=1)
                    startTime = readTime(str(lastDay) + " 23:59:59")


            # CALCULATE TIME LEFT AND BATT NEEDED
            hrsLeft = abs(rereadTime(startTime) - rereadTime(time))
            battLeft = abs(carDataDF.loc[carNum,'battSize']-carDataDF.loc[carNum,'battkW'])

            # LET PRIORITY = BATTLEFT/TIME LEFT, APPEND TO LIST
            priorityRows.append([carNum, battLeft*1000/hrsLeft.total_seconds(), battLeft])

        # CONVERT LIST INTO DATAFRAME AND SORT BY PRIORITY
        leaveTimes = pd.DataFrame.from_records(priorityRows, columns=['car','priority','battLeft'])
        leaveTimes = leaveTimes.sort_values(by=['priority'], ascending=False)
        leaveTimes = leaveTimes.reset_index(drop=True)

        # CALCULATE THE SUM OF PRIORITY VALUES
        prioritySum = sum(leaveTimes.priority)

        # CALCULATE PRIORITY AND CHARGE CARS
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
                    chargeRate = (priority/prioritySum)*chargeCapacity

                    # IF CHARGE RATE EXCEEDS MAX RATE
                    if chargeRate > maxRate: chargeRate = maxRate
                    # IF CHARGE RATE EXCEEDS CHARGE NEEDED
                    if chargeRate > battLeft*chunks: chargeRate = battLeft*chunks

                # ADJUST REMAINING CHARGE CAPACITY AND PRIORITY SUM
                chargeCapacity -= chargeRate
                prioritySum -= priority

                # CHARGE
                carDataDF, simulationDF, chargePtDF, totalCost = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF, pricesDF, totalCost)

    return carDataDF, simulationDF, chargePtDF, totalCost

############################################
# INCREASE BATT DURING CHARGE (COST SENSITIVE)
############################################
def costSensitiveCharge(carDataDF, depot, shiftsByCar, time,
                  chargeCapacity, simulationDF, chargePtDF,
                  pricesDF, totalCost):
    # IF THERE ARE CARS IN THE DEPOT
    if len(depot) >= 1:
        # CREATE A LIST FOR CARS
        priorityRows = []

        # FIND THE TIMES WHEN CARS LEAVE THE DEPOT
        for cars in range(0, len(depot)):
            carNum = depot[cars]

            # FIND NEXT SHIFT USING A POINTER TO SEARCH SHIFTS
            #   * Set pointer at 0
            pointer = 0

            #   * Find start time for the first shift at pointer
            startTime = readTime(shiftsByCar[str(carNum)].loc[0, 'startShift'])

            # WHILE START TIME FOR SHIFT < CURRENT TIME, SEARCH NEXT SHIFT
            while startTime < time:
                pointer += 1

                # IF SHIFT EXISTS
                if pointer < len(shiftsByCar[str(carNum)]):
                    # TAKE START TIME OF THE SHIFT
                    startTime = readTime(shiftsByCar[str(carNum)].loc[pointer, 'startShift'])

                # IF POINTER GOES BEYOND LAST SHIFT
                else:
                    # PREVENT TIME FROM EXCEEDING LAST POSSIBLE TIME
                    lastStart = shiftsByCar[str(carNum)].loc[pointer-1, 'startShift']
                    lastDay = readTime(lastStart).date() + dt.timedelta(days=1)
                    startTime = readTime(str(lastDay) + " 23:59:59")


            # CALCULATE TIME LEFT AND BATT NEEDED
            hrsLeft = abs(rereadTime(startTime) - rereadTime(time))
            battLeft = abs(carDataDF.loc[carNum,'battSize']-carDataDF.loc[carNum,'battkW'])

            # CALCULATE PRIORITY
            prior = battLeft*1000/hrsLeft.total_seconds()

            # DELAY CHARGING FOR CARS THAT ARE IN DEPOT DURING THE GREEN ZONE
            # minus one hour from current time just in case time is 00:00:00
            greenStart = readTime(str((time-dt.timedelta(hours=1)).date() + dt.timedelta(days=1)) + " 01:00:00")
            greenEnd = readTime(str((time-dt.timedelta(hours=1)).date() + dt.timedelta(days=1)) + " 07:00:00")
            if ((time < greenStart) & (startTime >= greenEnd)): prior = 0.0
            
            # APPEND TO COSTROWS
            priorityRows.append([carNum, prior, battLeft])

        # CONVERT LIST INTO DATAFRAME AND SORT BY PRIORITY
        leaveTimes = pd.DataFrame.from_records(priorityRows, columns=['car','priority','battLeft'])
        leaveTimes = leaveTimes.sort_values(by=['priority'], ascending=False)
        leaveTimes = leaveTimes.reset_index(drop=True)

        # CALCULATE THE SUM OF PRIORITY VALUES
        prioritySum = sum(leaveTimes.priority)

        # CALCULATE PRIORITY AND CHARGE CARS
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
                    else:                  chargeRate = (priority/prioritySum)*chargeCapacity

                    # IF CHARGE RATE EXCEEDS MAX RATE
                    if chargeRate > maxRate: chargeRate = maxRate
                    # IF CHARGE RATE EXCEEDS CHARGE NEEDED
                    if chargeRate > battLeft*chunks: chargeRate = battLeft*chunks

                # ADJUST REMAINING CHARGE CAPACITY AND PRIORITY SUM
                chargeCapacity -= chargeRate
                prioritySum -= priority

                # CHARGE
                carDataDF, simulationDF, chargePtDF, totalCost = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF, pricesDF, totalCost)

    return carDataDF, simulationDF, chargePtDF, totalCost


#################################################################################################################################

############################################
# RUN SIMULATION FROM SEPARATE FILE
############################################
def runSimulation(startTime, runTime, fleetData, driveDataDF, allShiftsDF, pricesDF, algo):

    # INITIALISE MAIN DATAFRAMES WITH DATA AT START TIME
    #   Get data from csv inputs
    carData, chargePtData = getLists(fleetData)

    #   Choose column names
    carCols = ["battkW","inDepot","battSize","chargePt"]
    cpCols = ["maxRate","inUse"]
    simCols = ["time","car","chargeDiff","batt","event","costPerCharge","totalCost"]

    #   Initialise dataframes
    carDataDF = pd.DataFrame.from_records(carData, columns=carCols)
    chargePtDF = pd.DataFrame.from_records(chargePtData, columns=cpCols)
    simulationDF = pd.DataFrame(columns=simCols)

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

    # RETRIEVE CHARGE CAPACITY
    chargeCapacity = getData(fleetData, 'chargeCapacity')

    rcCount = 0             # INITIALISE A COUNTER FOR RAPID CHARGES
    totalCost = 0           # INITIALISE A COUNTER FOR TOTAL COST
    time = startTime        # CHOOSE START TIME

    # RUN SIMULATION FOR ALL OF RUN TIME
    for i in range(0, runTime*chunks):
        # RUN FUNCTIONS FOR THE HOUR
        carDataDF, time, depot, chargePtDF = inOutDepot(carDataDF, shiftsByCar, time, depot, chargePtDF)
        carDataDF, simulationDF, time = readFullBattCars(carDataDF, simulationDF, time, totalCost)
        carDataDF, time, rcCount, simulationDF, totalCost = decreaseBatt(carDataDF, shiftsByCar, time, rcCount, simulationDF, driveDataByCar, i, totalCost)
        carDataDF, simulationDF, chargePtDF, totalCost = algo(carDataDF, depot, shiftsByCar, time, chargeCapacity, simulationDF, chargePtDF, pricesDF, totalCost)
        simulationDF = adjustTotalCost(time, simulationDF)

        time = incrementTime(time)

    # FORMAT FINAL SIMULATION DF FOR VIEWING OR ANIMATION
    sim = dfFunction(simulationDF, 'car')
    return styleDF(sim), simulationDF, rcCount    # second dataframe, 'sim', is for animation purposes
