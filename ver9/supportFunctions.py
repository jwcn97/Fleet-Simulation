import pandas as pd
import numpy as np
import datetime as dt
import time
from chargingFunctions import chunks

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

# FIND THE START TIME OF NEXT SHIFT
def nextShiftStart(carNum, carDataDF, shiftsByCar):
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
    
    return nextStart

# FIND THE NEXT ZONE WHERE TARIFF IS CHEAPER
def nextLowTariffZone(time, pricesDF):
    # ***** DEFINE NEXT GREEN ZONE *****
    # READ IN START AND END TIMES OF GREEN ZONE
    lowTariffStartHr = getData(pricesDF, 'startGreenZone')
    lowTariffEndHr = getData(pricesDF, 'endGreenZone')

    # IF GREEN ZONE RUNS OVERNIGHT:
    if (readTime(lowTariffStartHr) > readTime(lowTariffEndHr)):
        # GREEN START = CURRENT DAY + GREEN ZONE START TIME
        lowTariffStart = readTime(str(time.date()) + " " + lowTariffStartHr)
        # GREEN END = NEXT DAY + GREEN END TIME
        lowTariffEnd = readTime(str(time.date() + dt.timedelta(days=1)) + " " + lowTariffEndHr)

    # IF GREEN ZONE DOESN'T RUN OVERNIGHT, CONSIDER CASE WHERE TIME IS PAST MIDNIGHT
    else:
        # CALCULATE DIFFERENCE GREEN ZONE START TIME AND MIDNIGHT
        arbGreenStart = dt.datetime.combine(dt.date.today(), readTime(lowTariffStartHr))
        arbMidnight = dt.datetime.combine(dt.date.today(), readTime("00:00:00"))
        gap = arbGreenStart - arbMidnight

        # GREEN START = (TIME-GAP) + 1 DAY + GREEN ZONE START TIME
        lowTariffStart = readTime(str((time-gap).date() + dt.timedelta(days=1)) + " " + lowTariffStartHr)
        # GREEN END = (TIME-GAP) + 1 DAY + GREEN ZONE END TIME
        lowTariffEnd = readTime(str((time-gap).date() + dt.timedelta(days=1)) + " " + lowTariffEndHr)

    return lowTariffStart, lowTariffEnd


##############################
# MISC FUNCTIONS
##############################

# RETRIEVES COLUMN DATA FROM DATAFRAME
def getData(df, col):
    return df[col].values[0]

# GENERATE CAR DATA AND CHARGE POINT DATA
def getLists(df):
    # initialise charge points data
    chargePt_data = []
    for (rate,quantity) in eval(getData(df, 'chargePts')):
        # [maxRate, inUse]
        chargePt_data += [[rate,1]]*quantity

    # initialise car data
    car_data = []
    for (size,quantity) in eval(getData(df, 'cars')):
        # [battkW, inDepot, battSize, chargePt, chargeRate, rcChunks, shiftIndex, latestStartShift, latestEndShift]
        car_data += [[size,1,size,np.nan,0,0,-1,np.nan,np.nan]]*quantity
    
    # assign available charge points to cars
    for cp_id in range(len(chargePt_data)):
        size = car_data[cp_id][0]
        car_data[cp_id] = [size,1,size,cp_id,0,0,-1,np.nan,np.nan]

    return car_data, chargePt_data

# CHOOSE MAX TOTAL COST OF THE ROW
def adjustTotalCost(time, simulationDF):
    # SELECT ROWS IN SIMULATION WHERE TIME == TIME
    selectRows = simulationDF.loc[simulationDF['time']==time]

    # SELECT THE MAXIMUM VALUE IN THE TOTAL COST COLUMN
    maxCost = selectRows['totalCost'].max()

    # REPLACE EVERY OTHER TOTAL COST VALUE WITH MAXIMUM VALUE FOR THIS TIME
    simulationDF.loc[simulationDF['time']==time, 'totalCost'] = maxCost

    return simulationDF


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
# FUNCTIONS WHICH CHECK FOR EVENTS
##############################################

# IMPLEMENT CHANGES AT START AND END OF SHIFTS
def inOutDepot(time, carDataDF, shiftsByCar, depot, chargePtDF, eventChange):
    # WHEN SHIFT STARTS:
        # Remove from depot
        # Let inDepot = 0 in carDataDF
        # If connected to chargePt, remove chargePt

    # WHEN SHIFT ENDS:
        # Enter depot
        # Let inDepot = 1 in carDataDF

    # FOR EVERY CAR:
    for car in range(0, len(carDataDF)):
        
        # ***** CHECK IF CAR IS AT THE END OF A SHIFT *****
        # IF TIME == END TIME OF CURRENT SHIFT:
        if str(time) == carDataDF.loc[car, 'latestEndShift']:
            # ENTER DEPOT
            carDataDF.loc[car,'inDepot'] = 1
            depot.append(car)

            # RECOGNISE AN EVENT HAS HAPPENED
            eventChange = (True, "enterDepot")

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
                chargePtDF.loc[pt,'inUse'] = np.nan

                # REMOVE CHARGE PT IN CAR DATA DF
                carDataDF.loc[car,'chargePt'] = np.nan

                # RESET RCCHUNKS COUNT and CHARGE RATE
                carDataDF.loc[car,'rcChunks'] = 0
                carDataDF.loc[car,'chargeRate'] = 0

                # UPDATE SHIFT DATA IN CAR DATA DF
                carDataDF.loc[car, 'shiftIndex'] = shiftIndex + 1
                carDataDF.loc[car, 'latestStartShift'] = nextStartShift
                carDataDF.loc[car, 'latestEndShift'] = nextEndShift

                # RECOGNISE AN EVENT HAS HAPPENED
                eventChange = (True, "exitDepot")

    return eventChange, carDataDF, depot, chargePtDF

# READ CARS WITH FULL BATTERY INTO SIMULATION DF
def readFullBattCars(time, carDataDF, simulationDF, totalCost, eventChange):
    # SELECT VEHICLES IN THE DEPOT WITH FULL BATTERY
    chargeDF = carDataDF.loc[carDataDF['inDepot'] == 1]
    fullBattDF = chargeDF.loc[chargeDF['battkW'] == chargeDF['battSize']]

    # IF CAR IS FULLY CHARGED, LET CHARGE RATE = 0 IN TO-CHARGE DF
    for row in range(len(fullBattDF)):
        car = fullBattDF.index[row]
        carDataDF.loc[car, 'chargeRate'] = 0

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
            eventChange = (True, "fullBatt")

    return eventChange, carDataDF

# READ TARIFF CHANGES
def readTariffChanges(time, pricesDF, eventChange):
    # READ IN START AND END TIMES OF GREEN ZONE
    lowTariffStartHr = getData(pricesDF, 'startGreenZone')
    lowTariffEndHr = getData(pricesDF, 'endGreenZone')

    # READ IN TIME WITHOUT DATE
    timeHr = readTime(str(time.time()))

    # TIME == START OR END OF GREEN ZONE, THERE IS A TARIFF CHANGE
    if timeHr == readTime(lowTariffStartHr) or timeHr == readTime(lowTariffEndHr):
        # RECOGNISE AN EVENT HAS HAPPENED
        eventChange = (True, "tariffChange")

    return eventChange

# READ WHETHER NECESSARY TO CHARGE VEHICLES BEFORE LOW TARIFF ZONE
def readExtraCharging(time, pricesDF, depot, carDataDF, shiftsByCar, availablePower, eventChange):
    # DEFINE NEXT LOW TARIFF ZONE
    lowTariffStart, lowTariffEnd = nextLowTariffZone(time, pricesDF)

    # MAKE SURE ALL VEHICLES ARE IN DEPOT (TO TAKE INTO ACCOUNT BATTERY OF ALL VEHICLES)
    if len(depot) == len(carDataDF):
        # CALCULATE TOTAL BATTERY PROVIDED IN GREEN ZONE
        totalBattAvailable = (lowTariffEnd - lowTariffStart).total_seconds()*availablePower/(60*60)

        # ***** CALCULATE TOTAL BATTERY NEEDED IN GREEN ZONE *****
        totalBattLeft = 0
        for cars in range(0, len(depot)):
            carNum = depot[cars]

            # FIND THE START TIME OF NEXT SHIFT
            nextStart = nextShiftStart(carNum, carDataDF, shiftsByCar)

            # IF VEHICLE IS GOING TO BE IN DEPOT DURING GREEN ZONE
            if nextStart > lowTariffStart:
                # APPEND BATTERY LEFT TO TOTAL BATT LEFT
                totalBattLeft += carDataDF.loc[carNum,'battSize']-carDataDF.loc[carNum,'battkW']

        # IF TOTAL BATT LEFT IS MORE THAN THAT PROVIDED, ALLOCATE BUFFER TIME BEFORE LOW TARIFF START FOR VEHICLES TO CHARGE
        #   IF TIME == ALLOCATED TIME BEFORE LOW TARIFF START, CHARGE NOW (INSTEAD OF WAITING TILL LOW TARIFF ZONE)
        if totalBattLeft > totalBattAvailable:
            bufferHrs = (totalBattLeft - totalBattAvailable)/availablePower
            bufferSlots = int(np.ceil(bufferHrs*chunks))

            if time == lowTariffStart-dt.timedelta(hours=bufferSlots/chunks):
                eventChange = (True, "extraCharging")

    return eventChange


###################################################
# DRIVING FUNCTIONS
###################################################

# CHECK WHETHER VEHICLES REQUIRE RAPID CHARGE
#   UPDATE RAPID CHARGE CHUNKS IN CARDATADF and UPDATE RCCOUNT
def checkRC(carDataDF, rcDuration, rcPerc, rcCount):
    # FIND CARS OUTSIDE OF DEPOT
    drivingCarsDF = carDataDF.loc[carDataDF["inDepot"]==0]

    # FOR CARS OUTSIDE OF DEPOT:
    #   * CHECK FOR CARS CURRENTLY RAPID CHARGING
    #   * THEN CHECK FOR CARS THAT NEED RAPID CHARGING
    for row in range(len(drivingCarsDF)):
        car = drivingCarsDF.index[row]

        # FIND DURATION OF RAPID CHARGE IN CHUNKS
        rcChunks = int(np.ceil(rcDuration * chunks))
        # GET THE RAPID CHARGE STATUS OF VEHICLE
        chunkCount = carDataDF.loc[car, 'rcChunks']

        # IF CAR IS RAPID CHARGING AND REQUIRES MORE RAPID CHARGING:
        if 0 < chunkCount < rcChunks:
            # INCREMENT RAPID CHARGE CHUNKS COUNT
            carDataDF.loc[car, 'rcChunks'] += 1

        # ELSE (CAR HAS NOT BEEN RAPID CHARGING), CHECK IF CAR NEEDS RAPID CHARGING
        else:
            batt = carDataDF.loc[car, 'battkW']
            battSize = carDataDF.loc[car, 'battSize']
            # IF BATTERY < RC PERCENTAGE (INPUT), CAR NEEDS RAPID CHARGING
            if batt < (battSize*(rcPerc/100)):
                # INCREMENT RAPID CHARGE CHUNKS COUNT
                carDataDF.loc[car, 'rcChunks'] += 1
                # INCREASE RAPID CHARGE COUNT
                rcCount += 1

            # OTHERWISE, RESET RAPID CHARGE CHUNKS COUNT
            else: carDataDF.loc[car, 'rcChunks'] = 0
    
    return rcCount, carDataDF, drivingCarsDF

# LOOK AT CARS OUTSIDE THE DEPOT
#   FOR CARS THAT NEED RAPID CHARGING: RAPID CHARGE
#   FOR CARS THAT DON'T NEED RAPID CHARGING: DECREASE BATT
def driving(time, carDataDF, driveDataByCar, breaksDF, 
            rcCount, rcDuration, rcPerc, rcRate, 
            simulationDF, ind, totalCost):
    # GET CERTAIN PARAMETERS
    drivingValues = driveDataByCar['0'].shape[0]
    breakStart = getData(breaksDF, 'startBreak')
    breakEnd = getData(breaksDF, 'endBreak')

    # UPDATE RAPID CHARGE CHUNKS IN CARDATADF and UPDATE RCCOUNT
    rcCount, carDataDF, drivingCarsDF = checkRC(carDataDF, rcDuration, rcPerc, rcCount)

    for rows in range(len(drivingCarsDF)):
        car = drivingCarsDF.index[rows]
        
        # ***** FOR CARS THAT DON'T NEED RAPID CHARGING, DECREASE BATT (DRIVE) *****
        if carDataDF.loc[car, 'rcChunks'] == 0:
            # READ BATTERY
            batt = carDataDF.loc[car, 'battkW']

            # GET RANDOMISED VALUE FOR MILEAGE AND MPKW
            mileage = driveDataByCar[str(car % 4)].loc[ind % drivingValues, 'mileage']
            mpkw = driveDataByCar[str(car % 4)].loc[ind % drivingValues, 'mpkw']

            # CALCULATE RATE OF BATT DECREASE
            kwphr = 4#mileage/mpkw

            # UPDATE KWPHR TO BE 0.0 DURING BREAK PERIOD
            if not breakStart == "None":
                if readTime(breakStart) <= time.time() < readTime(breakEnd):
                    kwphr = 0.0

            # UPDATE SIMULATION ACCORDINGLY
            simulationDF = simulationDF.append({
                'time': time,
                'car': car,
                'chargeDiff': round(-kwphr/chunks, 1),
                'batt': round(batt, 1),
                'event': 'drive' if not kwphr==0.0 else 'wait',
                'costPerCharge': 0,
                'totalCost': round(totalCost, 2)
            }, ignore_index=True)

            # DECREASE BATTERY
            batt -= kwphr/chunks

            # ASSIGN BATTERY
            carDataDF.loc[car,'battkW'] = batt
        
        # ***** FOR CARS THAT NEED RAPID CHARGING, RAPID CHARGE *****
        else:
            # READ BATTERY AND BATTERY SIZE
            batt = carDataDF.loc[car, 'battkW']
            battSize = carDataDF.loc[car, 'battSize']

            # CALCULATE BATTERY INCREASE
            if batt + rcRate/chunks > battSize: RCbattIncrease = battSize - batt
            else:                               RCbattIncrease = rcRate/chunks

            # UPDATE RAPID CHARGE COUNT AND TOTAL COST
            RCcost = 0.3*(RCbattIncrease)
            totalCost += RCcost

            # UPDATE SIMULATION ACCORDINGLY
            simulationDF = simulationDF.append({
                'time': time,
                'car': car,
                'chargeDiff': round(RCbattIncrease, 1),
                'batt': round(batt, 1),
                'event': 'RC',
                'costPerCharge': round(RCcost, 2),
                'totalCost': round(totalCost, 2)
            }, ignore_index=True)

            # RAPID CHARGE and ASSIGN BATTERY
            batt += RCbattIncrease
            carDataDF.loc[car,'battkW'] = batt

    return carDataDF, rcCount, simulationDF, totalCost


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
def priorityCharge(leaveTimes, availablePower, carDataDF, chargePtDF):
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

            # ADJUST REMAINING AVAILABLE POWER AND PRIORITY SUM
            availablePower -= chargeRate
            prioritySum -= priority

            # UPDATE CHARGE RATE
            carDataDF.loc[car, 'chargeRate'] = chargeRate

    return carDataDF

# CHARGE VEHICLE FOR ONE HOUR
def charge(time, carDataDF, depot, 
            simulationDF, chargePtDF, 
            pricesDF, totalCost):
    # FOR EVERY CAR IN THE DEPOT
    for index in range(len(depot)):
        car = depot[index]

        # READ IN BATTERY, BATTERY SIZE AND CHARGE RATE
        batt = carDataDF.loc[car,'battkW']
        battSize = carDataDF.loc[car,'battSize']
        chargeRate = carDataDF.loc[car,'chargeRate']

        # FIND PRICE OF CHARGE AT TIME
        #   * Read in start and end times of green zone
        lowTariffStartHr = getData(pricesDF, 'startGreenZone')
        lowTariffEndHr = getData(pricesDF, 'endGreenZone')
        #   * Read in time without date
        timeHr = readTime(str(time.time()))

        # IF TIME IS WITHIN GREEN ZONE, PRICE = GREEN ZONE PRICE
        if readTime(lowTariffStartHr) <= timeHr < readTime(lowTariffEndHr):
            price = float(getData(pricesDF, 'priceGreenZone'))
        # ELSE, PRICE = RED ZONE PRICE
        else:
            price = float(getData(pricesDF, 'priceRedZone'))

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

        # INCREASE BATTERY PERCENTAGE ACCORDING TO CHARGE RATE
        batt += chargeRate/chunks
        batt = battSize if batt >= battSize else batt

        # ASSIGN BATTERY
        carDataDF.loc[car, 'battkW'] = batt

    return carDataDF, simulationDF, chargePtDF, totalCost


#############################################
# SUPPORT FUNCTIONS FOR PREDICTIVE CHARGING
#############################################

# STORE INOUTDEPOT EVENTS DURING GREEN ZONE
def getGZStatus(depot, carDataDF, shiftsByCar, lowTariffStart, lowTariffEnd):
    # CREATE A LIST FOR CARS AND THEIR STATUS DURING THE GREEN ZONE
    statusInGreenZone = []

    for cars in range(0, len(depot)):
        carNum = depot[cars]

        # FIND THE NEXT SHIFT
        nextStart = nextShiftStart(carNum, carDataDF, shiftsByCar)

        # IF VEHICLE IS GOING TO BE IN DEPOT DURING GREEN ZONE
        if nextStart > lowTariffStart:
            enterDepotTime = readTime(carDataDF.loc[carNum, 'latestEndShift'])
            leaveDepotTime = nextStart
            if enterDepotTime <= lowTariffStart: enterDepotTime = lowTariffStart
            if leaveDepotTime >= lowTariffEnd: leaveDepotTime = lowTariffEnd

            statusInGreenZone.append([enterDepotTime, carNum, 1])
            statusInGreenZone.append([leaveDepotTime, carNum, -1])

    gzStatus = pd.DataFrame.from_records(statusInGreenZone, columns=['time','car','inDepot'])
    gzStatus = gzStatus.sort_values(by=['time'], ascending=True)
    gzStatus = gzStatus.reset_index(drop=True)
    
    return gzStatus
