import pandas as pd
import numpy as np
import datetime as dt
import time
from sim_functions import *
import json
with open("scenario.txt") as f: scenarios = json.load(f)

chunks = getChunks()
startTime = readTime("06:00")   # CHOOSE STARTTIME
runTime = 24                    # CHOOSE RUNTIME (HRS)
mpkw = 4                        # SET AVERAGE MILES PER kW THAT WILL DETERMINE RATE OF BATT DECREASE
mph = 16                        # SET AVERAGE MILES PER HR COVERED
car_cols = ["battPerc","inDepot","battSize","chargePt"]
cp_cols = ["maxRate","inUse"]
sim_cols = ['time','car','charge_rate','batt','event']

performance = pd.DataFrame(columns=['type','dumb','leavetime','batt','smart'])

for filename in scenarios:
    car_num = filename[0:2]
    carShifts = scenarios[filename]['carShifts']
    chargeCapacity = scenarios[filename]['chargeCapacity']
    carData = scenarios[filename]['carData']
    chargePtData = scenarios[filename]['chargePtData']

    dumbDF, dumb_sim, dumb_rc = runSimulation(
                            startTime, runTime,
                            carData, car_cols, carShifts,
                            chargePtData, cp_cols, chargeCapacity, 
                            sim_cols, mph, mpkw, 'dumbCharge')

    smart_leavetimeDF, smart_leavetime_sim, smart_leavetime_rc = runSimulation(
                            startTime, runTime,
                            carData, car_cols, carShifts,
                            chargePtData, cp_cols, chargeCapacity, 
                            sim_cols, mph, mpkw, 'smartCharge_leavetime')

    smart_battDF, smart_batt_sim, smart_batt_rc = runSimulation(
                            startTime, runTime,
                            carData, car_cols, carShifts,
                            chargePtData, cp_cols, chargeCapacity, 
                            sim_cols, mph, mpkw, 'smartCharge_batt')

    smartDF, smart_sim, smart_rc = runSimulation(
                            startTime, runTime,
                            carData, car_cols, carShifts,
                            chargePtData, cp_cols, chargeCapacity, 
                            sim_cols, mph, mpkw, 'superSmartCharge')
    
    performance = performance.append({
        'type': filename,
        'dumb': dumb_rc,
        'leavetime': smart_leavetime_rc,
        'batt': smart_batt_rc,
        'smart': smart_rc
    }, ignore_index=True)


    ###############################################################
    # SAVE TO EXCEL (ONLY RUN WHEN ALL ALGORITHMS ARE UNCOMMENTED)
    # NOTE: CREATE A FOLDER CALLED 'TEST' FIRST
    ###############################################################
    # open writer
    writer = pd.ExcelWriter("results/" + filename + ".xlsx")
    # write files
    dumbDF.to_excel(
        writer, sheet_name="dumb")
    smart_leavetimeDF.to_excel(
        writer, sheet_name="smart_leavetime")
    smart_battDF.to_excel(
        writer, sheet_name="smart_batt")
    smartDF.to_excel(
        writer, sheet_name="superSmart")
    # close writer
    writer.save()
    print(str(filename) + ' done')
    
writer = pd.ExcelWriter("results/comparison.xlsx")
performance.to_excel(writer)
writer.save()

# smart_sim[['event','batt']].to_excel('output.xlsx')