import pandas as pd
import numpy as np
import datetime as dt
import time

# CHOOSE NUMBER OF CHUNKS IN AN HOUR
#   e.g. 3 chunks would divide the hour into 20-min shifts
chunks = 2

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

# SELECT FLEET DATA IN EXECUTION FILE BASED ON:
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
    car_data = [[30, 1, 30, np.nan, -1, np.nan, np.nan]]*smallCars + [[40, 1, 40, np.nan, -1, np.nan, np.nan]]*mediumCars + [[70, 1, 70, np.nan, -1, np.nan,np.nan]]*largeCars
    # assign available charge points to cars
    for cp_id in range(chargePts):
        size = car_data[cp_id][0]
        car_data[cp_id] = [size,1,size,cp_id,-1,np.nan,np.nan]

    return car_data, chargePt_data

# ORGANISE DATAFRAME FOR VIEWING
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

################################################################
# UNPACK SHIFT DATA FROM DATA FRAME INTO LIBRARY (SHIFTS BY CAR)
################################################################
def unpackShifts(carData, allShiftsDF):
    # INITIALISE LIBRARY
    shiftsByCar = {}

    # FOR ALL CARS:
    for cars in range(0, len(carData)):
        # SELECT DATA FOR CAR
        shiftsDFcar = allShiftsDF.loc[allShiftsDF['car']==cars]

        # CREATE NEW DATAFRAME FOR UNPACKED SHIFTS
        shiftsDF = pd.DataFrame(columns=["startShift","endShift"])

        # FOR EVERY DAY, UNPACK SHIFTS INTO DATA FRAME:
        for day in range(len(shiftsDFcar)):
            # READ IN THE DATE AS A STRING AND LIST OF SHIFTS
            dayStr = str(shiftsDFcar.loc[(shiftsDFcar.index[day]), 'day'])
            shiftsLi = eval(shiftsDFcar.loc[(shiftsDFcar.index[day]), 'shift'])

            # ***** UNPACK AND REFORMAT SHIFTS INTO NEW DATAFRAME *****
            # FOR EVERY SHIFT:
            for shift in range(0, len(shiftsLi)):
                # SPLIT SHIFT INTO START SHIFT AND END SHIFT
                splitShift = shiftsLi[shift].split("-")

                # IF START SHIFT < END SHIFT, ASSUME SHIFT DOESN'T RUN OVERNIGHT
                if readTime(splitShift[0]) < readTime(splitShift[1]):
                    # FORMAT DATE AND TIME TO START AND END SHIFT
                    startS = dayStr + " " + splitShift[0]
                    endS = dayStr + " " + splitShift[1]
                # IF START SHIFT < END SHIFT, ASSUME SHIFT RUNS OVERNIGHT
                else:
                    # FOR START SHIFT, FORMAT USING CURRENT DATE
                    startS = dayStr + " " + splitShift[0]
                    # FOR END SHIFT, FORMAT USING DATE OF THE NEXT DAY
                    nextDay = readTime(dayStr) + dt.timedelta(days=1)
                    endS = str(nextDay) + " " + splitShift[1]

                # APPEND START AND END SHIFT AS A ROW IN SHIFTS DF
                newRow = {"startShift" : startS,
                          "endShift" : endS}
                shiftsDF = shiftsDF.append(newRow, ignore_index=True)

        # SORT SHIFTS DF AND ASSIGN TO LIBRARY
        shiftsDF = shiftsDF.sort_values(by=['startShift'])
        shiftsDF = shiftsDF.reset_index(drop=True)
        shiftsByCar['%s' % cars] = shiftsDF

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

def inOutDepot(carDataDF, shiftsByCar, time, depot, chargePtDF, toChargeDF, eventChange):
    # FOR EVERY CAR:
    for car in range(0, len(carDataDF)):

        # ***** CHECK IF CAR IS AT THE END OF A SHIFT *****
        # IF TIME == END TIME OF CURRENT SHIFT:
        if str(time) == carDataDF.loc[car, 'latestEndShift']:
            # ENTER DEPOT
            carDataDF.loc[car,'inDepot'] = 1
            depot.append(car)

            # RECOGNISE AN EVENT HAS HAPPENED
            eventChange = True

        # ***** CHECK IF CAR IS AT THE START OF A SHIFT *****
        # READ INDEX OF CURRENT SHIFT AND LENGTH OF SHIFTS BY CAR
        shiftIndex = carDataDF.loc[car, 'shiftIndex']
        lastShiftIndex = len(shiftsByCar[str(car)])

        # IF NEXT SHIFT EXISTS:
        if (shiftIndex + 1) < lastShiftIndex:
            # READ START TIME AND END TIME OF THE NEXT SHIFT
            nextStartShift = shiftsByCar[str(car)].loc[shiftIndex+1, 'startShift']
            nextEndShift = shiftsByCar[str(car)].loc[shiftIndex+1, 'endShift']

            # IF TIME == START TIME OF THE NEXT SHIFT:
            if str(time) == nextStartShift:
                # EXIT DEPOT
                carDataDF.loc[car,'inDepot'] = 0
                depot.remove(car)

                # REMOVE CHARGE PT IN CHARGE PT DF
                pt = carDataDF.loc[car,'chargePt']
                if not np.isnan(pt):
                    chargePtDF.loc[pt,'inUse'] = np.nan
                    # print("remove charge point "+str(pt))

                # REMOVE CHARGE PT IN CAR DATA DF
                carDataDF.loc[car,'chargePt'] = np.nan

                # LET CHARGE RATE = 0 IN TO-CHARGE DF
                toChargeDF.loc[car,'chargeRate'] = 0

                # UPDATE SHIFT DATA IN CAR DATA DF
                carDataDF.loc[car, 'shiftIndex'] = shiftIndex + 1
                carDataDF.loc[car, 'latestStartShift'] = nextStartShift
                carDataDF.loc[car, 'latestEndShift'] = nextEndShift

                # RECOGNISE AN EVENT HAS HAPPENED
                eventChange = True

    return carDataDF, depot, chargePtDF, toChargeDF, eventChange

################################################
# READ CARS WITH FULL BATTERY INTO SIMULATION DF
################################################
def readFullBattCars(carDataDF, simulationDF, toChargeDF, time, totalCost, eventChange):
    # SELECT VEHICLES IN THE DEPOT WITH FULL BATTERY
    chargeDF = carDataDF.loc[carDataDF['inDepot'] == 1]
    fullBattDF = chargeDF.loc[chargeDF['battkW'] == chargeDF['battSize']]

    # IF CAR IS FULLY CHARGED, LET CHARGE RATE = 0 IN TO-CHARGE DF
    for row in range(len(fullBattDF)):
        car = fullBattDF.index[row]
        toChargeDF.loc[car, 'chargeRate'] = 0

    # ***** IF NEW CARS REACH FULL BATT, RECOGNISE EVENT *****
    # CREATE A SET FOR CARS THAT HAD FULL BATT IN PREVIOUS TIME
    prevSimData = simulationDF.iloc[-len(carDataDF):]
    prevFullBatt = prevSimData.loc[prevSimData['event']=="full"]
    prevFullBattCars = set(prevFullBatt['car'].values.tolist())

    # CREATE A SET FOR CARS THAT CURRENTLY HAVE FULL BATT
    fullBattCars = set(fullBattDF.index.tolist())

    # IF NO. OF FULL BATT CARS >= PREVIOUS NO. OF FULL BATT CARS:
    if len(fullBattCars) >= len(prevFullBattCars):
        # AND IF INDEX OF FULL BATT CARS ARE DIFFERENT FROM PREVIOUS FULL BATT CARS:
        if fullBattCars != prevFullBattCars:
            # RECOGNISE AN EVENT HAS HAPPENED
            eventChange = True

    return toChargeDF, eventChange

################################################
# READ TARIFF CHANGES
################################################
def readTariffChanges(time, pricesDF, company, eventChange):
    # READ IN START AND END TIMES OF GREEN ZONE
    greenStart = pricesDF.loc[pricesDF['company']==company, 'startGreenZone'].to_string(index=False)[1:]
    greenEnd = pricesDF.loc[pricesDF['company']==company, 'endGreenZone'].to_string(index=False)[1:]

    # READ IN TIME WITHOUT DATE
    timeHr = readTime(str(time.time()))

    # TIME == START OR END OF GREEN ZONE, THERE IS A TARIFF CHANGE
    if timeHr == readTime(greenStart) or timeHr == readTime(greenEnd):
        # RECOGNISE AN EVENT HAS HAPPENED
        eventChange = True

    return eventChange

###############################
# LOOK AT CARS OUTSIDE THE DEPOT

# FOR CARS THAT NEED RAPID CHARGING: RAPID CHARGE
# FOR CARS THAT DON'T NEED RAPID CHARGING: DECREASE BATT
###############################
def driving(carDataDF, time, rcCount, RCduration, RCperc, simulationDF, driveDataByCar, ind, totalCost):
    # FIND CARS OUTSIDE OF DEPOT
    drivingCarsDF = carDataDF.loc[carDataDF["inDepot"]==0]

    # ***** DIVIDE CARS THAT NEED RAPID CHARGING AND CARS THAT DONT INTO 2 LISTS *****
    # FIND CARS TO RAPID CHARGE AND APPEND TO LIST
    toRapidCharge = []
    # IF NO NEED TO RAPID CHARGE, APPEND TO ANOTHER LIST
    dontRapidCharge = []

    # FOR CARS OUTSIDE OF DEPOT:
    #   * CHECK FOR CARS CURRENTLY RAPID CHARGING
    #   * THEN CHECK FOR CARS THAT NEED RAPID CHARGING
    for row in range(len(drivingCarsDF)):
        car = drivingCarsDF.index[row]

        # FIND DURATION OF RAPID CHARGE IN CHUNKS
        RCchunks = np.ceil(chunks/(60/RCduration))

        # PREPARE BASE CASE FOR WHILE LOOP
        chunkCount = 1
        checkTime = str(time - ((dt.timedelta(hours=1/chunks))*chunkCount))
        prevSimChunk = simulationDF.loc[simulationDF['time']==checkTime]
        checkEvent = prevSimChunk.loc[prevSimChunk['car']==car, 'event'].to_string(index=False)

        # CHECK IF CAR HAS BEEN RAPID CHARGING
        while checkEvent == "RC":
            chunkCount += 1
            checkTime = str(time - ((dt.timedelta(hours=1/chunks))*chunkCount))
            prevSimChunk = simulationDF.loc[simulationDF['time']==checkTime]
            checkEvent = prevSimChunk.loc[prevSimChunk['car']==car, 'event'].to_string(index=False)

        # IF CAR IS RAPID CHARGING AND REQUIRES MORE RAPID CHARGING:
        if 1 < chunkCount <= RCchunks:
            # APPEND TO RAPID CHARGE LIST
            toRapidCharge.append(car)

        # ELSE (CAR HAS NOT BEEN RAPID CHARGING), CHECK IF CAR NEEDS RAPID CHARGING
        else:
            # IF BATTERY < RC PERCENTAGE (INPUT), CAR NEEDS RAPID CHARGING
            batt = carDataDF.loc[car, 'battkW']
            battSize = carDataDF.loc[car, 'battSize']
            if batt < (battSize*(RCperc/100)):
                # APPEND TO RAPID CHARGE LIST
                toRapidCharge.append(car)
                # INCREASE RAPID CHARGE COUNT
                rcCount += 1

            # OTHERWISE, ADD TO DON'T RAPID CHARGE LIST
            else: dontRapidCharge.append(car)

    # ***** FOR CARS THAT DON'T NEED RAPID CHARGING, DECREASE BATT (DRIVE) *****
    for carsDontRC in range(len(dontRapidCharge)):
        car = dontRapidCharge[carsDontRC]

        # READ BATTERY
        batt = carDataDF.loc[car, 'battkW']

        # GET RANDOMISED VALUE FOR MILEAGE AND MPKW
        mileage = driveDataByCar[str(car)].loc[ind, 'mileage']
        mpkw = driveDataByCar[str(car)].loc[ind, 'mpkw']

        # CALCULATE RATE OF BATT DECREASE
        kwphr = mileage/mpkw

        # UPDATE SIMULATION ACCORDINGLY
        simulationDF = simulationDF.append({
            'time': time,
            'car': car,
            'chargeDiff': round(-kwphr/chunks, 1),
            'batt': round(batt, 1),
            'event': 'drive',
            'costPerCharge': 0,
            'totalCost': round(totalCost, 2)
        }, ignore_index=True)

        # DECREASE BATTERY
        batt -= kwphr/chunks

        # ASSIGN BATTERY
        carDataDF.loc[car,'battkW'] = batt

    # ***** FOR CARS THAT NEED RAPID CHARGING, RAPID CHARGE *****
    for carsToRC in range(len(toRapidCharge)):
        car = toRapidCharge[carsToRC]

        # READ BATTERY AND BATTERY SIZE
        batt = carDataDF.loc[car, 'battkW']
        battSize = carDataDF.loc[car, 'battSize']

        # CALCULATE BATTERY INCREASE
        RCbattIncrease = 50/chunks

        # UPDATE RAPID CHARGE COUNT AND TOTAL COST
        RCcost = 0.3*(50/chunks)
        totalCost += RCcost

        # UPDATE SIMULATION ACCORDINGLY
        simulationDF = simulationDF.append({
            'time': time,
            'car': car,
            'chargeDiff': round(RCbattIncrease, 1),
            'batt': round(batt, 1),
            'event': 'RC',
            'costPerCharge': RCcost,
            'totalCost': round(totalCost, 2)
        }, ignore_index=True)

        # RAPID CHARGE
        batt += RCbattIncrease
        if  batt > battSize: batt = battSize

        # ASSIGN BATTERY
        carDataDF.loc[car,'battkW'] = batt

    return carDataDF, rcCount, simulationDF, totalCost

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

        # UPDATE CHARGE PT DF and CAR DATA DF
        chargePtDF.loc[pt, 'inUse'] = 1
        carDataDF.loc[car, 'chargePt'] = pt

    # IF CAR HAS A CHARGE PT, PT = CHARGE PT, ELSE PT = NAN
    else:
        pt = chargePt
        # print("car "+str(car)+" has charge pt "+str(pt))

    return pt, carDataDF, chargePtDF

###################################
# CHARGE VEHICLE FOR ONE HOUR
###################################
def charge(carDataDF, depot, simulationDF, time, chargePtDF, toChargeDF, pricesDF, company, totalCost):
    # FOR EVERY CAR IN THE DEPOT
    for index in range(len(depot)):
        car = depot[index]

        # READ IN BATTERY, BATTERY SIZE AND CHARGE RATE
        batt = carDataDF.loc[car,'battkW']
        battSize = carDataDF.loc[car,'battSize']
        chargeRate = toChargeDF.loc[car,'chargeRate']

        # FIND PRICE OF CHARGE AT TIME
        #   * Read in start and end times of green zone
        greenStart = pricesDF.loc[pricesDF['company']==company, 'startGreenZone'].to_string(index=False)[1:]
        greenEnd = pricesDF.loc[pricesDF['company']==company, 'endGreenZone'].to_string(index=False)[1:]
        #   * Read in time without date
        timeHr = readTime(str(time.time()))

        # IF TIME IS WITHIN GREEN ZONE, PRICE = GREEN ZONE PRICE
        if readTime(greenStart) <= timeHr < readTime(greenEnd):
            price = float(pricesDF.loc[pricesDF['company']==company, 'priceGreenZone'])
        # ELSE, PRICE = RED ZONE PRICE
        else:
            price = float(pricesDF.loc[pricesDF['company']==company, 'priceRedZone'])

        # CALCULATE COST OF CHARGE AND ADD THIS TO TOTAL COST
        costOfCharge = (chargeRate*price)/chunks
        totalCost += costOfCharge

        # DETERMINE EVENT STATUS
        if chargeRate > 0:
            event = "charge"
        else:
            if batt == battSize: event = "full"
            else: event = "wait"

        # APPEND DATA TO SIMULATION DATA
        simulationDF = simulationDF.append({
            'time': time,
            'car': car,
            'chargeDiff': round(chargeRate/chunks, 1),
            'batt': round(batt, 1),
            'event': event,
            'costPerCharge': round(costOfCharge, 1) if chargeRate > 0 else 0,
            'totalCost': round(totalCost, 2)
        }, ignore_index=True)
        # print("CHARGE")

        # INCREASE BATTERY PERCENTAGE ACCORDING TO CHARGE RATE
        batt += chargeRate/chunks
        batt = battSize if batt >= battSize else batt

        # ASSIGN BATTERY
        carDataDF.loc[car, 'battkW'] = batt

    return carDataDF, simulationDF, chargePtDF, totalCost

############################################
# CHOOSE MAX TOTAL COST OF THE ROW idk how to explain
############################################
def adjustTotalCost(time, simulationDF):
    # SELECT ROWS IN SIMULATION WHERE TIME == TIME
    selectRows = simulationDF.loc[simulationDF['time']==time]

    # SELECT THE MAXIMUM VALUE IN THE TOTAL COST COLUMN
    maxCost = selectRows['totalCost'].max()

    # REPLACE EVERY OTHER TOTAL COST VALUE WITH MAXIMUM VALUE FOR THIS TIME
    simulationDF.loc[simulationDF['time']==time, 'totalCost'] = maxCost

    return simulationDF

#################################################################################################################################
# CORE FUNCTIONS

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

    # FORMAT FINAL SIMULATION DF FOR VIEWING OR ANIMATION
    sim = dfFunction(simulationDF, 'car')

    return styleDF(sim), simulationDF, rcCount
