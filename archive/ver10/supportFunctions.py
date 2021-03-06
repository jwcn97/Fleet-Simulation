import pandas as pd
import numpy as np
import datetime as dt
import time
from chunks import chunks

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

# FIND THE START AND END TIME OF NEXT SHIFT
def nextShift(carNum, carDataDF, shiftsByCar):
    # READ INDEX OF LATEST SHIFT AND INDEX OF THE LAST SHIFT
    shiftIndex = carDataDF.loc[carNum, 'shiftIndex']
    lastShiftIndex = len(shiftsByCar[str(carNum)])

    # IF NEXT SHIFT EXISTS, TAKE START TIME OF NEXT SHIFT
    if (shiftIndex + 1) < lastShiftIndex:
        nextStart = readTime(shiftsByCar[str(carNum)].loc[shiftIndex+1, 'startShift'])
        nextEnd = readTime(shiftsByCar[str(carNum)].loc[shiftIndex+1, 'endShift'])

    # IF SHIFT INDEX GOES BEYOND LAST SHIFT, TAKE ARBITRARY LEAVETIME
    else:
        lastStart = shiftsByCar[str(carNum)].loc[lastShiftIndex-1, 'startShift']
        lastDay = readTime(lastStart).date() + dt.timedelta(days=1)
        nextStart = readTime(str(lastDay) + " 23:59:59")
        nextEnd = nextStart
    
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


##############################
# MISC FUNCTIONS
##############################

# RETRIEVES COLUMN DATA FROM DATAFRAME
def getData(df, col):
    return df[col].values[0]

# GENERATE CARDATADF, CHARGEPTDF AND SIMULATIONDF
def generateDF(fleetData, carCols, cpCols):
    # initialise charge points data
    chargePt_data = []
    for (rate,quantity) in eval(getData(fleetData, 'chargePts')):
        # [maxRate, inUse]
        chargePt_data += [[rate,1]]*quantity

    # initialise car data
    car_data = []
    for (size,quantity) in eval(getData(fleetData, 'cars')):
        # [inDepot, battSize, battkW,
        #  lat, long, destLat, destLong, destIndex
        #  chargePt, chargeRate, totalCost, totalDistance, 
        #  rcCount, rcChunks,
        #  shiftIndex, latestStartShift, latestEndShift]
        car_data += [[1, size, size,
                    0.0, 0.0, np.nan, np.nan, 0,
                    np.nan, 0.0, 0.0, 0.0,
                    0, 0,
                    -1, np.nan, np.nan]]*quantity

    # initialise dataframes
    carDataDF = pd.DataFrame.from_records(car_data, columns=carCols)
    chargePtDF = pd.DataFrame.from_records(chargePt_data, columns=cpCols)
    
    # assign available charge points to cars
    for cp_id in range(len(chargePt_data)):
        carDataDF.loc[cp_id, 'chargePt'] = cp_id

    return carDataDF, chargePtDF

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

# PREDICT BATTERY NEEDED FOR DRIVING SHIFT
def predictBattNeeded(car, hrsLeft, battSize, driveDataByCar, ind):
    # READ TOTAL NUMBER OF DRIVING VALUES
    drivingValues = driveDataByCar['0'].shape[0]
    # SET BUFFER FOR BATTERY NEEDED
    battNeeded = battSize * 10/100
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
                # EXIT DEPOT
                carDataDF.loc[car,'inDepot'] = 0
                depot.remove(car)

                # REMOVE CHARGE PT IN CHARGE PT DF
                pt = carDataDF.loc[car,'chargePt']
                chargePtDF.loc[pt,'inUse'] = np.nan

                # REMOVE CHARGE PT IN CAR DATA DF
                carDataDF.loc[car,'chargePt'] = np.nan

                # UPDATE PARAMETERS IN CARDATADF
                carDataDF.loc[car,'rcChunks'] = 0
                carDataDF.loc[car,'chargeRate'] = 0
                carDataDF.loc[car,'shiftIndex'] = shiftIndex + 1
                carDataDF.loc[car,'latestStartShift'] = nextStartShift
                carDataDF.loc[car,'latestEndShift'] = nextEndShift

                # RECOGNISE AN EVENT HAS HAPPENED
                eventChange = "exitDepot"

    return eventChange, carDataDF, depot, chargePtDF

# READ CARS WITH FULL BATTERY INTO SIMULATION
def readFullBattCars(time, carDataDF, sim, eventChange):
    # SELECT VEHICLES IN THE DEPOT WITH FULL BATTERY
    chargeDF = carDataDF.loc[carDataDF['inDepot'] == 1]
    fullBattDF = chargeDF.loc[chargeDF['battkW'] == chargeDF['battSize']]

    # IF CAR IS FULLY CHARGED, LET CHARGE RATE = 0 IN TO-CHARGE DF
    for row in range(len(fullBattDF)):
        car = fullBattDF.index[row]
        carDataDF.loc[car, 'chargeRate'] = 0

    # ***** IF NEW CARS REACH FULL BATT, RECOGNISE EVENT *****
    # CREATE A SET FOR CARS THAT HAD FULL BATT IN PREVIOUS TIME
    prevSimData = sim[-len(carDataDF):]
    prevFullBattCars = set([rows[1] for rows in prevSimData if rows[4]=='full'])

    # CREATE A SET FOR CARS THAT CURRENTLY HAVE FULL BATT
    fullBattCars = set(fullBattDF.index.tolist())

    # IF NO. OF FULL BATT CARS >= PREVIOUS NO. OF FULL BATT CARS:
    if len(fullBattCars) >= len(prevFullBattCars):
        # AND IF INDEX OF FULL BATT CARS ARE DIFFERENT FROM PREVIOUS FULL BATT CARS:
        if fullBattCars != prevFullBattCars:
            # RECOGNISE AN EVENT HAS HAPPENED
            eventChange = "fullBatt"

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
def predictExtraCharging(time, pricesDF, depot, carDataDF, shiftsByCar, availablePower, eventChange):
    # DEFINE NEXT LOW TARIFF ZONE
    lowTariffStart, lowTariffEnd = nextLowTariffZone(time, pricesDF)

    # MAKE SURE ALL VEHICLES ARE IN DEPOT (TO TAKE INTO ACCOUNT BATTERY OF ALL VEHICLES)
    if len(depot) == len(carDataDF):
        # CALCULATE TOTAL BATTERY PROVIDED IN LOW TARIFF ZONE
        totalBattAvailable = (lowTariffEnd - lowTariffStart).total_seconds()*availablePower/(60*60)

        # ***** CALCULATE TOTAL BATTERY NEEDED IN LOW TARIFF ZONE *****
        totalBattLeft = 0
        for cars in range(0, len(depot)):
            carNum = depot[cars]

            # FIND THE START AND END TIME OF NEXT SHIFT
            nextStart, nextEnd = nextShift(carNum, carDataDF, shiftsByCar)

            # IF VEHICLE IS GOING TO BE IN DEPOT DURING LOW TARIFF ZONE
            if nextStart > lowTariffStart:
                # APPEND BATTERY LEFT TO TOTAL BATT LEFT
                totalBattLeft += carDataDF.loc[carNum,'battSize']-carDataDF.loc[carNum,'battkW']

        # IF TOTAL BATT LEFT IS MORE THAN THAT PROVIDED, ALLOCATE BUFFER TIME BEFORE LOW TARIFF START FOR VEHICLES TO CHARGE
        #   IF TIME == ALLOCATED TIME BEFORE LOW TARIFF START, CHARGE NOW (INSTEAD OF WAITING TILL LOW TARIFF ZONE)
        if totalBattLeft > totalBattAvailable:
            bufferHrs = (totalBattLeft - totalBattAvailable)/availablePower
            bufferSlots = int(np.ceil(bufferHrs*chunks))

            if time == lowTariffStart-dt.timedelta(hours=bufferSlots/chunks):
                eventChange = "extraCharging"

    return eventChange

