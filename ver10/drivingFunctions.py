import numpy as np
import math
import geopy
from geopy.distance import VincentyDistance
import time
from chunks import chunks
from supportFunctions import *

# CALCULATE BEARING BETWEEN TWO POINTS
#   POINT A, POINT B IN THE FORM OF TUPLES
def calculateBearing(pointA, pointB):
    """
    Calculates the bearing between two points.
    The formulae used is the following:
        θ = atan2(sin(Δlong).cos(lat2),
                  cos(lat1).sin(lat2) − sin(lat1).cos(lat2).cos(Δlong))
    :Parameters:
      - `pointA: The tuple representing the latitude/longitude for the
        first point. Latitude and longitude must be in decimal degrees
      - `pointB: The tuple representing the latitude/longitude for the
        second point. Latitude and longitude must be in decimal degrees
    :Returns:
      The bearing in degrees
    :Returns Type:
      float
    """
    if (type(pointA) != tuple) or (type(pointB) != tuple):
        raise TypeError("Only tuples are supported as arguments")

    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])

    diffLong = math.radians(pointB[1] - pointA[1])

    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
            * math.cos(lat2) * math.cos(diffLong))

    initial_bearing = math.atan2(x, y)

    # Now we have the initial bearing but math.atan2 return values
    # from -180° to + 180° which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing

# FIND LAT LONG LOCATION BASED ON MILES AND BEARING
#   bearing (in degrees), distance (in miles)
def milesToLatLong(lat1, long1, bearing, distance):
    origin = geopy.Point(lat1, long1)
    destination = VincentyDistance(kilometers=distance*1.609).destination(origin, bearing)

    return destination.latitude, destination.longitude

# FIND THE DISTANCE BETWEEN TWO COORDINATES
#   ASSUMES EARTH IS PERFECTLY SPHERICAL
def latLongToMiles(lat1, long1, lat2, long2):
    # Convert latitude and longitude to
    # spherical coordinates in radians.
    degrees_to_radians = math.pi/180.0

    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians

    # theta = longitude
    theta1 = long1*degrees_to_radians
    theta2 = long2*degrees_to_radians

    # Compute spherical distance from spherical coordinates.

    # For two locations in spherical coordinates
    # (1, theta, phi) and (1, theta', phi')
    # cosine( arc length ) =
    # sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length

    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) +
    math.cos(phi1)*math.cos(phi2))
    arc = math.acos( cos )

    # Remember to multiply arc by the radius of the earth
    # in your favorite set of units to get length.
    return arc*3960

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

#########################################################################
# LOOK AT CARS OUTSIDE THE DEPOT
#   FOR CARS THAT NEED RAPID CHARGING: RAPID CHARGE
#   FOR CARS THAT DON'T NEED RAPID CHARGING: DECREASE BATT
#########################################################################
def constantDriving(time, carDataDF, driveDataByCar, breaksDF, rcData, latLongDF, simulationDF, ind):
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
    totalCost = carDataDF['totalCost'].sum()

    for rows in range(len(drivingCarsDF)):
        car = drivingCarsDF.index[rows]

        # READ BATTERY and BATTERY SIZE
        batt = carDataDF.loc[car, 'battkW']
        battSize = carDataDF.loc[car, 'battSize']
        
        # ***** FOR CARS THAT DON'T NEED RAPID CHARGING, DECREASE BATT (DRIVE) *****
        if carDataDF.loc[car, 'rcChunks'] == 0:
            # SET MILEAGE AND MPKW
            mileage = 16
            mpkw = 4

            # UPDATE MILEAGE TO BE 0 DURING BREAK PERIOD
            if not breakStart == "None":
                if readTime(breakStart) <= time.time() < readTime(breakEnd):
                    mileage = 0

            # CALCULATE RATE OF BATT DECREASE
            kwphr = mileage/mpkw

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
            # ASSIGN UPDATED TOTAL DISTANCE OF CAR (IN MILES)
            carDataDF.loc[car, 'totalDistance'] += (mileage/chunks)
        
        # ***** FOR CARS THAT NEED RAPID CHARGING, RAPID CHARGE *****
        else:
            # CALCULATE BATTERY INCREASE
            if batt + rcRate/chunks > battSize: RCbattIncrease = battSize - batt
            else:                               RCbattIncrease = rcRate/chunks

            # UPDATE RAPID CHARGE COUNT AND TOTAL COST
            rcCost = rcPrice * RCbattIncrease
            totalCost += rcCost

            # UPDATE SIMULATION ACCORDINGLY
            simulationDF = simulationDF.append({
                'time': time,
                'car': car,
                'chargeDiff': round(RCbattIncrease, 1),
                'batt': round(batt, 1),
                'event': 'RC',
                'costPerCharge': round(rcCost, 2),
                'totalCost': round(totalCost, 2)
            }, ignore_index=True)

            # RAPID CHARGE and ASSIGN BATTERY
            carDataDF.loc[car,'battkW'] = batt + RCbattIncrease
            # ASSIGN UPDATED TOTAL COST
            carDataDF.loc[car, 'totalCost'] += rcCost

    return carDataDF, simulationDF

#########################################################################
# SIMILAR TO DRIVING FUNCTION (WITH VARIATIONS IN MILEAGE AND MPKW)
#########################################################################
def variedDriving(time, carDataDF, driveDataByCar, breaksDF, rcData, latLongDF, simulationDF, ind):
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
    totalCost = carDataDF['totalCost'].sum()

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

            # UPDATE MILEAGE TO BE 0 DURING BREAK PERIOD
            if not breakStart == "None":
                if readTime(breakStart) <= time.time() < readTime(breakEnd):
                    mileage = 0

            # CALCULATE RATE OF BATT DECREASE
            kwphr = mileage/mpkw

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
            # ASSIGN UPDATED TOTAL DISTANCE OF CAR (IN MILES)
            carDataDF.loc[car, 'totalDistance'] += (mileage/chunks)
        
        # ***** FOR CARS THAT NEED RAPID CHARGING, RAPID CHARGE *****
        else:
            # CALCULATE BATTERY INCREASE
            if batt + rcRate/chunks > battSize: RCbattIncrease = battSize - batt
            else:                               RCbattIncrease = rcRate/chunks

            # UPDATE RAPID CHARGE COUNT AND TOTAL COST
            rcCost = rcPrice * RCbattIncrease
            totalCost += rcCost

            # UPDATE SIMULATION ACCORDINGLY
            simulationDF = simulationDF.append({
                'time': time,
                'car': car,
                'chargeDiff': round(RCbattIncrease, 1),
                'batt': round(batt, 1),
                'event': 'RC',
                'costPerCharge': round(rcCost, 2),
                'totalCost': round(totalCost, 2)
            }, ignore_index=True)

            # RAPID CHARGE and ASSIGN BATTERY
            carDataDF.loc[car,'battkW'] = batt + RCbattIncrease
            # ASSIGN UPDATED TOTAL COST
            carDataDF.loc[car, 'totalCost'] += rcCost

    return carDataDF, simulationDF

#########################################################################
# SIMILAR TO DRIVING FUNCTION (WITH LATITUDE AND LONGITUDE CALCULATIONS)
#########################################################################
def latLongDriving(time, carDataDF, driveDataByCar, breaksDF, rcData, latLongDF, simulationDF, ind):
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
    totalCost = carDataDF['totalCost'].sum()

    for rows in range(len(drivingCarsDF)):
        car = drivingCarsDF.index[rows]

        # READ BATTERY and BATTERY SIZE
        batt = carDataDF.loc[car, 'battkW']
        battSize = carDataDF.loc[car, 'battSize']
        destinations = latLongDF.loc[car,'destinations']
        
        # ***** FOR CARS THAT DON'T NEED RAPID CHARGING, DECREASE BATT (DRIVE) *****
        if carDataDF.loc[car, 'rcChunks'] == 0:
            # SET MILEAGE AND MPKW
            mileage = 16
            mpkw = 4

            # UPDATE MILEAGE TO BE 0 DURING BREAK PERIOD
            if not breakStart == "None":
                if readTime(breakStart) <= time.time() < readTime(breakEnd):
                    mileage = 0

            # GET INDEX OF NEXT DESTINATION
            destIndex = carDataDF.loc[car, 'destIndex']
            # GET LATITUDE AND LONGITUDE PARAMETERS
            currLat, currLong = carDataDF.loc[car, 'lat'], carDataDF.loc[car, 'long']
            destLat, destLong = carDataDF.loc[car, 'destLat'], carDataDF.loc[car, 'destLong']

            # CALCULATE BEARING OR DIRECTION OF TRAVEL
            bearing = calculateBearing((currLat, currLong),(destLat, destLong))
            # CALCULATE NEXT LATITUDE AND LONGITUDE FOR NEXT TIME FRAME
            newLat, newLong = milesToLatLong(currLat, currLong, bearing, mileage/chunks)

            # IF LATITUDE PASSES BY DESTINATION LATITUDE
            #   VEHICLE HAS REACHED ITS INTENDED DESTINATION
            if (currLat < destLat < newLat) or (newLat < destLat < currLat):
                newLat, newLong = destLat, destLong

                # ENSURE THE CYCLE REPEATS
                destIndex = (destIndex + 1) % len(destinations)
                # ASSIGNS DESTINATION LATITUDE AND LONGITUDE
                carDataDF.loc[car,'destIndex'] = destIndex
                carDataDF.loc[car,'destLat'] = destinations[destIndex][0]
                carDataDF.loc[car,'destLong'] = destinations[destIndex][1]
            
            carDataDF.loc[car,'lat'] = newLat
            carDataDF.loc[car,'long'] = newLong

            # CALCULATE RATE OF BATT DECREASE
            kwphr = mileage/mpkw

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

            # UPDATE BATTERY AND TOTAL DISTANCE OF CAR (IN MILES)
            carDataDF.loc[car,'battkW'] = batt - (kwphr/chunks)
            carDataDF.loc[car, 'totalDistance'] += (mileage/chunks)
        
        # ***** FOR CARS THAT NEED RAPID CHARGING, RAPID CHARGE *****
        else:
            # CALCULATE BATTERY INCREASE
            if batt + rcRate/chunks > battSize: RCbattIncrease = battSize - batt
            else:                               RCbattIncrease = rcRate/chunks

            # UPDATE RAPID CHARGE COUNT AND TOTAL COST
            rcCost = rcPrice * RCbattIncrease
            totalCost += rcCost

            # UPDATE SIMULATION ACCORDINGLY
            simulationDF = simulationDF.append({
                'time': time,
                'car': car,
                'chargeDiff': round(RCbattIncrease, 1),
                'batt': round(batt, 1),
                'event': 'RC',
                'costPerCharge': round(rcCost, 2),
                'totalCost': round(totalCost, 2)
            }, ignore_index=True)

            # UPDATE BATTERY AND TOTAL COST
            carDataDF.loc[car,'battkW'] = batt + RCbattIncrease
            carDataDF.loc[car, 'totalCost'] += rcCost

    return carDataDF, simulationDF