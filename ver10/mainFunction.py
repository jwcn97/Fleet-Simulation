import pandas as pd
from chunks import chunks
from supportFunctions import *
from chargingFunctions import *
from drivingFunctions import *

def runSimulation(startTime, runTime, rcData,
                fleetData, driveDataDF, allShiftsDF, breaksDF, pricesDF, algo):

    # INITIALISE MAIN DATAFRAMES WITH DATA AT START TIME
    #   Get data from csv inputs
    carData, chargePtData = getLists(fleetData)

    #   Choose column names
    carCols = ["inDepot","battSize","battkW",
                "lat","long",
                "chargePt","chargeRate",
                "rcCount","rcChunks",
                "shiftIndex","latestStartShift","latestEndShift"]
    cpCols = ["maxRate","inUse"]
    simCols = ["time","car","chargeDiff","batt","event","costPerCharge","totalCost"]

    #   Initialise dataframes
    carDataDF = pd.DataFrame.from_records(carData, columns=carCols)
    chargePtDF = pd.DataFrame.from_records(chargePtData, columns=cpCols)
    simulationDF = pd.DataFrame(columns=simCols)

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

    totalCost = 0           # INITIALISE A COUNTER FOR TOTAL COST
    time = startTime        # CHOOSE START TIME

    # RUN SIMULATION FOR ALL OF RUN TIME
    for i in range(0, runTime*chunks):
        # INITIALISE A VARIABLE TO CHECK FOR EVENT CHANGES
        eventChange = (False, None)

        # *** RUN FUNCTIONS THAT INCLUDE WILL RECOGNISE CHANGES IN EVENTS ***
        eventChange, carDataDF, depot, chargePtDF = inOutDepot(time, carDataDF, shiftsByCar, depot, chargePtDF, eventChange)
        eventChange, carDataDF = readFullBattCars(time, carDataDF, simulationDF, totalCost, eventChange)
        eventChange = readTariffChanges(time, pricesDF, eventChange)
        eventChange = readExtraCharging(time, pricesDF, depot, carDataDF, shiftsByCar, availablePower, eventChange)

        # *** RUN FUNCTIONS AFFECTING CARS OUTSIDE THE DEPOT ***
        # DECREASE BATT/RAPID CHARGE CARS OUTSIDE THE DEPOT
        carDataDF, simulationDF, totalCost = driving(time, carDataDF, driveDataByCar, breaksDF, rcData, simulationDF, i, totalCost)

        # *** RUN FUNCTIONS AFFECTING CARS IN THE DEPOT ***
        # IF THERE IS AN EVENT and THERE ARE CARS THAT REQUIRE CHARGING
        # RUN CHARGING ALGORITHM
        if (eventChange[0] == True) and (len(depot) > 0):
            carDataDF = algo(time, carDataDF, depot, shiftsByCar, availablePower, chargePtDF, pricesDF, eventChange)

        # CHARGE/READ WAITING CARS IN THE DEPOT
        carDataDF, simulationDF, totalCost = charge(time, carDataDF, depot, simulationDF, pricesDF, totalCost)

        # FORMAT TOTAL COST COLUMN IN SIMULATION DF
        simulationDF = adjustTotalCost(time, simulationDF)

        # INCREMENT TIME OF SIMULATION
        time = incrementTime(time)

    return simulationDF, carDataDF['rcCount'].sum(), totalCost