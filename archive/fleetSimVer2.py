#!/usr/bin/env python
# coding: utf-8

# %%

import pandas as pd
import numpy as np
import sys
import datetime as dt
import time

########################
# MISC FUNCTIONS
########################
def readTime(ti):
    return dt.datetime.strptime(ti, "%H:%M").time()

def rereadTime(ti):
    reread = str(ti)
    if len(reread) == 5: read = dt.datetime.strptime(reread, "%H:%M")
    else:                read = dt.datetime.strptime(reread, "%H:%M:%S")
    return read

def incrementTime(ti):
    return (rereadTime(ti) + dt.timedelta(hours=1)).time()

######################
# FOR VISUALISATION
######################
def color(val):
    color = 'green' if val > 0 else 'red'
    return 'color: %s' % color

def background(val):
    color = '#75fa7e' if val > 0 else '#fab9b9'
    return 'background-color: %s' % color

def markEvents(val):
    if val == 'idle': color = '#fcfa6f'
    elif val == 'charge': color = '#75fa7e'
    elif val == 'drive': color = '#fab9b9'
    else: color = None
    return 'background-color: %s' % color

# %%
# ### Battery Functions
###############################
# DECREASE BATT DURING SHIFT
###############################
def decreaseBatt(carDataDF, shiftsByCar, time, rcCount, simulationDF):
    for car in range(len(carDataDF)):
        # READ DATA FOR EVERY ROW IN CarDataDF
        batt = carDataDF.loc[car, 'battPerc']
        isC = carDataDF.loc[car, 'inDepot']
        battSize = carDataDF.loc[car, 'battSize']
        # CALCULATE RATE OF BATT DECREASE
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
                        'charge_rate': 0,
                        'batt': round(batt),
                        'event': 'drive'
                    }, ignore_index=True)
                    batt -= kwphr

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
                        'charge_rate': 0,
                        'batt': round(batt),
                        'event': 'drive'
                    }, ignore_index=True)
                    batt -= kwphr

        # RAPID CHARGE OUTSIDE CHARGE CENTRE IF VEHICLE HAS NO BATTERY
        if batt <= 0:
            batt = 27
            rcCount += 1
            print("car:" + str(car) + " rapid charge at " + str(time))

        # ASSIGN BATTERY
        carDataDF.loc[car,'battPerc'] = batt

    return carDataDF, time, rcCount, simulationDF

# %%
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
        print("car "+str(car)+" plugged into CP "+str(pt))
        availablePts = availablePts.drop(pt, axis=0)

        # UPDATE chargePtDF and carDataDF
        chargePtDF.loc[pt, 'inUse'] = 1
        carDataDF.loc[car, 'chargePt'] = pt

    # IF CAR HAS A CHARGE PT pt = CHARGE PT, ELSE pt = np.nan
    else:
        pt = chargePt
        print("car "+str(car)+" has charge pt "+str(pt))

    return pt, carDataDF, chargePtDF

# %%
###################################
# CHARGE VEHICLE FOR ONE HOUR
###################################
def charge(carDataDF, carNum, chargeRate, simulationDF, time, chargePtDF):
    batt = carDataDF.loc[carNum,'battPerc']
    battSize = carDataDF.loc[carNum,'battSize']
    simulationDF = simulationDF.append({
        'time': time,
        'car': carNum,
        'charge_rate': round(chargeRate),
        'batt': round(batt),
        'event': 'charge'
    }, ignore_index=True)
    print("CHARGE")


    # INCREASE BATT PERCENTAGE ACCORDING TO CHARGE RATE
    batt += chargeRate
    batt = battSize if batt >= battSize else batt
    carDataDF.loc[carNum, 'battPerc'] = batt

    return carDataDF, simulationDF, chargePtDF

# %%
# ### Core Functions
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

            if time == startS:                      # exiting centre
                carDataDF.loc[car,'inDepot'] = 0
                depot.remove(car)

                # REMOVE CHARGE PT
                pt = carDataDF.loc[car,'chargePt']
                if not np.isnan(pt):
                    chargePtDF.loc[pt,'inUse'] = np.nan
                    print("remove charge point "+str(pt))

                carDataDF.loc[car,'chargePt'] = np.nan

            if time == endS:                        # entering centre
                carDataDF.loc[car,'inDepot'] = 1
                depot.append(car)

    # SELECT IDLE VEHICLES
    chargeDF = carDataDF.loc[carDataDF['inDepot'] == 1]
    idleDF = chargeDF.loc[chargeDF['battPerc'] == 30]
    if len(idleDF) >= 1:
        # LABEL IDLE CARS IN SIMULATION
        for cars in range(len(idleDF)):
            num = idleDF.index[cars]
            simulationDF = simulationDF.append({
                'time': time,
                'car': num,
                'charge_rate': 0,
                'batt': round(carDataDF.loc[num,'battPerc']),
                'event': 'idle'
            }, ignore_index=True)

    return carDataDF, time, depot, simulationDF, chargePtDF

# %%
#################################
# INCREASE BATT DURING CHARGE
#################################
def dumbCharge(carDataDF, depot, chargeCapacity, simulationDF, chargePtDF):
    # SELECT CARS IN DEPOT WITH BATT < 100
    chargeDF = carDataDF.loc[carDataDF['inDepot'] == 1]
    chargeDF = chargeDF.loc[chargeDF['battPerc'] < 30]

    # IF THERE ARE CARS THAT REQUIRE CHARGING
    if len(chargeDF) > 0:

        # CALCULATE CHARGE RATE
        if len(chargeDF) <= len(chargePtDF):
            chargeRate = chargeCapacity/len(chargeDF)
        else:
            chargeRate = chargeCapacity/len(chargePtDF)

        # CHARGE SELECTED CARS IN DEPOT
        for cars in range(len(chargeDF)):
            car = chargeDF.index[cars]
            # ALLOCATE CHARGE PT IF CAR DOESN'T HAVE ONE
            pt, carDataDF, chargePtDF = findChargePt(carDataDF, car, chargePtDF)

            # IF CAR HAS A VALID CHARGE PT
            if not np.isnan(pt):
                # LIMIT CHARGE RATE TO MAX RATE OF CHARGE PT
                maxRatePt = chargePtDF.loc[pt, 'maxRate']
                if maxRatePt < chargeRate:
                    chargeRate = maxRatePt

                # CHARGE
                carDataDF, simulationDF, chargePtDF = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF)

    return carDataDF, simulationDF, chargePtDF

# %%
######################################
# INCREASE BATT DURING CHARGE (LEAVETIME)
######################################
def smartCharge_leavetime(carDataDF, depot, shiftsByCar, time, chargeCapacity, simulationDF, chargePtDF):
    # IF THERE ARE CARS IN THE CHARGE CENTRE
    if len(depot) >= 1:
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

                # IF CAR HAS A VALID CHARGE PT
                if not np.isnan(pt):
                    # READ MAX RATE
                    maxRate = chargePtDF.loc[pt, 'maxRate']
                    energyLeft = chargeCapacity - maxRate

                    # IF ENOUGH CAPACITY FOR FOR MAX RATE, CHARGE CAR AT MAX
                    if energyLeft >= 0:
                        chargeRate = maxRate

                        # CHARGE
                        carDataDF, simulationDF, chargePtDF = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF)
                        chargeCapacity -= chargeRate

                    # IF NOT ENOUGH FOR MAX RATE, CHARGE USING REMAINING POWER
                    elif energyLeft < 0 and energyLeft > -maxRate:
                        chargeRate = chargeCapacity

                        # CHARGE
                        carDataDF, simulationDF, chargePtDF = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF)
                        chargeCapacity -= chargeRate

                    else:
                        # if vehicle is plugged in but not allocated any charge
                        simulationDF = simulationDF.append({
                            'time': time,
                            'car': car,
                            'charge_rate': 0,
                            'batt': round(batt),
                            'event': 'hold'
                        }, ignore_index=True)

    return carDataDF, simulationDF, chargePtDF

# %%
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

                # IF CAR HAS A VALID CHARGE PT
                if not np.isnan(pt):
                    # TAKE CHARGE RATE AS MAX RATE OF CHARGE PT
                    maxRate = chargePtDF.loc[pt, 'maxRate']
                    energyLeft = chargeCapacity - maxRate

                    # IF ENOUGH CAPACITY FOR MAX RATE, CHARGE CAR AT MAX
                    if energyLeft >= 0:
                        chargeRate = maxRate

                        # CHARGE
                        carDataDF, simulationDF, chargePtDF = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF)
                        chargeCapacity -= chargeRate

                    # IF NOT ENOUGH FOR MAX RATE,  CHARGE USING REMAINING POWER
                    elif energyLeft < 0 and energyLeft > -maxRate:
                        chargeRate = chargeCapacity

                        # CHARGE
                        carDataDF, simulationDF, chargePtDF = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF)
                        chargeCapacity -= chargeRate

                    else:
                        # if vehicle is plugged in but not allocated any charge
                        simulationDF = simulationDF.append({
                            'time': time,
                            'car': car,
                            'charge_rate': 0,
                            'batt': round(batt),
                            'event': 'hold'
                        }, ignore_index=True)

    return carDataDF, simulationDF, chargePtDF

# %%
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

                    chargeCapacity -= chargeRate
                    prioritySum -= priority
                    carDataDF, simulationDF, chargePtDF = charge(carDataDF, car, chargeRate, simulationDF, time, chargePtDF)

    return carDataDF, simulationDF, chargePtDF

# %%
# ### EXAMPLE SCENARIOS

######################## DEPO ############################
chargeCapacity = 18             # SET MAX AVAILABLE POWER IN CENTRE (kW/hr)

######################## DRIVING ############################
mpkw = 4                        # SET AVERAGE MILES PER kW THAT WILL DETERMINE RATE OF BATT DECREASE
mph = 16                        # SET AVERAGE MILES PER HR COVERED
runTime = 24                    # CHOOSE RUNTIME (HRS)

# carData = [[30, 1, 30], [30, 1, 30], [30, 1, 30], [30, 1, 30]]

# filename = "work" # 1 vs 0
# carShifts = [[["06:00", "11:00"], ["14:00", "20:00"]],
#              [["06:00", "13:00"], ["17:00", "23:00"]],
#              [["07:00", "12:00"], ["20:00", "00:00"]],
#              [["08:00", "14:00"], ["18:00", "23:00"]]]

# filename = "meal_delivery" # 1 vs 0
# carShifts = [[["10:00", "14:00"], ["17:00", "00:00"]],
#              [["11:00", "14:00"], ["18:00", "22:00"]],
#              [["10:00", "14:00"], ["19:00", "23:00"]],
#              [["11:00", "14:00"], ["18:00", "00:00"]]]

# filename = "tourism" # 4 vs 4
# carShifts = [[["10:00", "18:00"]],
#              [["10:00", "19:00"]],
#              [["09:00", "19:00"]],
#              [["10:00", "20:00"]]]

# filename = "test" # 3 vs 1
# carShifts = [[["06:00", "12:00"], ["15:00", "21:00"]],
#              [["06:00", "14:00"], ["17:00", "23:00"]],
#              [["07:00", "14:00"], ["20:00", "01:00"]],
#              [["08:00", "15:00"], ["18:00", "23:00"]]]

# filename = "frequent" # frequent shifts # 3 vs 3
# carShifts = [[["07:00", "13:00"], ["14:00", "18:00"], ["20:00", "22:00"]],
#              [["06:00", "12:00"], ["13:00", "15:00"], ["17:00", "20:00"]],
#              [["06:00", "14:00"], ["16:00", "18:00"], ["20:00", "00:00"]],
#              [["07:00", "13:00"], ["14:00", "18:00"], ["20:00", "23:00"]]]

# filename = "first_shift_same" # first shift is all the same, vary second shift to see how smart system perform # 2 vs 1
# carShifts = [[["07:00", "14:00"], ["20:00", "22:00"]],
#              [["07:00", "14:00"], ["17:00", "20:00"]],
#              [["07:00", "14:00"], ["20:00", "00:00"]],
#              [["07:00", "14:00"], ["18:00", "23:00"]]]

# filename = "second_shift_same" # second shift is all the same, vary first shift to see how smart system perform # 3 vs 2
# carShifts = [[["06:00", "11:00"], ["15:00", "22:00"]],
#              [["08:00", "13:00"], ["15:00", "22:00"]],
#              [["07:00", "11:00"], ["15:00", "22:00"]],
#              [["07:00", "12:00"], ["15:00", "22:00"]]]

carData = [[30, 1, 30, 0], [30, 1, 30, 1], [30, 1, 30, 2], [30, 1, 30, 3],
           [30, 1, 30, 4], [30, 1, 30, 5], [30, 1, 30, 6], [30, 1, 30, 7]]

chargePtData = [[7, 1], [7, 1], [7, 1], [7, 1],
                [7, 1], [7, 1], [7, 1], [7, 1]]

# filename = "8_cars_work" # 6 vs 4
# carShifts = [[["06:00", "11:00"], ["14:00", "20:00"]],
#              [["06:00", "13:00"], ["17:00", "23:00"]],
#              [["07:00", "12:00"], ["20:00", "00:00"]],
#              [["08:00", "14:00"], ["18:00", "23:00"]],
#              [["06:00", "11:00"], ["14:00", "20:00"]],
#              [["06:00", "13:00"], ["17:00", "23:00"]],
#              [["07:00", "12:00"], ["20:00", "00:00"]],
#              [["08:00", "14:00"], ["18:00", "23:00"]]]

# filename = "8_cars_test" # 6 vs 7
# carShifts = [[["06:00", "12:00"], ["15:00", "21:00"]],
#              [["06:00", "14:00"], ["17:00", "23:00"]],
#              [["07:00", "14:00"], ["20:00", "01:00"]],
#              [["08:00", "15:00"], ["18:00", "23:00"]],
#              [["06:00", "12:00"], ["15:00", "21:00"]],
#              [["06:00", "14:00"], ["17:00", "23:00"]],
#              [["07:00", "14:00"], ["20:00", "01:00"]],
#              [["08:00", "15:00"], ["18:00", "23:00"]]]

# filename = "8_cars_frequent"
# carShifts = [[["07:00", "13:00"], ["16:00", "20:00"], ["22:00", "00:00"]],
#              [["06:00", "12:00"], ["15:00", "19:00"], ["21:00", "00:00"]],
#              [["06:00", "13:00"], ["18:00", "20:00"], ["22:00", "02:00"]],
#              [["07:00", "13:00"], ["16:00", "20:00"], ["22:00", "01:00"]],
#              [["07:00", "13:00"], ["16:00", "20:00"], ["22:00", "00:00"]],
#              [["06:00", "12:00"], ["15:00", "19:00"], ["21:00", "00:00"]],
#              [["06:00", "13:00"], ["18:00", "20:00"], ["22:00", "02:00"]],
#              [["07:00", "13:00"], ["16:00", "20:00"], ["22:00", "01:00"]]]

filename = "8_cars_first_shift_same"
carShifts = [[["07:00", "14:00"], ["20:00", "22:00"]],
             [["07:00", "14:00"], ["17:00", "20:00"]],
             [["07:00", "14:00"], ["20:00", "00:00"]],
             [["07:00", "14:00"], ["18:00", "23:00"]],
             [["07:00", "14:00"], ["20:00", "22:00"]],
             [["07:00", "14:00"], ["17:00", "20:00"]],
             [["07:00", "14:00"], ["20:00", "00:00"]],
             [["07:00", "14:00"], ["18:00", "23:00"]]]

shiftsByCar = {}                                                # Set dictionary name as 'shiftsByCar'
for cars in range(0,len(carData)):                              # For every keys of the car:
    shiftsDF = pd.DataFrame(carShifts[cars], columns=["startShift","endShift"])
    shiftsDF = shiftsDF.sort_values(by=['startShift'])
    shiftsDF = shiftsDF.reset_index(drop=True)
    shiftsByCar['%s' % cars] = shiftsDF                             # The value = an empty list

# writer = pd.ExcelWriter("scenario/" + filename + ".xlsx")

# %%

# ### SMART CHARGING (LEAVETIME)

######################## DEPO ############################
depot = []
carDataDF = pd.DataFrame.from_records(carData, columns=["battPerc","inDepot","battSize","chargePt"])
chargePtDF = pd.DataFrame.from_records(chargePtData, columns=["maxRate","inUse"])
for car in range(0, len(carDataDF)):
    if carDataDF.loc[car,'inDepot']: depot.append(car)

######################## SIMULATION #############################
rcCount = 0                     # INITIALISE A COUNTER FOR RAPID CHARGES
time = readTime("06:00")        # CHOOSE START TIME
simulationDF = pd.DataFrame(columns=['time','car','charge_rate','batt','event'])

for i in range(0, runTime):
    print(str(time))
    carDataDF, time, depot, simulationDF, chargePtDF = inOutDepot(carDataDF, shiftsByCar, time, depot, simulationDF, chargePtDF)
    carDataDF, time, rcCount, simulationDF = decreaseBatt(carDataDF, shiftsByCar, time, rcCount, simulationDF)
    carDataDF, simulationDF, chargePtDF = smartCharge_leavetime(carDataDF, depot, shiftsByCar, time, chargeCapacity, simulationDF, chargePtDF)
    time = incrementTime(time)
chargePtDF
print("No. of rapid charges: " + str(rcCount))
smartDF = simulationDF.set_index(['time','car'])
smartDF = smartDF.T.stack().T
smartDF = smartDF.iloc[6:,:].append(smartDF.iloc[0:6,:])
smartDF = smartDF.style.    applymap(color, subset=['charge_rate']).    applymap(background, subset = ['charge_rate']).    applymap(markEvents, subset = ['event']).    set_caption('SMART CHARGING (LEAVETIME)')
# smartDF.to_excel(writer, sheet_name="smart")
# writer.save()
smartDF

# %%

# ### DUMB CHARGING

######################## DEPO ############################
depot = []
carDataDF = pd.DataFrame.from_records(carData, columns=["battPerc","inDepot","battSize","chargePt"])
chargePtDF = pd.DataFrame.from_records(chargePtData, columns=["maxRate","inUse"])
for car in range(0, len(carDataDF)):
    if carDataDF.loc[car,'inDepot']: depot.append(car)

######################## SIMULATION #############################
rcCount = 0                     # INITIALISE A COUNTER FOR RAPID CHARGES
time = readTime("06:00")        # CHOOSE START TIME
simulationDF = pd.DataFrame(columns=['time','car','charge_rate','batt','event'])

for i in range(0, runTime):
    carDataDF, time, depot, simulationDF, chargePtDF = inOutDepot(carDataDF, shiftsByCar, time, depot, simulationDF, chargePtDF)
    carDataDF, time, rcCount, simulationDF = decreaseBatt(carDataDF, shiftsByCar, time, rcCount, simulationDF)
    carDataDF, simulationDF, chargePtDF = dumbCharge(carDataDF, depot, chargeCapacity, simulationDF, chargePtDF)
    time = incrementTime(time)

print("No. of rapid charges: " + str(rcCount))
dumbDF = simulationDF.set_index(['time','car'])
dumbDF = dumbDF.T.stack().T
# dumbDF = dumbDF.iloc[6:,:].append(dumbDF.iloc[0:6,:])
dumbDF = dumbDF.style.    applymap(color, subset=['charge_rate']).    applymap(background, subset = ['charge_rate']).    applymap(markEvents, subset = ['event']).    set_caption('DUMB CHARGING')
# dumbDF.to_excel(writer, sheet_name="dumb")
dumbDF

# %%

# ### SMART CHARGING (BATT)

######################## DEPO ############################
depot = []
carDataDF = pd.DataFrame.from_records(carData, columns=["battPerc","inDepot","battSize","chargePt"])
chargePtDF = pd.DataFrame.from_records(chargePtData, columns=["maxRate","inUse"])
for car in range(0, len(carDataDF)):
    if carDataDF.loc[car,'inDepot']: depot.append(car)

######################## SIMULATION #############################
rcCount = 0                     # INITIALISE A COUNTER FOR RAPID CHARGES
time = readTime("06:00")        # CHOOSE START TIME
simulationDF = pd.DataFrame(columns=['time','car','charge_rate','batt','event'])

for i in range(0, runTime):
    print(str(time))
    carDataDF, time, depot, simulationDF, chargePtDF = inOutDepot(carDataDF, shiftsByCar, time, depot, simulationDF, chargePtDF)
    carDataDF, time, rcCount, simulationDF = decreaseBatt(carDataDF, shiftsByCar, time, rcCount, simulationDF)
    carDataDF, simulationDF, chargePtDF = smartCharge_batt(carDataDF, depot, shiftsByCar, time, chargeCapacity, simulationDF, chargePtDF)
    time = incrementTime(time)

print("No. of rapid charges: " + str(rcCount))
smartDF = simulationDF.set_index(['time','car'])
smartDF = smartDF.T.stack().T
smartDF = smartDF.iloc[6:,:].append(smartDF.iloc[0:6,:])
smartDF = smartDF.style.    applymap(color, subset=['charge_rate']).    applymap(background, subset = ['charge_rate']).    applymap(markEvents, subset = ['event']).    set_caption('SMART CHARGING (BATT)')
# smartDF.to_excel(writer, sheet_name="smart")
# writer.save()

smartDF

# %%

# ### SUPER SMART CHARGING

######################## DEPO ############################
depot = []
carDataDF = pd.DataFrame.from_records(carData, columns=["battPerc","inDepot","battSize","chargePt"])
chargePtDF = pd.DataFrame.from_records(chargePtData, columns=["maxRate","inUse"])
for car in range(0, len(carDataDF)):
    if carDataDF.loc[car,'inDepot']: depot.append(car)

######################## SIMULATION #############################
rcCount = 0                     # INITIALISE A COUNTER FOR RAPID CHARGES
time = readTime("06:00")        # CHOOSE START TIME
simulationDF = pd.DataFrame(columns=['time','car','charge_rate','batt','event'])

for i in range(0, runTime):
    carDataDF, time, depot, simulationDF, chargePtD = inOutDepot(carDataDF, shiftsByCar, time, depot, simulationDF, chargePtDF)
    carDataDF, time, rcCount, simulationDF = decreaseBatt(carDataDF, shiftsByCar, time, rcCount, simulationDF)
    carDataDF, simulationDF, chargePtDF = superSmartCharge(carDataDF, depot, shiftsByCar, time, chargeCapacity, simulationDF, chargePtDF)
    time = incrementTime(time)

print("No. of rapid charges: " + str(rcCount))
smartDF = simulationDF.set_index(['time','car'])
smartDF = smartDF.T.stack().T
smartDF = smartDF.iloc[6:,:].append(smartDF.iloc[0:6,:])
smartDF = smartDF.style.    applymap(color, subset=['charge_rate']).    applymap(background, subset = ['charge_rate']).    applymap(markEvents, subset = ['event']).    set_caption('SUPER SMART CHARGING')
# smartDF.to_excel(writer, sheet_name="smart")
# writer.save()
smartDF
