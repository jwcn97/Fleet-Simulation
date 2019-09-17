import numpy as np
import math
import geopy
from geopy.distance import VincentyDistance
import time
from chunks import chunks
from supportFunctions import *

#######################################
# LAT AND LONG FUNCTIONS
#######################################

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

# UPDATE THE LAT AND LONG OF VEHICLE WHILE DRIVING
#   miles = miles going to be travelled by vehicle in this time slot
#   (dependent on number of chunks)
def updateLatLong(car, carDataDF, latLongDF, miles):
    # GET ALL DESTINATIONS OF VEHICLE
    destinations = latLongDF.loc[car,'destinations']
    # GET INDEX OF NEXT DESTINATION
    destIndex = carDataDF.loc[car, 'destIndex']
    # GET LATITUDE AND LONGITUDE PARAMETERS
    currLat, currLong = carDataDF.loc[car, 'lat'], carDataDF.loc[car, 'long']
    destLat, destLong = carDataDF.loc[car, 'destLat'], carDataDF.loc[car, 'destLong']

    # CALCULATE BEARING OR DIRECTION OF TRAVEL
    bearing = calculateBearing((currLat, currLong),(destLat, destLong))
    # CALCULATE NEXT LATITUDE AND LONGITUDE FOR NEXT TIME FRAME
    newLat, newLong = milesToLatLong(currLat, currLong, bearing, miles)

    # IF LATITUDE PASSES BY DESTINATION LATITUDE
    #   VEHICLE HAS REACHED ITS INTENDED DESTINATION
    if (currLat < destLat < newLat) or (currLat > destLat > newLat):
        # SET NEW LAT AND LONG TO THAT OF DESTINATION'S
        newLat, newLong = destLat, destLong
        # ENSURE THE CYCLE REPEATS
        destIndex = (destIndex + 1) % len(destinations)

        # ASSIGNS DESTINATION LATITUDE AND LONGITUDE
        carDataDF.loc[car,'destIndex'] = destIndex
        carDataDF.loc[car,'destLat'] = destinations[destIndex][0]
        carDataDF.loc[car,'destLong'] = destinations[destIndex][1]
    
    carDataDF.loc[car,'lat'] = newLat
    carDataDF.loc[car,'long'] = newLong

    return carDataDF


##################################################
# FUNCTIONS WHICH SUPPORT DRIVING
##################################################

# CHECK WHETHER IT IS A NON CHARGING BREAK
def breakTime(time, breaksDF):
    breakStart = getData(breaksDF, 'startBreak')
    breakEnd = getData(breaksDF, 'endBreak')

    if not breakStart == "None":
        if readTime(breakStart) <= time.time() < readTime(breakEnd):
            return True

# DECREASE BATTERY WHILE DRIVING NORMALLY
def decreaseBatt(car, carDataDF, driveDataByCar, ind, nonChargingBreak, latLongDF):
    # READ PARAMETERS
    batt = carDataDF.loc[car, 'battkW']
    battSize = carDataDF.loc[car, 'battSize']
    drivingValues = driveDataByCar['0'].shape[0]

    # GET VALUE FOR MILEAGE AND MPKW
    if nonChargingBreak: mileage = 0
    else:                mileage = driveDataByCar[str(car % 4)].loc[ind % drivingValues, 'mileage']
    mpkw = driveDataByCar[str(car % 4)].loc[ind % drivingValues, 'mpkw']

    # CALCULATE RATE OF BATT DECREASE
    kwphr = mileage/mpkw

    # UPDATE LAT AND LONG OF VEHICLE WHILE DRIVING
    carDataDF = updateLatLong(car, carDataDF, latLongDF, mileage/chunks)

    # SET INPUTS FOR SIMULATION DF
    chargeDiff = round(-kwphr/chunks, 1)
    costPerCharge = 0

    # UPDATE BATTERY AND TOTAL DISTANCE OF CAR (IN MILES)
    carDataDF.loc[car,'battkW'] = batt - (kwphr/chunks)
    carDataDF.loc[car,'totalDistance'] += (mileage/chunks)

    return carDataDF, kwphr, chargeDiff, costPerCharge

# RAPID CHARGE VEHICLE
def rapidCharge(car, carDataDF, rcRate, rcPrice, totalCost):
    # READ BATTERY and BATTERY SIZE
    batt = carDataDF.loc[car, 'battkW']
    battSize = carDataDF.loc[car, 'battSize']

    # CALCULATE BATTERY INCREASE
    if batt + rcRate/chunks > battSize: RCbattIncrease = battSize - batt
    else:                               RCbattIncrease = rcRate/chunks

    # UPDATE RAPID CHARGE COUNT AND TOTAL COST
    rcCost = rcPrice * RCbattIncrease
    totalCost += rcCost

    # UPDATE BATTERY AND TOTAL COST
    carDataDF.loc[car,'battkW'] = batt + RCbattIncrease
    carDataDF.loc[car,'totalCost'] += rcCost

    # SET INPUTS FOR SIMULATION DF
    chargeDiff = round(RCbattIncrease, 2)
    costPerCharge = round(rcCost, 3)

    return carDataDF, totalCost, chargeDiff, costPerCharge


#########################################################################
# LOOK AT CARS OUTSIDE THE DEPOT
#   FOR CARS THAT NEED RAPID CHARGING: RAPID CHARGE
#   FOR CARS THAT DON'T NEED RAPID CHARGING: DECREASE BATT
#########################################################################
def driving(time, carDataDF, driveDataByCar, ind, breaksDF, rcData, latLongDF, sim):
    # EXTRACT RAPID CHARGE DATA
    rcPrice = getData(rcData, 'rcPrice')        # PRICE PER KW OF RAPID CHARGE (£ PER KW)
    rcPerc = getData(rcData, 'rcPerc')          # WHAT PERCENTAGE TO START RAPID CHARGING (%)
    rcRate = getData(rcData, 'rcRate')          # RATE OF RAPID CHARGING (KW/HR)

    # FIND CARS OUTSIDE OF DEPOT
    drivingCarsDF = carDataDF.loc[carDataDF["inDepot"]==0]

    # GET OTHER PARAMETERS
    drivingValues = driveDataByCar['0'].shape[0]
    nonChargingBreak = breakTime(time, breaksDF)
    totalCost = carDataDF['totalCost'].sum()

    for rows in range(len(drivingCarsDF)):
        car = drivingCarsDF.index[rows]

        # READ VEHICLE PARAMETERS
        batt = carDataDF.loc[car, 'battkW']
        battSize = carDataDF.loc[car, 'battSize']
        battNeeded = carDataDF.loc[car, 'battNeeded']
        rcChunks = carDataDF.loc[car,'rcChunks']

        # IF CAR HAS BEEN RAPID CHARGING AND STILL NEEDS RAPID CHARGING, RAPID CHARGE
        if (rcChunks > 0) and (batt < battNeeded < battSize):
            # RAPID CHARGE VEHICLE
            carDataDF, totalCost, chargeDiff, costPerCharge = rapidCharge(car, carDataDF, rcRate, rcPrice, totalCost)
            # UPDATE RC PARAMETERS
            carDataDF.loc[car,'rcChunks'] += 1
            # LABEL EVENT
            event = 'RC'

        # IF CAR HASN'T BEEN RAPID CHARGING BUT NEEDS RAPID CHARGING, RAPID CHARGE
        elif (batt < battSize*rcPerc/100) and (batt < battNeeded < battSize):
            # RAPID CHARGE VEHICLE
            carDataDF, totalCost, chargeDiff, costPerCharge = rapidCharge(car, carDataDF, rcRate, rcPrice, totalCost)
            # UPDATE RC PARAMETERS
            if rcChunks == 0: carDataDF.loc[car,'rcCount'] += 1
            carDataDF.loc[car,'rcChunks'] += 1
            # LABEL EVENT
            event = 'RC'

        # IF CAR DOESN'T NEED RAPID CHARGING, DECREASE BATT (DRIVE):
        else:
            # DECREASE BATTERY OF VEHICLE
            carDataDF, kwphr, chargeDiff, costPerCharge = decreaseBatt(car, carDataDF, driveDataByCar, ind, nonChargingBreak, latLongDF)
            # UPDATE RAPID CHARGE CHUNKS
            carDataDF.loc[car,'rcChunks'] = 0
            # UPDATE EVENT
            event = 'wait' if kwphr == 0.0 else 'drive'

        # UPDATE SIMULATION ACCORDINGLY
        # time, car, chargeDiff, batt, event, costPerCharge, totalCost
        sim += [[time, car, chargeDiff, round(batt, 2), event, costPerCharge, round(totalCost, 3)]]

    return carDataDF, sim