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
    carDataDF, chargePtDF = generateDF(fleetData, carCols, cpCols)

    sim = []
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
        eventChange, carDataDF = readFullBattCars(time, carDataDF, sim, eventChange)
        eventChange = readTariffChanges(time, pricesDF, eventChange)
        eventChange = predictExtraCharging(time, pricesDF, depot, carDataDF, shiftsByCar, availablePower, eventChange)

        # *** RUN FUNCTIONS AFFECTING CARS OUTSIDE THE DEPOT ***
        # DECREASE BATT/RAPID CHARGE CARS OUTSIDE THE DEPOT
        carDataDF, sim = driving(time, carDataDF, driveDataByCar, breaksDF, rcData, sim, i)

        # *** RUN FUNCTIONS AFFECTING CARS IN THE DEPOT ***
        # IF THERE IS AN EVENT and THERE ARE CARS THAT REQUIRE CHARGING
        if (eventChange != None) and (len(depot) > 0):
            # RUN CHARGING ALGORITHM AND UPDATE INTENDED CHARGE RATE
            carDataDF = algo(time, carDataDF, depot, shiftsByCar, availablePower, chargePtDF, pricesDF, eventChange)

        # CHARGE/READ WAITING CARS IN THE DEPOT
        carDataDF, sim = charge(time, carDataDF, depot, sim, pricesDF)

        # FORMAT TOTAL COST COLUMN IN SIMULATION
        sim = adjustTotalCost(time, sim)

        # INCREMENT TIME OF SIMULATION
        time = incrementTime(time)

    # CONVERT SIMULATION LIST TO DATAFRAME
    simulationDF = pd.DataFrame.from_records(sim, columns=simCols)

    return simulationDF, carDataDF['rcCount'].sum(), carDataDF['totalCost'].sum()