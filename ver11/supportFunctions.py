import pandas as pd
import numpy as np
import datetime as dt
import time
from chunks import chunks

"""
TIME FUNCTIONS
"""
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

# FIND THE START AND END TIME OF NEXT SHIFT
def nextShift(carNum, carDataDF, shiftsByCar):
    # READ INDEX OF LATEST SHIFT AND INDEX OF THE LAST SHIFT
    shiftIndex = carDataDF.loc[carNum, 'shiftIndex']
    lastShiftIndex = len(shiftsByCar[str(carNum)])

    # IF NEXT SHIFT EXISTS, TAKE START TIME AND END TIME OF NEXT SHIFT
    if (shiftIndex + 1) < lastShiftIndex:
        nextStart = readTime(shiftsByCar[str(carNum)].loc[shiftIndex+1, 'startShift'])
        nextEnd = readTime(shiftsByCar[str(carNum)].loc[shiftIndex+1, 'endShift'])

    # IF SHIFT INDEX GOES BEYOND LAST SHIFT, TAKE ARBITRARY LEAVETIME
    else:
        lastStart = shiftsByCar[str(carNum)].loc[lastShiftIndex-1, 'startShift']
        lastDay = readTime(lastStart).date() + dt.timedelta(days=1)
        nextStart = readTime(str(lastDay) + " 05:59:59")
        nextEnd = nextStart + dt.timedelta(hours=2)
    
    return nextStart, nextEnd

# FIND THE START AND END TIME OF NEXT NEXT SHIFT
def nextNextShift(carNum, carDataDF, shiftsByCar):
    # READ INDEX OF LATEST SHIFT AND INDEX OF THE LAST SHIFT
    shiftIndex = carDataDF.loc[carNum, 'shiftIndex']
    lastShiftIndex = len(shiftsByCar[str(carNum)])

    # IF NEXT NEXT SHIFT EXISTS, TAKE START TIME AND END TIME OF NEXT NEXT SHIFT
    if (shiftIndex + 2) < lastShiftIndex:
        nextStart = readTime(shiftsByCar[str(carNum)].loc[shiftIndex+2, 'startShift'])
        nextEnd = readTime(shiftsByCar[str(carNum)].loc[shiftIndex+2, 'endShift'])

    # IF SHIFT INDEX GOES BEYOND LAST SHIFT, TAKE ARBITRARY LEAVETIME
    else:
        lastStart = shiftsByCar[str(carNum)].loc[lastShiftIndex-1, 'startShift']
        lastDay = readTime(lastStart).date() + dt.timedelta(days=1)
        nextStart = readTime(str(lastDay) + " 05:59:59")
        nextEnd = nextStart + dt.timedelta(hours=2)
    
    return nextStart, nextEnd

# FIND THE NEXT ZONE WHERE TARIFF IS CHEAPER
def nextLowTariffZone(time, pricesDF):
    # ***** DEFINE NEXT LOW TARIFF ZONE *****
    # READ IN START AND END TIMES OF LOW TARIFF ZONE
    lowTariffStartHr = getData(pricesDF, 'startGreenZone')
    lowTariffEndHr = getData(pricesDF, 'endGreenZone')

    # IF LOW TARIFF ZONE RUNS OVERNIGHT:
    if (readTime(lowTariffStartHr) > readTime(lowTariffEndHr)):
        # LOW TARIFF START = CURRENT DAY + LOW TARIFF ZONE START TIME
        lowTariffStart = readTime(str(time.date()) + " " + lowTariffStartHr)
        # LOW TARIFF END = NEXT DAY + LOW TARIFF END TIME
        lowTariffEnd = readTime(str(time.date() + dt.timedelta(days=1)) + " " + lowTariffEndHr)

    # IF LOW TARIFF ZONE DOESN'T RUN OVERNIGHT, CONSIDER CASE WHERE TIME IS PAST MIDNIGHT
    else:
        # CALCULATE DIFFERENCE LOW TARIFF ZONE START TIME AND MIDNIGHT
        arbGreenStart = dt.datetime.combine(dt.date.today(), readTime(lowTariffStartHr))
        arbMidnight = dt.datetime.combine(dt.date.today(), readTime("00:00:00"))
        gap = arbGreenStart - arbMidnight

        # LOW TARIFF START = (TIME-GAP) + 1 DAY + LOW TARIFF ZONE START TIME
        lowTariffStart = readTime(str((time-gap).date() + dt.timedelta(days=1)) + " " + lowTariffStartHr)
        # LOW TARIFF END = (TIME-GAP) + 1 DAY + LOW TARIFF ZONE END TIME
        lowTariffEnd = readTime(str((time-gap).date() + dt.timedelta(days=1)) + " " + lowTariffEndHr)

    return lowTariffStart, lowTariffEnd


"""
MISC FUNCTIONS
"""
# RETRIEVES COLUMN DATA FROM DATAFRAME
def getData(df, col):
    return df[col].values[0]

# GENERATE CARDATADF, CHARGEPTDF AND SIMULATIONDF
def generateDF(fleetData, latLongData, carCols, cpCols, latLongCols):
    # initialise charge points data
    chargePt_data = []
    for (rate,quantity) in eval(getData(fleetData, 'chargePts')):
        # [maxRate, inUse]
        chargePt_data += [[rate,1]]*quantity

    # get lat and long of depot and first destination
    (depotLat, depotLong) = eval(getData(fleetData, 'depotCoord'))

    # initialise car data
    car_data = []
    for (size,quantity) in eval(getData(fleetData, 'cars')):
        # [inDepot, battSize, battkW, battNeeded,
        #  lat, long, destLat, destLong, destIndex
        #  chargePt, chargeRate, totalCost, totalDistance, 
        #  rcCount, rcChunks,
        #  shiftIndex, latestStartShift, latestEndShift]
        car_data += [[1, size, size, size,
                    depotLat, depotLong, np.nan, np.nan, 0,
                    np.nan, 0.0, 0.0, 0.0,
                    0, 0,
                    -1, np.nan, np.nan]]*quantity

    # initialise dataframes
    carDataDF = pd.DataFrame.from_records(car_data, columns=carCols)
    chargePtDF = pd.DataFrame.from_records(chargePt_data, columns=cpCols)
    
    # assign available charge points to cars
    for cp_id in range(len(chargePt_data)):
        carDataDF.loc[cp_id, 'chargePt'] = cp_id
    
    # set latitude and longitude of vehicles and setup latLongDF
    latLongDF = pd.DataFrame(columns=latLongCols)
    for car in range(len(carDataDF)):
        carDataDF.loc[car,'destLat'] = eval(latLongData.loc[car,'destinationCoord'])[0][0]
        carDataDF.loc[car,'destLong'] = eval(latLongData.loc[car,'destinationCoord'])[0][1]

        destinations = eval(latLongData.loc[car,'destinationCoord'])
        destinations.append((depotLat, depotLong))
        latLongDF = latLongDF.append({
            "car": car,
            "destinations": destinations
        }, ignore_index=True)        

    return carDataDF, chargePtDF, latLongDF

# CHOOSE MAX TOTAL COST OF THE ROW
def adjustTotalCost(time, sim):
    # SELECT THE MAXIMUM VALUE IN THE TOTAL COST COLUMN FOR CURRENT TIME
    maxCost = max([rows[-1] for rows in sim if rows[0]==time])

    # REPLACE EVERY OTHER TOTAL COST VALUE WITH MAXIMUM VALUE FOR CURRENT TIME
    i = len(sim) - 1
    while i >= 0 :
        sim[i][-1] = maxCost
        i -= 1
        if sim[i][0] != time: break

    return sim


"""
FUNCTIONS WHICH HANDLE CAR SHIFTS
"""
# UNPACK SHIFT DATA FROM DATA FRAME INTO LIBRARY (SHIFTS BY CAR)
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

# GENERATES DEPOT STATUS DATAFRAME FOR EVERY TIME WHEN INOUTDEPOT EVENT OCCURS
def generateDepotStatus(carData, shiftsByCar):
    eventTimes = pd.DataFrame(columns=["time","car","events"])

    # FOR ALL CARS:
    for car in range(len(carData)):
        # PICK OUT SHIFTS FOR A VEHICLE
        carShifts = shiftsByCar[str(car)]

        # ADD THE INITIAL STATE OF VEHICLE (IN DEPOT)
        eventTimes = eventTimes.append({
            "time": readTime("2019-01-01 06:00:00"),
            "car": car,
            "events": 1
        }, ignore_index=True)

        # FOR EACH SHIFT
        for shifts in range(len(carShifts)):
            # ADD START SHIFTS
            eventTimes = eventTimes.append({
                "time": readTime(carShifts.loc[shifts, 'startShift']),
                "car": car,
                "events": -1
            }, ignore_index=True)
            # ADD END SHIFTS
            eventTimes = eventTimes.append({
                "time": readTime(carShifts.loc[shifts, 'endShift']),
                "car": car,
                "events": 1
            }, ignore_index=True)
    
    eventTimes = eventTimes.sort_values(by=["time"], ascending=True)
    eventTimes = eventTimes.reset_index(drop=True)

    def toSet(x): return set(x)

    curr_set = {0,1,2,3}
    shiftByTimes = eventTimes.groupby('time').agg({'events': sum, 'car': toSet})
    shiftByTimes.insert(0, 'time', shiftByTimes.index)
    shiftByTimes = shiftByTimes.reset_index(drop=True)

    for shifts in range(len(eventTimes)):
        car = eventTimes.loc[shifts,'car']
        curr_event = eventTimes.loc[shifts,'events']
        curr_index = shiftByTimes.loc[shiftByTimes['time'] == eventTimes.loc[shifts,'time']].index.values[0]

        if curr_event > 0: curr_set = curr_set.union({car}) # CAR ENTERS DEPOT
        else:              curr_set = curr_set - {car}      # CAR LEAVES DEPOT
            
        shiftByTimes.at[curr_index,'car'] = curr_set
    
    return shiftByTimes

# GETS DEPOT STATUS FOR A TIME SLOT
def getDepotStatus(time, depotStatus):
    firstInstance = depotStatus.loc[depotStatus['time'] >= time]
    prevInstance = depotStatus.loc[depotStatus['time'] < time]

    if (len(firstInstance) > 0) and (firstInstance.iloc[0].time == time):
        return list(firstInstance.iloc[0].car)
    else:
        return list(prevInstance.loc[len(prevInstance)-1, 'car'])

# GETS DEPOT STATUS FOR A TIME RANGE
def getDepotStatusRange(timeTuple, depotStatus):
    (startTime, endTime) = timeTuple
    status = []

    instance = depotStatus.loc[(depotStatus['time'] >= startTime) & (depotStatus['time'] < endTime)]
    prevInstance = depotStatus.loc[depotStatus['time'] < startTime]

    if (len(instance) > 0) and (instance.iloc[0].time > startTime) and (prevInstance is not None):
        prevInstance.at[len(prevInstance)-1, 'time'] = startTime             # update the first time of dataframe
        instance = instance.append(prevInstance.iloc[len(prevInstance)-1])   # adding at end of row
        instance.index = instance.index + 1                                  # shifting index
        instance.sort_index(inplace=True)

    instance.reset_index(inplace=True)

    return instance[['time','car']]


"""
FUNCTIONS WHICH CHECK FOR EVENTS
"""
# IMPLEMENT CHANGES AT START AND END OF SHIFTS
def inOutDepot(time, carDataDF, shiftsByCar, latLongDF, chargePtDF, eventChange):
    # WHEN SHIFT STARTS:
        # Remove from depot
        # Let inDepot = 0 in carDataDF
        # If connected to chargePt, remove chargePt

    # WHEN SHIFT ENDS:
        # Enter depot
        # Let inDepot = 1 in carDataDF

    # FOR EVERY CAR:
    for car in range(0, len(carDataDF)):
        destinations = latLongDF.loc[car, 'destinations']

        # ***** CHECK IF CAR IS AT THE END OF A SHIFT *****
        # IF TIME == END TIME OF CURRENT SHIFT:
        if str(time) == carDataDF.loc[car, 'latestEndShift']:
            # ENTER DEPOT
            carDataDF.loc[car,'inDepot'] = 1

            # RESET LATITUDES AND LONGITUDES
            carDataDF.loc[car,'destIndex'] = 0
            carDataDF.loc[car,'destLat'] = destinations[carDataDF.loc[car,'destIndex']][0]
            carDataDF.loc[car,'destLong'] = destinations[carDataDF.loc[car,'destIndex']][1]
            carDataDF.loc[car,'lat'] = destinations[-1][0]
            carDataDF.loc[car,'long'] = destinations[-1][1]

            # RECOGNISE AN EVENT HAS HAPPENED
            eventChange = "enterDepot"

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
                # REMOVE CHARGE PT IN CHARGE PT DF
                pt = carDataDF.loc[car,'chargePt']
                chargePtDF.loc[pt,'inUse'] = np.nan
                # REMOVE CHARGE PT AND EXIT DEPOT
                carDataDF.loc[car,'chargePt'] = np.nan
                carDataDF.loc[car,'inDepot'] = 0

                # UPDATE PARAMETERS IN CARDATADF
                carDataDF.loc[car,'rcChunks'] = 0
                carDataDF.loc[car,'chargeRate'] = 0
                carDataDF.loc[car,'shiftIndex'] = shiftIndex + 1
                carDataDF.loc[car,'latestStartShift'] = nextStartShift
                carDataDF.loc[car,'latestEndShift'] = nextEndShift

                # RECOGNISE AN EVENT HAS HAPPENED
                eventChange = "exitDepot"

    return eventChange, carDataDF, chargePtDF

# READ CARS WITH FULL BATTERY INTO SIMULATION
def readFullBattCars(carDataDF, sim, eventChange):
    # CREATE A SET FOR CARS THAT CURRENTLY HAVE FULL BATT
    chargeDF = carDataDF.loc[carDataDF['inDepot'] == 1]
    fullBattDF = chargeDF.loc[chargeDF['battkW'] == chargeDF['battSize']]
    fullBattCars = set(fullBattDF.index.tolist())

    # IF CAR IS FULLY CHARGED, LET CHARGE RATE = 0 IN TO-CHARGE DF
    for row in range(len(fullBattDF)):
        car = fullBattDF.index[row]
        carDataDF.loc[car, 'chargeRate'] = 0

    # ***** IF NEW CARS REACH FULL BATT, RECOGNISE EVENT *****
    # CREATE A SET FOR CARS THAT HAD FULL BATT IN PREVIOUS TIME
    prevSimData = sim[-len(carDataDF):]
    prevFullBattCars = set([rows[1] for rows in prevSimData if rows[4]=='full'])

    # IF NO. OF FULL BATT CARS >= PREVIOUS NO. OF FULL BATT CARS:
    if len(fullBattCars) >= len(prevFullBattCars):
        # AND IF INDEX OF FULL BATT CARS ARE DIFFERENT FROM PREVIOUS FULL BATT CARS:
        if fullBattCars != prevFullBattCars:
            # RECOGNISE AN EVENT HAS HAPPENED
            eventChange = "fullBatt"

    return eventChange, carDataDF

# READ CARS THAT HAS ACQUIRED ENOUGH BATTERY
def readCarsWithEnoughBatt(carDataDF, sim, eventChange, predictive):
    # RUN THIS FUNCTION ONLY WHEN THE PREDICTIVE ALGORITHM IS USED
    if predictive:
        # CREATE A DF FOR CARS THAT CURRENTLY ALREADY HAVE ENOUGH BATT
        chargeDF = carDataDF.loc[carDataDF['inDepot'] == 1]
        exceedBattNeededDF = chargeDF.loc[chargeDF['battkW'] == chargeDF['battNeeded']]

        # CREATE A SET FOR CARS THAT ARE CHARGING IN PREVIOUS TIME
        prevSimData = sim[-len(carDataDF):]
        prevChargingCars = set([rows[1] for rows in prevSimData if rows[4]=='charge'])

        for row in range(len(exceedBattNeededDF)):
            car = exceedBattNeededDF.index[row]
            # INSTRUCT VEHICLE TO STOP CHARGING
            carDataDF.loc[car, 'chargeRate'] = 0
            # IF CAR IS STILL CHARGING BEFORE BUT HAS NOW ACQUIRE ENOUGH BATTERY
            if car in prevChargingCars:
                # RECOGNIZE AN EVENT HAS HAPPENED
                eventChange = "exceedBattNeeded"

    return eventChange, carDataDF

# READ TARIFF CHANGES
def readTariffChanges(time, pricesDF, eventChange):
    # READ IN START AND END TIMES OF LOW TARIFF ZONE
    lowTariffStartHr = getData(pricesDF, 'startGreenZone')
    lowTariffEndHr = getData(pricesDF, 'endGreenZone')

    # READ IN TIME WITHOUT DATE
    timeHr = readTime(str(time.time()))

    # TIME == START OR END OF LOW TARIFF ZONE, THERE IS A TARIFF CHANGE
    if timeHr == readTime(lowTariffStartHr) or timeHr == readTime(lowTariffEndHr):
        # RECOGNISE AN EVENT HAS HAPPENED
        eventChange = "tariffChange"

    return eventChange

# PREDICT WHETHER VEHICLES NEED EXTRA CHARGING BEFORE LOW TARIFF ZONE
def predictExtraCharging(time, pricesDF, depot, carDataDF, shiftsByCar, availablePower, eventChange, predictive):
    # DETERMINE UPPER LIMIT OF VEHICLE
    if predictive: upperLimit = 'battNeeded'
    else:          upperLimit = 'battSize'

    # MAKE SURE ALL VEHICLES ARE IN DEPOT (TO TAKE INTO ACCOUNT BATTERY OF ALL VEHICLES)
    if len(depot) == len(carDataDF):
        # DEFINE NEXT LOW TARIFF ZONE
        lowTariffStart, lowTariffEnd = nextLowTariffZone(time, pricesDF)
        # CALCULATE TOTAL BATTERY PROVIDED IN LOW TARIFF ZONE
        totalBattAvailable = (lowTariffEnd - lowTariffStart).total_seconds()*availablePower/(60*60)
        # CHOOSE ONLY VEHICLES WHICH HAVE CHARGE PT ASSIGNED TO THEM
        chargeDF = carDataDF.loc[~carDataDF['chargePt'].isna()]

        # ***** CALCULATE TOTAL BATTERY NEEDED IN LOW TARIFF ZONE *****
        totalBattLeft = 0
        for cars in range(len(chargeDF)):
            carNum = chargeDF.index[cars]
            # FIND THE START AND END TIME OF NEXT SHIFT
            nextStart, nextEnd = nextShift(carNum, chargeDF, shiftsByCar)
            # IF VEHICLE IS GOING TO BE IN DEPOT DURING LOW TARIFF ZONE
            if nextStart > lowTariffStart:
                # APPEND BATTERY LEFT TO TOTAL BATT LEFT
                totalBattLeft += chargeDF.loc[carNum,upperLimit]-chargeDF.loc[carNum,'battkW']

        # IF TOTAL BATT LEFT IS MORE THAN THAT PROVIDED, ALLOCATE BUFFER TIME BEFORE LOW TARIFF START FOR VEHICLES TO CHARGE
        if totalBattLeft > totalBattAvailable:
            bufferHrs = (totalBattLeft - totalBattAvailable)/availablePower
            bufferSlots = int(np.ceil(bufferHrs*chunks))
            # IF TIME >= ALLOCATED TIME BEFORE LOW TARIFF START
            if time >= lowTariffStart - dt.timedelta(hours = bufferSlots/chunks):
                # TRIGGER ALGORITHM TO CHARGE VEHICLE NOW (INSTEAD OF WAITING TILL LOW TARIFF ZONE)
                eventChange = "extraCharging"

    return eventChange


"""
BATTERY PREDICTION
"""
# PREDICT BATTERY NEEDED FOR A PARTICULAR DRIVING PERIOD
def battNeededForShift(time, startDrive, endDrive, driveDataByCar, ind, car):
    # DECLARE VARIABLE TO STORE BATTERY NEEDED
    batteryNeeded = 0
    # READ TOTAL NUMBER OF DRIVING VALUES
    drivingValues = driveDataByCar['0'].shape[0]

    # FIND TIME SLOTS LEFT TILL DRIVING (WILL BE 0 IF VEHICLE IS ALREADY DRIVING)
    hrsLeft = (startDrive-time).total_seconds()/(60*60)
    chunksLeft = int(hrsLeft * chunks)
    # FIND TIME SLOTS WHERE VEHICLE WILL BE DRIVING
    hrsDriving = (endDrive - startDrive).total_seconds()/(60*60)
    chunksDriving = int(hrsDriving * chunks)

    # FIND BATTERY NEEDED IN UPCOMING DRIVE
    for i in range(chunksDriving):
        # GET VALUE FOR MILEAGE AND MPKW
        mileage = driveDataByCar[str(car % 4)].loc[(i + ind + chunksLeft) % drivingValues, 'mileage']
        mpkw = driveDataByCar[str(car % 4)].loc[(i + ind + chunksLeft) % drivingValues, 'mpkw']
        # CALCULATE RATE OF BATT DECREASE
        kwphr = mileage/mpkw
        # INCREMENT BATTERY NEEDED
        batteryNeeded += kwphr/chunks
    
    return batteryNeeded

# PREDICT BATTERY GAINED FROM A PARTICULAR CHARGING PERIOD
def battGainedFromCharge(startCharge, endCharge, depotStatus, availablePower):
    # DECLARE VARIABLE TO STORE BATTERY GAINED
    batteryGained = 0
    # GET DEPOT EVENTS WITHIN CHARGING CYCLE
    depotEvents = getDepotStatusRange((startCharge, endCharge), depotStatus)
    # APPEND THE LEAVING TIME OF VEHICLE
    depotEvents = depotEvents.append({"time": endCharge, "car": {}}, ignore_index=True)

    for row in range(0,len(depotEvents)-1):
        # GET DURATION BETWEEN EACH EVENT
        durationHrs = (depotEvents.loc[row+1, 'time'] - depotEvents.loc[row, 'time']).total_seconds()/(60*60)
        # GET THE NUMBER OF VEHICLES IN THE DEPOT BETWEEN EACH EVENT
        carsInDepot = len(depotEvents.loc[row, 'car'])

        # DIVIDE AVAILABLE POWER ACCORDINGLY IF THERE ARE MORE THAN ONE VEHICLE
        if carsInDepot > 1: batteryGained += (availablePower/carsInDepot)*durationHrs
        # IF NOT, ASSUME THAT THE ONE VEHICLE IS GIVEN MAX POWER OF 7KW/HR
        else:               batteryGained += 7*durationHrs

    return batteryGained

# PREDICT BATTERY NEEDED FOR EACH VEHICLE BASED ON ITS CURRENT STATE
def predictBatteryNeeded(time, carDataDF, driveDataByCar, ind, shiftsByCar, depotStatus, availablePower, predictive):
    # FOR EACH VEHICLE
    for car in range(len(carDataDF)):
        # GET BATTERY AND BATTERY SIZE
        batt = carDataDF.loc[car, 'battkW']
        battSize = carDataDF.loc[car, 'battSize']
        # SET BUFFER FOR BATTERY NEEDED
        battNeeded = battSize * 10/100

        # FOR VEHICLES DRIVING, LOOK INTO MOST IMMEDIATE DRIVING CYCLE
        if carDataDF.loc[car, 'inDepot'] == 0:
            # GET END OF SHIFT
            endDrive = readTime(carDataDF.loc[car, 'latestEndShift'])
            # PREDICT BATTERY NEEDED FOR CURRENT DRIVING SHIFT
            battNeeded += battNeededForShift(time, time, endDrive, driveDataByCar, ind, car)

        # FOR VEHICLES IN DEPOT, LOOK INTO NEXT 2 DRIVING CYCLES AND NEXT CHARGING CYCLE
        elif predictive:
            # SET START AND END DRIVE TIMES
            startDrive, endDrive = nextShift(car, carDataDF, shiftsByCar)
            nextStartDrive, nextEndDrive = nextNextShift(car, carDataDF, shiftsByCar)

            # PREDICT BATTERY NEEDED FOR THE MOST IMMEDIATE DRIVING SHIFT
            battNeeded += battNeededForShift(time, startDrive, endDrive, driveDataByCar, ind, car)
            # PREDICT BATTERY GAINED FROM THE NEXT CHARGING CYCLE
            # battNeeded -= battGainedFromCharge(endDrive, nextStartDrive, depotStatus, availablePower)
            # PREDICT BATTERY NEEDED FOR THE NEXT DRIVING SHIFT
            battNeeded += battNeededForShift(time, nextStartDrive, nextEndDrive, driveDataByCar, ind, car)/3

        # IF BATTERY NEEDED IS MORE THAN BATTERY SIZE, REQUIRE VEHICLE TO CHARGE TILL FULL
        if battNeeded > battSize: battNeeded = battSize
        # IF BATTERY ALREADY EXCEEDS BATTERY NEEDED, BATTERY NEEDED = BATTERY LEVEL
        if battNeeded < batt: battNeeded = batt
        # ASSIGN BATTERY NEEDED
        carDataDF.loc[car, 'battNeeded'] = battNeeded

    return carDataDF