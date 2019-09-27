import pandas as pd
import numpy as np
import datetime as dt
import time
import sys

# number of chunks in an hour
# e.g. 3 chunks would divide the hour into 20-min shifts
chunks = 1

########################
# MISC FUNCTIONS
########################
def getChunks():
    return chunks

def readTime(ti):
    return dt.datetime.strptime(ti, "%H:%M").time()

def rereadTime(ti):
    reread = str(ti)
    if len(reread) == 5: read = dt.datetime.strptime(reread, "%H:%M")
    else:                read = dt.datetime.strptime(reread, "%H:%M:%S")
    return read

def incrementTime(ti):
    return (rereadTime(ti) + dt.timedelta(hours=1/chunks)).time()

def dfFunction(df):
    DF = df.set_index(['time','car'])
    DF = DF.T.stack().T
    DF = DF.iloc[6*chunks:,:].append(DF.iloc[0:6*chunks,:])
    return DF

######################
# FOR VISUALISATION
######################
def color(val):
    color = 'green' if val >= 0 else 'red'
    return 'color: %s' % color

def background(val):
    if val > 0: color = '#75fa7e'
    elif val == 0: color = '#adfc83'
    elif val < 0: color = '#fab9b9'
    return 'background-color: %s' % color

def markEvents(val):
    if val == 'idle': color = '#adfc83'
    elif val == 'charge': color = '#75fa7e'
    elif val == 'drive': color = '#fab9b9'
    elif val == 'RC': color = 'red'
    else: color = None
    return 'background-color: %s' % color

def styleDF(df):
    DF = df.style.\
        applymap(color, subset=['charge_rate']).\
        applymap(background, subset = ['charge_rate']).\
        applymap(markEvents, subset = ['event'])
    return DF

###############################
# DECREASE BATT DURING SHIFT
###############################
def decreaseBatt(carDataDF, shiftsByCar, time, rcCount, simulationDF, mph, mpkw):
    for car in range(len(carDataDF)):
        # READ DATA FOR EVERY ROW IN CarDataDF
        batt = carDataDF.loc[car, 'battPerc']
        isC = carDataDF.loc[car, 'inDepot']
        battSize = carDataDF.loc[car, 'battSize']
        # CALCULATE RATE OF BATT DECREASE
#         kwphr = np.random.choice([mph-3,mph+3])/np.random.choice([mpkw-1,mpkw+1])
        kwphr = mph/mpkw

        for b in range(0,len(shiftsByCar[str(car)])):
            startS = readTime(shiftsByCar[str(car)].loc[b, 'startShift'])
            endS = readTime(shiftsByCar[str(car)].loc[b, 'endShift'])

            # IF SHIFT DOESN'T RUN OVER MIDNIGHT
            if startS < endS:
                # DECREASE BATT DURING SHIFT
                if time >= startS and time < endS:
                    batt = carDataDF.loc[car,'battPerc']
                    simulationDF = simulationDF.append({
                        'time': time,
                        'car': car,
                        'charge_rate': round(-kwphr, 2),
                        'batt': round(batt, 2),
                        'event': 'drive' if batt-kwphr/chunks>0 else 'RC'
                    }, ignore_index=True)
                    batt -= kwphr/chunks

            # IF SHIFT RUNS OVER MIDNIGHT
            else:
                # SELECT NON-SHIFT TIME
                saveVal = startS
                startS = endS
                endS = saveVal

                # DECREASE BATT IF NOT DURING NON-SHIFT
                if time >= startS and time < endS: continue
                else:
                    batt = carDataDF.loc[car,'battPerc']
                    simulationDF = simulationDF.append({
                        'time': time,
                        'car': car,
                        'charge_rate': round(-kwphr, 2),
                        'batt': round(batt, 2),
                        'event': 'drive' if batt-kwphr/chunks>0 else 'RC'
                    }, ignore_index=True)
                    batt -= kwphr/chunks

        # RAPID CHARGE OUTSIDE CHARGE CENTRE IF VEHICLE HAS NO BATTERY
        if batt <= 0:
            batt = carDataDF.loc[car,'battSize']*9/10
            rcCount += 1
            # print("car:" + str(car) + " rapid charge at " + str(time))

        # ASSIGN BATTERY
        carDataDF.loc[car,'battPerc'] = batt

    return carDataDF, time, rcCount, simulationDF

#################################################################
# WHEN SHIFT STARTS: inDepot = 0, REMOVE FROM CHARGE CENTRE
# WHEN SHIFT ENDS: inDepot = 1, ENTER CHARGE CENTRE
#################################################################
def inOutDepot(carDataDF, shiftsByCar, time, depot, simulationDF, chargePtDF):
    for car in range(0, len(carDataDF)):
        for shifts in range(0, len(shiftsByCar[str(car)])):
            # READ DATA FOR EVERY ROW IN CarDataDF
            startS = readTime(shiftsByCar[str(car)].loc[shifts, 'startShift'])
            endS = readTime(shiftsByCar[str(car)].loc[shifts, 'endShift'])

            if time == startS:                      # exiting depot
                carDataDF.loc[car,'inDepot'] = 0
                depot.remove(car)

                # REMOVE CHARGE PT
                pt = carDataDF.loc[car,'chargePt']
                if not np.isnan(pt):
                    chargePtDF.loc[pt,'inUse'] = np.nan
                    # print("remove charge point "+str(pt))

                carDataDF.loc[car,'chargePt'] = np.nan

            if time == endS:                        # entering depot
                carDataDF.loc[car,'inDepot'] = 1
                depot.append(car)

    # SELECT IDLE VEHICLES
    chargeDF = carDataDF.loc[carDataDF['inDepot'] == 1]
    idleDF = chargeDF.loc[chargeDF['battPerc'] == chargeDF['battSize']]
    if len(idleDF) >= 1:
        # LABEL IDLE CARS IN SIMULATION
        for cars in range(len(idleDF)):
            num = idleDF.index[cars]
            batt = carDataDF.loc[num,'battPerc']
            simulationDF = simulationDF.append({
                'time': time,
                'car': num,
                'charge_rate': 0,
                'batt': round(batt, 2),
                'event': 'idle'
            }, ignore_index=True)

    return carDataDF, time, depot, simulationDF, chargePtDF

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
#         print("car "+str(car)+" plugged into CP "+str(pt))
        availablePts = availablePts.drop(pt, axis=0)

        # UPDATE chargePtDF and carDataDF
        chargePtDF.loc[pt, 'inUse'] = 1
        carDataDF.loc[car, 'chargePt'] = pt

    # IF CAR HAS A CHARGE PT pt = CHARGE PT, ELSE pt = np.nan
    else:
        pt = chargePt
#         print("car "+str(car)+" has charge pt "+str(pt))

    return pt, carDataDF, chargePtDF

###################################
# CHARGE VEHICLE FOR ONE HOUR
###################################
def charge(carDataDF, carNum, chargeRate, simulationDF, time, chargePtDF):
    batt = carDataDF.loc[carNum,'battPerc']
    battSize = carDataDF.loc[carNum,'battSize']
    
    chargeRate = chargeRate/chunks
    chargeRate = (battSize-batt) if (chargeRate > battSize-batt) else chargeRate
    
    simulationDF = simulationDF.append({
        'time': time,
        'car': carNum,
        'charge_rate': round(chargeRate, 2),
        'batt': round(batt, 2),
        'event': 'charge' if chargeRate > 0 else 'idle'
    }, ignore_index=True)
#     print("CHARGE")

    # INCREASE BATT PERCENTAGE ACCORDING TO CHARGE RATE
    batt += chargeRate
    batt = battSize if batt >= battSize else batt
    carDataDF.loc[carNum, 'battPerc'] = batt

    return carDataDF, simulationDF, chargePtDF



#################################################################################################################################
# CORE FUNCTIONS

#################################
# INCREASE BATT DURING CHARGE
#################################
def dumbCharge(carDataDF, depot, shiftsByCar, time, chargeCapacity, simulationDF, chargePtDF):
    # SELECT CARS IN DEPOT WITH BATT < 100
    chargeDF = carDataDF.loc[carDataDF['inDepot'] == 1]
    chargeDF = chargeDF.loc[chargeDF['battPerc'] < chargeDF['battSize']]

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
            carDataDF, simulationDF, chargePtDF = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF)

    return carDataDF, simulationDF, chargePtDF

######################################
# INCREASE BATT DURING CHARGE (LEAVETIME)
######################################
def smartCharge_leavetime(carDataDF, depot, shiftsByCar, time, chargeCapacity, simulationDF, chargePtDF):
    # IF THERE ARE CARS IN THE CHARGE CENTRE
    if len(depot) > 0:
        listRows = []
        # FIND THE TIMES WHEN CARS LEAVE THE CHARGE CENTRE
        for cars in range(0, len(depot)):
            f = depot[cars]
            leaveTime = readTime("23:59")
            for g in range(0, len(shiftsByCar[str(f)])):
                startTime = readTime(shiftsByCar[str(f)].loc[g, 'startShift'])
                if startTime > time and startTime < leaveTime:
                    leaveTime = startTime

            if leaveTime == readTime("23:59"):
                leaveTime = shiftsByCar[str(f)].loc[0,'startShift']

            hrsLeft = abs(rereadTime(leaveTime) - rereadTime(time))
            listRows.append([f, hrsLeft])

        leaveTimes = pd.DataFrame.from_records(listRows, columns=['car','hrsLeft'])
        leaveTimes = leaveTimes.sort_values(by=['hrsLeft'])
        leaveTimes = leaveTimes.reset_index(drop=True)

        # CHARGE CARS IN ORDER ON AVAILABLE CHARGE PTS
        for h in range(0, len(leaveTimes)):
            car = leaveTimes.loc[h, 'car']
            batt = carDataDF.loc[car, 'battPerc']
            batt_size = carDataDF.loc[car, 'battSize']
            chargePt = carDataDF.loc[car, 'chargePt']

            # IF CAR BATT IS NOT 100%, CHARGE CAR
            if batt < batt_size:
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
                        
                # CHARGE
                carDataDF, simulationDF, chargePtDF = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF)
                chargeCapacity -= chargeRate

    return carDataDF, simulationDF, chargePtDF

######################################
# INCREASE BATT DURING CHARGE (BATT)
######################################
def smartCharge_batt(carDataDF, depot, shiftsByCar, time, chargeCapacity, simulationDF, chargePtDF):
    # IF THERE ARE CARS IN THE CHARGE CENTRE
    if len(depot) >= 1:
        listRows = []
        # FIND THE TIMES WHEN CARS LEAVE THE CHARGE CENTRE
        for cars in range(0, len(depot)):
            f = depot[cars]

            battLeft = abs(carDataDF.loc[f,'battSize']-carDataDF.loc[f,'battPerc'])
            listRows.append([f, battLeft])

        leaveTimes = pd.DataFrame.from_records(listRows, columns=['car','battLeft'])
        leaveTimes = leaveTimes.sort_values(by=['battLeft'], ascending=False)
        leaveTimes = leaveTimes.reset_index(drop=True)

        # CHARGE CARS IN ORDER ON AVAILABLE CHARGE PTS
        for h in range(0, len(leaveTimes)):
            car = leaveTimes.loc[h, 'car']
            batt = carDataDF.loc[car, 'battPerc']
            batt_size = carDataDF.loc[car, 'battSize']
            chargePt = carDataDF.loc[car, 'chargePt']

            # IF CAR BATT IS NOT 100%, CHARGE CAR
            if batt < batt_size:
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
                        
                # CHARGE
                carDataDF, simulationDF, chargePtDF = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF)
                chargeCapacity -= chargeRate

    return carDataDF, simulationDF, chargePtDF


############################################
# INCREASE BATT DURING CHARGE (SUPER SMART)
############################################
def superSmartCharge(carDataDF, chargeCen, shiftsByCar, time, chargeCapacity, simulationDF, chargePtDF):
    # IF THERE ARE CARS IN THE CHARGE CENTRE
    if len(chargeCen) >= 1:
        listRows = []
        # FIND THE TIMES WHEN CARS LEAVE THE CHARGE CENTRE
        for cars in range(0, len(chargeCen)):
            f = chargeCen[cars]
            leaveTime = readTime("23:59")
            for g in range(0, len(shiftsByCar[str(f)])):
                startTime = readTime(shiftsByCar[str(f)].loc[g, 'startShift'])
                if startTime > time and startTime < leaveTime:
                    leaveTime = startTime

            if leaveTime == readTime("23:59"):
                leaveTime = shiftsByCar[str(f)].loc[0,'startShift']

            hrsLeft = abs(rereadTime(leaveTime) - rereadTime(time))
            battLeft = abs(carDataDF.loc[f,'battSize']-carDataDF.loc[f,'battPerc'])
            listRows.append([f, battLeft/hrsLeft.total_seconds(), battLeft])

        leaveTimes = pd.DataFrame.from_records(listRows, columns=['car','priority','battLeft'])
        leaveTimes = leaveTimes.sort_values(by=['priority'], ascending=False)
        prioritySum = sum(leaveTimes.priority)

        # CHARGE CARS
        for h in range(0, len(leaveTimes)):
            car = leaveTimes.loc[h, 'car']
            batt = carDataDF.loc[car, 'battPerc']
            batt_size = carDataDF.loc[car, 'battSize']
            batt_left = leaveTimes.loc[h, 'battLeft']
            priority = leaveTimes.loc[h, 'priority']

            # IF CAR BATT IS NOT 100%, CHARGE CAR
            if batt < batt_size:
                # ALLOCATE CHARGE PT IF CAR DOESN'T HAVE ONE
                pt, carDataDF, chargePtDF = findChargePt(carDataDF, car, chargePtDF)
                chargeRate = 0

                # IF CAR HAS A VALID CHARGE PT
                if not np.isnan(pt):
                    # READ MAX RATE
                    maxRate = chargePtDF.loc[pt, 'maxRate']

                    # CALCULATE CHARGE RATE
                    chargeRate = (priority/prioritySum)*chargeCapacity

                    # IF CHARGE RATE EXCEEDS MAX RATE
                    if chargeRate > maxRate: chargeRate = maxRate
                    # IF CHARGE RATE EXCEEDS CHARGE NEEDED
                    if chargeRate > batt_left: chargeRate = batt_left

                # CHARGE
                carDataDF, simulationDF, chargePtDF = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF)
                chargeCapacity -= chargeRate
                prioritySum -= priority

    return carDataDF, simulationDF, chargePtDF



#################################################################################################################################

simulations = {
    'dumbCharge': dumbCharge,
    'smartCharge_leavetime': smartCharge_leavetime,
    'smartCharge_batt': smartCharge_batt,
    'superSmartCharge': superSmartCharge
}

def runSimulation(startTime, runTime, 
                  carData, car_cols, carShifts, 
                  chargePtData, cp_cols, chargeCapacity, 
                  sim_cols, mph, mpkw, algo):
    shiftsByCar = {}                                                # Set dictionary name as 'shiftsByCar'
    for cars in range(0,len(carData)):                              # For every keys of the car:
        shiftsDF = pd.DataFrame(carShifts[cars], columns=["startShift","endShift"])
        shiftsDF = shiftsDF.sort_values(by=['startShift'])
        shiftsDF = shiftsDF.reset_index(drop=True)
        shiftsByCar['%s' % cars] = shiftsDF                             # The value = an empty list
    
    depot = []
    carDataDF = pd.DataFrame.from_records(carData, columns=car_cols)
    chargePtDF = pd.DataFrame.from_records(chargePtData, columns=cp_cols)
    simulationDF = pd.DataFrame(columns=sim_cols)
    for car in range(0, len(carDataDF)):
        if carDataDF.loc[car,'inDepot']: depot.append(car)

    rcCount = 0             # INITIALISE A COUNTER FOR RAPID CHARGES
    time = startTime        # CHOOSE START TIME

    for i in range(0, runTime*chunks):
    #     print(str(time))
        carDataDF, time, depot, simulationDF, chargePtD = inOutDepot(carDataDF, shiftsByCar, time, depot, simulationDF, chargePtDF)
        carDataDF, time, rcCount, simulationDF = decreaseBatt(carDataDF, shiftsByCar, time, rcCount, simulationDF, mph, mpkw)
        carDataDF, simulationDF, chargePtDF = simulations[algo](carDataDF, depot, shiftsByCar, time, chargeCapacity, simulationDF, chargePtDF)
        time = incrementTime(time)
    # print("No. of rapid charges: " + str(rcCount))
    sim = dfFunction(simulationDF)
    return styleDF(sim), simulationDF, rcCount    # second dataframe, 'sim', is for animation purposes