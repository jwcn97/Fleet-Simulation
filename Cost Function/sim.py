import pandas as pd
import numpy as np
import math
import datetime as dt

prev = []

def inOutDepot(curr_time, carData, c):
    shiftIdx = carData.loc[c, 'shiftIdx']
    start, end = carData.loc[c, 'shift'][shiftIdx].split('~')
    
    start = dt.datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
    end = dt.datetime.strptime(end, '%Y-%m-%d %H:%M:%S')

    if curr_time == start: # exit depot
        carData.loc[c, 'inDepot'] = 0

    if curr_time == end: # enter depot
        carData.loc[c, 'inDepot'] = 1
        shiftIdx += 1
        if shiftIdx < len(carData.loc[c, 'shift']):
            carData.loc[c, 'shiftIdx'] = shiftIdx
            
    return carData

def drive(carData, c, battSize):
    batt = carData.loc[c, 'batt']
    kwphr = 4
    
    if batt >= kwphr:
        # enough battery to sustain driving
        carData.loc[c, 'batt'] -= kwphr
        carData.loc[c, 'kwUsed'] += kwphr
    else:
        # not enough battery: rapid charge to 70% of battery size
        toRC = battSize * 0.7 - batt
        carData.loc[c, 'batt'] += toRC
        carData.loc[c, 'toRC'] += toRC
        carData.loc[c, 'connection'] += 1
    
    return carData

def charge(carData, c, battSize, cps, cpf, depotLimit):
    (cpsNum, cpsRate) = cps
    (cpfNum, cpfRate) = cpf
    batt = carData.loc[c, 'batt']
    
    # vehicle is not full yet
    if battSize != batt:
        # fast charge
        if cpfNum > 0:
            cpfNum -= 1
            rate = cpfRate
            if battSize - batt < cpfRate:
                rate = battSize - batt
                
        # slow charge
        elif cpsNum > 0:
            cpsNum -= 1
            rate = cpsRate
            if battSize - batt < cpsRate:
                rate = battSize - batt
                
        # all charge points are occupied
        else: rate = 0
                
        carData.loc[c, 'batt'] += rate
        carData.loc[c, 'kwSupplied'] += rate
        carData.loc[c, 'kwDiff'] = rate
        
    return carData, (cpsNum, cpsRate), (cpfNum, cpfRate)

# simulation only runs for a day
def runSimulation(filename, cps, cpf, tariff, carNum, battSize, depotLimit):
    # current inputs
    curr = {
        'shift': filename,
        'cp': (cps, cpf),
        'cars': carNum,
        'depotLimit': depotLimit
    }

    # use the previous answer if same inputs have been used before
    if (len(prev) > 0) and (curr in [i['inputs'] for i in prev]):
        idx = [i['inputs'] for i in prev].index(curr)
        return prev[idx]['answer']

    # extract schedule
    schedule = pd.read_csv("csv/schedules/" + filename + ".csv", sep=";", index_col=None)
    schedule['shift'] = schedule['shift'].apply(eval)
    
    # store temperory variable
    minDepotNum = 1
    cps_temp, cpf_temp = cps, cpf
    (lowTariff, highTariff, ltPeriod) = tariff
    
    # initialise time
    curr_time = dt.datetime(2019,1,1,5,0,0)
    # initialise vehicle dataframe
    carData = pd.DataFrame(columns=['car','batt','inDepot','shiftIdx','shift',
                                    'kwUsed','kwDiff','kwSupplied','toRC','connection'])
    for c in range(carNum):
        carData = carData.append({
            'car': c,
            'batt': battSize,
            'inDepot': 1,
            'shiftIdx': 0,
            'shift': schedule.loc[c%len(schedule), 'shift'],
            'kwUsed': 0,
            'kwDiff': 0,
            'kwSupplied': 0,
            'toRC': 0,
            'connection': 0
        }, ignore_index=True)
    
    # FOR EVERY HOUR ...
    for t in range(0,24):
        # reset number of slow chargers and fast chargers
        cps, cpf = cps_temp, cpf_temp
        
        # FOR EVERY VEHICLE ...
        for c in range(len(carData)):
            # reset kwDiff
            carData.loc[c, 'kwDiff'] = 0
            
            # move vehicle in and out of depot based on schedule
            carData = inOutDepot(curr_time, carData, c)
            
            if carData.loc[c, 'inDepot']:
                carData, cps, cpf = charge(carData, c, battSize, cps, cpf, depotLimit)
            else:
                carData = drive(carData, c, battSize)
                
        # find minimum number of depots needed
        depotNum = math.floor(carData['kwDiff'].sum()/depotLimit)+1
        if depotNum > minDepotNum: minDepotNum = depotNum

        # prioritise charging of vehicle based on battery left
        carData = carData.sort_values(by=['batt'])
        carData = carData.reset_index(drop=True)
        
        # increment by an hour
        curr_time = curr_time + dt.timedelta(hours=1)

    # store current inputs and answers for future reference
    prev.append({
        'inputs': curr,
        'answer': (carData[['kwUsed', 'kwSupplied', 'toRC', 'connection']].sum(), minDepotNum)
    })
    
    return carData[['kwUsed', 'kwSupplied', 'toRC', 'connection']].sum(), minDepotNum