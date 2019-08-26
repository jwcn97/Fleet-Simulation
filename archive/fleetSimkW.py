import pandas as pd
import numpy as np
import sys
import datetime as dt
import time

#===============================================================================
def readTime(ti):
    read = dt.datetime.strptime(ti, "%H:%M").time()
    return read

def rereadTime(ti):
    reread = str(ti)
    if len(reread) == 5:
        read = dt.datetime.strptime(reread, "%H:%M")

    else:
        read = dt.datetime.strptime(reread, "%H:%M:%S")

    return read

def incrementTime(ti):
    rereadTi = rereadTime(ti)
    oneHour = dt.timedelta(hours=1)

    finalTime = (rereadTi + oneHour).time()

    return finalTime

#===============================================================================
# SET UP START OF SIMULATION

# CHOOSE START TIME
time = readTime("06:00")

# SET UP CAR DATA DF AT START TIME
a = [30, 100, 1, 30]
b = [30, 100, 1, 30]
c = [30, 100, 1, 30]
d = [30, 100, 1, 30]

carData = [a, b, c, d]
labels1 = ["battPower", "battPerc", "isCharge", "battSize"]

carDataDF = pd.DataFrame.from_records(carData, columns=labels1)

# SET UP CAR SHIFTS LIBRARY
aS = [["06:00", "11:00"], ["14:00", "20:00"]]
bS = [["06:00", "13:00"], ["17:00", "23:00"]]
cS = [["07:00", "12:00"], ["20:00", "00:00"]]
dS = [["08:00", "14:00"], ["18:00", "23:00"]]

carShifts = [aS, bS, cS, dS]
labels2 = ["startShift", "endShift"]

carNumList = [0,1,2,3]                                          # Set keys as numbers representing each car
shiftsByCar = {}                                                # Set dictionary name as 'shiftsByCar'
for e in carNumList:                                            # For every key:
    shiftsDF = pd.DataFrame(carShifts[e], columns=labels2)
    shiftsDF = shiftsDF.sort_values(by=['startShift'])
    shiftsDF = shiftsDF.reset_index(drop=True)
    shiftsByCar['%s' % e] = shiftsDF                                # The value = an empty list

#===============================================================================
# SET MAX AVAILABLE POWER IN CENTRE (kW/hr)
chargeCapacity = 12

# SET MAX CHARGE RATE PER CAR (kW/hr)
maxRate = 7

# SET UP CARS IN CHARGE CENTRE
chargeCen = []
for car in range(0, len(carDataDF)):
    isC = carDataDF.loc[car, 'isCharge']
    if isC == 1:
        chargeCen.append(car)

#===============================================================================
# DECREASE BATT DURING SHIFT

# # SET AVERAGE MILES PER kW THAT WILL DETERMINE RATE OF BATT DECREASE
mpkw = 4

# SET AVERAGE MILES PER HR COVERED
mph = 16

# INITIALISE A COUNTER FOR RAPID CHARGES
rcCount = 0

def decreaseBatt(carDataDF, shiftsByCar, time, rcCount):
    for a in range(len(carDataDF)):
        # READ DATA FOR EVERY ROW IN CarDataDF
        battPower = carDataDF.loc[a, 'battPower']
        isC = carDataDF.loc[a, 'isCharge']
        battSize = carDataDF.loc[a, 'battSize']

        # CALCULATE RANDOMISED RATE OF BATT DECREASE
        # rand = np.random.randint(0,high=100)
        # mpkw = 3.5 + ((rand/100)*2)
        kwphr = mph/mpkw

        for b in range(0,len(shiftsByCar[str(a)])):

            startS = readTime(shiftsByCar[str(a)].loc[b, 'startShift'])
            endS = readTime(shiftsByCar[str(a)].loc[b, 'endShift'])

            # IF SHIFT DOESN'T RUN OVER MIDNIGHT
            if startS < endS:
                # DECREASE BATT DURING SHIFT
                if time >= startS and time < endS:
                    battPower -= kwphr

            # IF SHIFT RUNS OVER MIDNIGHT
            else:
                # SELECT NON-SHIFT TIME
                saveVal = startS
                startS = endS
                endS = saveVal

                # DECREASE BATT IF NOT DURING NON-SHIFT
                if time >= startS and time < endS:
                    continue
                else:
                    battPower -= kwphr

        batt = (battPower/battSize)*100

        # RAPID CHARGE OUTSIDE CHARGE CENTRE IF VEHICLE HAS NO BATTERY
        if battPower <= 0:
            batt = 90
            battPower = (batt/100)*battSize
            rcCount += 1
            print("*** car " + str(a) + " rapid charge ***")


        # ASSIGN BATTERY
        carDataDF.loc[a, 'battPerc'] = batt
        carDataDF.loc[a, 'battPower'] = battPower

    return carDataDF, time, rcCount

#===============================================================================
# WHEN SHIFT STARTS: isCharge = 0 AND REMOVE FROM CHARGE CENTRE
# WHEN SHIFT ENDS: isCharge = 1 AND ENTER CHARGE CENTRE

def inOutCentre(carDataDF, shiftsByCar, time, chargeCen):
    for b in range(0, len(carDataDF)):
        for c in range(0, len(shiftsByCar[str(b)])):
            # READ DATA FOR EVERY ROW IN CarDataDF
            startS = readTime(shiftsByCar[str(b)].loc[c, 'startShift'])
            endS = readTime(shiftsByCar[str(b)].loc[c, 'endShift'])

            if time == startS:
                carDataDF.loc[b, 'isCharge'] = 0
                chargeCen.remove(b)
                # print("car " + str(b) + " has exited the charge centre :0")

                kw = carDataDF.loc[b, 'battPower']
                print("  car " + str(b) + " leaving centre with " + str(kw) + " kW")

            if time == endS:
                carDataDF.loc[b, 'isCharge'] = 1
                chargeCen.append(b)
                # print("car " + str(b) + " has entered the charge centre :)")

    return carDataDF, time, chargeCen

#===============================================================================
# CHARGE VEHICLE FOR ONE HOUR

def charge(carDataDF, carNum, chargeCen, chargeRate):
    battPower = carDataDF.loc[carNum, 'battPower']
    battSize = carDataDF.loc[carNum, 'battSize']
    print("    power:     " + str(battPower))

    # THE FOURTH CHARGER IS A SLOW CHARGER WITH A MAX RATE OF 3kW/hr
    if len(chargeCen) > 3 and chargeRate > 3:
        chargeRate = 3

    # INCREASE BATT PERCENTAGE ACCORDING TO CHARGE RATE
    battPower += chargeRate
    batt = (battPower/battSize)*100

    # ASSIGN BATTERY
    if batt >= 100:
        carDataDF.loc[carNum, 'battPower'] = battSize
        carDataDF.loc[carNum, 'battPerc'] = 100
        print("    new power: " + str(battSize))
    else:
        carDataDF.loc[carNum, 'battPower'] = battPower
        carDataDF.loc[carNum, 'battPerc'] = batt
        print("    new power: " + str(battPower))

    return carDataDF

#===============================================================================
# INCREASE BATT DURING CHARGE

def dumbCharge(chargeCen, chargeCapacity, maxRate, carDataDF):
    # IF THERE ARE CARS IN THE CHARGE CENTRE
    if len(chargeCen) >= 1:

        # SELECT CARS IN CENTRE WITH BATT < 100
        chargeDF = carDataDF.loc[carDataDF['isCharge'] == 1]
        chargeDF = chargeDF.loc[chargeDF['battPerc'] < 100]

        if len(chargeDF) >= 1:
            # CALCULATE CHARGE RATE
            chargeRate = chargeCapacity/len(chargeDF)
            if chargeRate > maxRate:
                chargeRate = maxRate

            # CHARGE SELECTED CARS IN CENTRE
            for c in range(len(chargeDF)):
                d = chargeDF.index[c]
                print("  car "+str(d)+" charging at "+str(chargeRate)+" kW/hr")
                carDataDF = charge(carDataDF, d, chargeCen, chargeRate)


    return carDataDF

#===============================================================================

def smartCharge(chargeCen, shiftsByCar, time, chargeCapacity, maxRate, carDataDF):
    # IF THERE ARE CARS IN THE CHARGE CENTRE
    if len(chargeCen) >= 1:

        listRows = []
        # FIND THE TIMES WHEN CARS LEAVE THE CHARGE CENTRE
        for e in range(0, len(chargeCen)):
            f = chargeCen[e]
            leaveTime = readTime("23:59")
            for g in range(0, len(shiftsByCar[str(f)])):
                startTime = readTime(shiftsByCar[str(f)].loc[g, 'startShift'])
                if startTime > time and startTime < leaveTime:
                    leaveTime = startTime

            if leaveTime == readTime("23:59"):
                leaveTime = shiftsByCar[str(f)].loc[0, 'startShift']

            leaveT = rereadTime(leaveTime)
            timeT = rereadTime(time)
            leaveF = abs(leaveT - timeT)

            row = [f, leaveF]
            listRows.append(row)

        labelLT = ['car', 'hrsLeft']
        leaveTimes = pd.DataFrame.from_records(listRows, columns=labelLT)
        leaveTimes = leaveTimes.sort_values(by=['hrsLeft'])
        leaveTimes = leaveTimes.reset_index(drop=True)

        for h in range(0, len(leaveTimes)):
            car = leaveTimes.loc[h, 'car']
            batt = carDataDF.loc[car, 'battPerc']

            energyLeft = chargeCapacity - maxRate
            if energyLeft >= 0 and batt < 100:
                chargeRate = maxRate
                print("  car "+str(car)+" charging at "+str(chargeRate)+" kW/hr")
                charge(carDataDF, car, chargeCen, chargeRate)

                chargeCapacity -= chargeRate

            elif energyLeft < 0 and energyLeft > -maxRate and batt < 100:
                chargeRate = chargeCapacity
                print("  car "+str(car)+" charging at "+str(chargeRate)+" kW/hr")
                charge(carDataDF, car, chargeCen, chargeRate)

                chargeCapacity -= chargeRate

            else:
                continue

    return carDataDF


#===============================================================================
# CHOOSE TIME (HRS)
runTime = 24

# RUN THE PROGRAM

for i in range(0, runTime):
    print("time = " + str(time))
    carDataDF, time, chargeCen = inOutCentre(carDataDF, shiftsByCar, time, chargeCen)

    carDataDF, time, rcCount = decreaseBatt(carDataDF, shiftsByCar, time, rcCount)

    # carDataDF = dumbCharge(chargeCen, chargeCapacity, maxRate, carDataDF)
    carDataDF = smartCharge(chargeCen, shiftsByCar, time, chargeCapacity, maxRate, carDataDF)

    time = incrementTime(time)
    print("\n")



print("No. of rapid charges: " + str(rcCount))
carDataDF
