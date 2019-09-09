import numpy as np
import time
from chunks import chunks
from supportFunctions import *

# CHECK WHETHER VEHICLES REQUIRE RAPID CHARGE
#   UPDATE RAPID CHARGE CHUNKS IN CARDATADF and UPDATE RCCOUNT
def checkRC(carDataDF, rcDuration, rcPerc):
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
                carDataDF.loc[car, 'rcCount'] += 1

            # OTHERWISE, RESET RAPID CHARGE CHUNKS COUNT
            else: carDataDF.loc[car, 'rcChunks'] = 0
    
    return carDataDF, drivingCarsDF

# LOOK AT CARS OUTSIDE THE DEPOT
#   FOR CARS THAT NEED RAPID CHARGING: RAPID CHARGE
#   FOR CARS THAT DON'T NEED RAPID CHARGING: DECREASE BATT
def driving(time, carDataDF, driveDataByCar, breaksDF, rcData, simulationDF, ind, totalCost):
    # EXTRACT RAPID CHARGE DATA
    rcPrice = getData(rcData, 'rcPrice')        # PRICE PER KW OF RAPID CHARGE (£ PER KW)
    rcDuration = getData(rcData, 'rcDuration')  # RAPID CHARGE DURATION (HRS)
    rcPerc = getData(rcData, 'rcPerc')          # WHAT PERCENTAGE TO START RAPID CHARGING (%)
    rcRate = getData(rcData, 'rcRate')          # RATE OF RAPID CHARGING (KW/HR)

    # UPDATE RAPID CHARGE CHUNKS IN CARDATADF and UPDATE RCCOUNT
    carDataDF, drivingCarsDF = checkRC(carDataDF, rcDuration, rcPerc)

    # GET OTHER PARAMETERS
    drivingValues = driveDataByCar['0'].shape[0]
    breakStart = getData(breaksDF, 'startBreak')
    breakEnd = getData(breaksDF, 'endBreak')

    for rows in range(len(drivingCarsDF)):
        car = drivingCarsDF.index[rows]

        # READ BATTERY and BATTERY SIZE
        batt = carDataDF.loc[car, 'battkW']
        battSize = carDataDF.loc[car, 'battSize']
        
        # ***** FOR CARS THAT DON'T NEED RAPID CHARGING, DECREASE BATT (DRIVE) *****
        if carDataDF.loc[car, 'rcChunks'] == 0:
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

            # DECREASE BATTERY and ASSIGN BATTERY
            carDataDF.loc[car,'battkW'] = batt - (kwphr/chunks)
        
        # ***** FOR CARS THAT NEED RAPID CHARGING, RAPID CHARGE *****
        else:
            # CALCULATE BATTERY INCREASE
            if batt + rcRate/chunks > battSize: RCbattIncrease = battSize - batt
            else:                               RCbattIncrease = rcRate/chunks

            # UPDATE RAPID CHARGE COUNT AND TOTAL COST
            RCcost = rcPrice * RCbattIncrease
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
            carDataDF.loc[car,'battkW'] = batt + RCbattIncrease

    return carDataDF, simulationDF, totalCost