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
    if request.method == 'POST':
        # SELECT PARAMETERS
        company = request.form['company']
        schedule = request.form['schedule']
        fleetType = int(request.form['fleetType'])
        rcDuration = float(request.form['rcDuration'])
        rcPerc = int(request.form['rcPerc'])
        rcRate = int(request.form['rcRate'])
        runTime = int(request.form['runTime'])
        startTime = readTime(request.form['startTime'])

        # READ IN NECESSARY CSV FILES
        allShiftsDF = pd.read_csv("csv/schedules/" + schedule + ".csv", sep=";", index_col=None)
        drivingDF = pd.read_csv("csv/driving/HighMpkwLowSD.csv", sep=";", index_col=None)
        pricesDF = pd.read_csv("csv/prices.csv", sep=";", index_col=None)
        pricesDF = pricesDF.loc[pricesDF.company == company]
        breaksDF = pd.read_csv("csv/breaks.csv", sep=";", index_col=None)
        breaksDF = breaksDF.loc[breaksDF.id == 0]
        fleetDF = pd.read_csv("csv/fleetData.csv", sep=";", index_col=None)
        fleetData = fleetDF.loc[fleetDF.index == fleetType]

        extraDF, extraRC, extraCost = runSimulation(startTime, runTime, rcDuration, rcPerc, rcRate, 
                                    fleetData, drivingDF, allShiftsDF, breaksDF, pricesDF, extraCharge)
        
        compareCars("static/", "results", extraDF, 'extra', 8, company)

        return render_template('index.html',
                    cost="Total Cost: £" + str(round(extraCost),2),
                    rapid_charges="Total Rapid Charges: " + str(extraRC))

    # Otherwise this was a normal GET request
    else:   
        return render_template('index.html', cost="", rapid_charges="")

if __name__ == '__main__':
    app.run(host='0.0.0.0')