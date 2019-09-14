import pandas as pd
from chunks import chunks
from supportFunctions import *
from chargingFunctions import *
from drivingFunctions import *

def runSimulation(startTime, runTime, rcData,
                fleetData, driveDataDF, allShiftsDF, breaksDF, pricesDF, algo):

    # INITIALISE MAIN DATAFRAMES WITH DATA AT START TIME
    #   Choose column names
    carCols = ["inDepot","battSize","battkW",
                "lat","long","destLat","destLong","destIndex",
                "chargePt","chargeRate","totalCost","totalDistance",
                "rcCount","rcChunks",
                "shiftIndex","latestStartShift","latestEndShift"]
    cpCols = ["maxRate","inUse"]
    simCols = ["time","car","chargeDiff","batt","event","costPerCharge","totalCost"]

    #   Generate dataframes from csv inputs
    carDataDF, chargePtDF, simulationDF = generateDF(fleetData, carCols, cpCols, simCols)

    depot = []
    driveDataByCar = {}
    for car in range(0, len(carDataDF)):
        # APPEND CARS INTO DEPOT AT START TIME
        if carDataDF.loc[car,'inDepot']: depot.append(car)
        # CREATE LIBRARY FOR DRIVING DATA
        findData = driveDataDF.loc[driveDataDF['car']==car]
        dataNoIndex = findData.reset_index(drop=True)
        driveDataByCar['%s' % car] = dataNoIndex
    
    # CREATE LIBRARY FOR SHIFTS BY CAR
    shiftsByCar = unpackShifts(carDataDF, allShiftsDF)
    # RETRIEVE AVAILABLE POWER FROM FLEET DATA
    availablePower = getData(fleetData, 'availablePower')
    # CHOOSE START TIME
    time = startTime

    # RUN SIMULATION FOR ALL OF RUN TIME
    for i in range(0, runTime*chunks):
        # INITIALISE A VARIABLE TO CHECK FOR EVENT CHANGES
        eventChange = None

        # *** RUN FUNCTIONS THAT INCLUDE WILL RECOGNISE CHANGES IN EVENTS ***
        eventChange, carDataDF, depot, chargePtDF = inOutDepot(time, carDataDF, shiftsByCar, depot, chargePtDF, eventChange)
        eventChange, carDataDF = readFullBattCars(time, carDataDF, simulationDF, eventChange)
        eventChange = readTariffChanges(time, pricesDF, eventChange)
        eventChange = readExtraCharging(time, pricesDF, depot, carDataDF, shiftsByCar, availablePower, eventChange)

        # *** RUN FUNCTIONS AFFECTING CARS OUTSIDE THE DEPOT ***
        # DECREASE BATT/RAPID CHARGE CARS OUTSIDE THE DEPOT
        carDataDF, simulationDF = driving(time, carDataDF, driveDataByCar, breaksDF, rcData, simulationDF, i)

        # *** RUN FUNCTIONS AFFECTING CARS IN THE DEPOT ***
        # IF THERE IS AN EVENT and THERE ARE CARS THAT REQUIRE CHARGING
        # RUN CHARGING ALGORITHM
        if (eventChange != None) and (len(depot) > 0):
            carDataDF = algo(time, carDataDF, depot, shiftsByCar, availablePower, chargePtDF, pricesDF, eventChange)

        # CHARGE/READ WAITING CARS IN THE DEPOT
        carDataDF, simulationDF = charge(time, carDataDF, depot, simulationDF, pricesDF)

        # FORMAT TOTAL COST COLUMN IN SIMULATION DF
        simulationDF = adjustTotalCost(time, simulationDF)

        # INCREMENT TIME OF SIMULATION
        time = incrementTime(time)

    return simulationDF, carDataDF['rcCount'].sum(), carDataDF['totalCost'].sum()