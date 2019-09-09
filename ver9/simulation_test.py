import pandas as pd
import numpy as np
import datetime as dt
import time
from chargingFunctions import *
from stylingFunctions import styleDF
from graphFunctions import *

from flask import Flask, render_template, url_for, request
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    companies = ["BritishGas","OriginalTest"]
    shifts = ["shift0","shift1","shift2","shift3","shift4","shift5"]
    fleetTypes = [0,1,2,3,4,5,6,7,8,9,10,11,12]

    # POST request
    if request.method == 'POST':
        # GET PARAMETERS FROM FORM
        company = request.form['company']
        schedule = request.form['schedule']
        fleetType = int(request.form['fleetType'])
        rcDuration = float(request.form['rcDuration'])
        rcPerc = int(request.form['rcPerc'])
        rcRate = int(request.form['rcRate'])
        runTime = int(request.form['runTime'])
        startTime = readTime("2019-01-01 06:00:00")

        # READ IN NECESSARY CSV FILES
        allShiftsDF = pd.read_csv("csv/schedules/" + schedule + ".csv", sep=";", index_col=None)
        drivingDF = pd.read_csv("csv/driving/HighMpkwLowSD.csv", sep=";", index_col=None)
        pricesDF = pd.read_csv("csv/prices.csv", sep=";", index_col=None)
        pricesDF = pricesDF.loc[pricesDF.company == company]
        breaksDF = pd.read_csv("csv/breaks.csv", sep=";", index_col=None)
        breaksDF = breaksDF.loc[breaksDF.id == 0]
        fleetDF = pd.read_csv("csv/fleetData.csv", sep=";", index_col=None)
        fleetData = fleetDF.loc[fleetDF.index == fleetType]

        # dumbDF, dumbRC, dumbCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
        #                             fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, dumbCharge)

        # leaveTDF, leaveTRC, leaveTCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
        #                             fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, smartCharge_leavetime)

        # battDF, battRC, battCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
        #                             fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, smartCharge_batt)

        # smartDF, smartRC, smartCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate,
        #                             fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, smartCharge_battOverLeavetime)

        # costDF, costRC, costCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate, 
        #                             fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, costSensitiveCharge)

        extraDF, extraRC, extraCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate, 
                                    fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, extraCharge)
        
        # total_cars = 8
        # total_algos = 6

        # compareCars("static/results", extraDF, 'extra', total_cars, company)

        # for car in range(total_cars):
        #     result = pd.concat([getCarDF(dumbDF, 'dumb', car),
        #                         getCarDF(leaveTDF, 'leavetime', car),
        #                         getCarDF(battDF, 'batt', car),
        #                         getCarDF(smartDF, 'smart', car),
        #                         getCarDF(costDF, 'cost', car),
        #                         getCarDF(extraDF, 'extra', car)])
        #     compareAlgo(outputFolder+schedule, result, car, total_algos, company)

        return render_template('home.html',
                    companies=companies,
                    shifts=shifts,
                    fleetTypes=fleetTypes,
                    cost="Total Cost: £" + str(round(extraCost,2)),
                    rapid_charges="Total Rapid Charges: " + str(extraRC))

    # GET request
    else:
        return render_template('home.html',
                    companies=companies,
                    shifts=shifts,
                    fleetTypes=fleetTypes,
                    cost="",
                    rapid_charges="")

@app.route('/about', methods=['GET', 'POST'])
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0')