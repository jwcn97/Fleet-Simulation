import pandas as pd
import numpy as np
import datetime as dt
import time
import matplotlib.pyplot as plt
from chargingFunctions import chunks

# get simulationDF of a single car (for different algorithms)
def getCarDF(df, algo, car):
    df = df.loc[df['car'] == car]
    df['algo'] = algo
    return df

# stack and pivot the dataframe for visualisation
def DFFunction(df, col):
    DF = df.set_index(['time',col])
    DF = DF.T.stack().T
    return DF

# create x-axis hour labels
def createSlots(startTime, modulo):
    slots = []
    # show tickers only for values that are divisibly by 3 (e.g. 3,6,9...)
    for slot in range(24*5*chunks+2):
        if (slot/chunks) % modulo == 0:
            slots.append(str(int(slot/chunks + startTime) % 24))
        else:
            slots.append(None)
    return np.array(slots)

##################################################
# create graph to compare battery kW between cars
##################################################
def compareCars(folder, name, sim, algo, total_cars, company):
    testDF = DFFunction(sim, 'car')
    fig, ax = plt.subplots(figsize=(60,6))
    
    for cars in range(total_cars):
        ax.scatter(testDF.index, np.ones(len(testDF.index))*cars, 
                c=testDF['batt'].iloc[:,cars], cmap="Greens", vmin=-11, vmax=35, 
                s=(testDF['batt'][cars]**2.1).apply(int))

    for time in range(len(testDF.index)):
        alphaVal = 0.7 if time/chunks % 24 == 0 else 0.2
        # draw vertical lines to indicate hours
        # line indicating days will have more weight
        ax.axvline(x=testDF.index[time], ymin=-1, ymax=1, 
                color='black', linestyle='-', lw=0.7, alpha=alphaVal)

        # label RC and Wait events
        for k in range(total_cars):
            if testDF['event'].iloc[time,k] == 'RC':
                ax.scatter(testDF.index[time], k, c='red', s=(testDF['batt'].iloc[time+1,k]**2.1))
            elif testDF['event'].iloc[time,k] == 'wait':
                ax.scatter(testDF.index[time], k, c='#fcbe03', s=(testDF['batt'].iloc[time,k]**2.1))

    # mark the green zone (cheap to charge)
    if company == 'BritishGas':
        ax.axvspan(testDF.index[0*chunks], testDF.index[1*chunks], facecolor='b', alpha=0.2)
        ax.axvspan(testDF.index[(5*24-5)*chunks], testDF.index[(5*24-1)*chunks], facecolor='b', alpha=0.2)
        for day in range(1, 5):
            ax.axvspan(testDF.index[(day*24-5)*chunks], testDF.index[(day*24+1)*chunks], facecolor='b', alpha=0.2)
    elif company == 'OriginalTest':
        ax.axvspan(testDF.index[(5*24-6)*chunks], testDF.index[(5*24-1)*chunks], facecolor='b', alpha=0.2)
        for day in range(1, 5):
            ax.axvspan(testDF.index[(day*24-6)*chunks], testDF.index[(day*24)*chunks], facecolor='b', alpha=0.2)

    ax.yaxis.set_ticks(np.arange(0,total_cars,1))
    ax.xaxis.set_ticks(testDF.index)
    ax.set_xticklabels(createSlots(6, 3), fontdict={'fontsize':18})
    ax.set_xlim([testDF.index[0]-dt.timedelta(hours=1), testDF.index[-1]+dt.timedelta(hours=1)])
    
    ax.set_title('Charge (kW)', {'fontsize': 20})
    plt.savefig(folder + name + '_' + algo + '_charge.png')
    plt.close('all')

#########################################################
# create graph to compare battery kW between algorithms
#########################################################
def compareAlgo(folder, name, sim, car, total_algos, company):
    testDF = DFFunction(sim, 'algo')
    fig, ax = plt.subplots(figsize=(60,6))
    
    for cars in range(total_algos):
        ax.scatter(testDF.index, np.ones(len(testDF.index))*cars, 
                c=testDF['batt'].iloc[:,cars], cmap="Greens", vmin=-11, vmax=35, 
                s=(testDF['batt'].iloc[:,cars]**2.1).apply(int))

    for time in range(len(testDF.index)):
        alphaVal = 0.7 if time/chunks % 24 == 0 else 0.2
        lwVal = 1.1 if time/chunks % 24 == 0 else 0.7
        # draw vertical lines to indicate hours
        # line indicating days will have more weight
        ax.axvline(x=testDF.index[time], ymin=-1, ymax=1, 
                color='black', linestyle='-', lw=lwVal, alpha=alphaVal)
        
        # label RC and Wait events
        # shade regions of time where vehicle is outside driving
        for k in range(total_algos):
            if testDF['event'].iloc[time,k] == 'RC':
                ax.scatter(testDF.index[time], k, c='red', s=(testDF['batt'].iloc[time+1,k]**2.1))
                ax.axvspan(testDF.index[time], testDF.index[time+1], facecolor='r', alpha=0.1)
            elif testDF['event'].iloc[time,k] == 'wait':
                ax.scatter(testDF.index[time], k, c='#fcbe03', s=(testDF['batt'].iloc[time,k]**2.1))
            elif testDF['event'].iloc[time,k] == 'drive':
                ax.axvspan(testDF.index[time], testDF.index[time+1], facecolor='r', alpha=0.1)

    # mark the green zone (cheap to charge)
    if company == 'BritishGas':
        ax.axvspan(testDF.index[0*chunks], testDF.index[1*chunks], facecolor='b', alpha=0.2)
        ax.axvspan(testDF.index[(5*24-5)*chunks], testDF.index[(5*24-1)*chunks], facecolor='b', alpha=0.2)
        for day in range(1, 5):
            ax.axvspan(testDF.index[(day*24-5)*chunks], testDF.index[(day*24+1)*chunks], facecolor='b', alpha=0.2)
    elif company == 'OriginalTest':
        ax.axvspan(testDF.index[(5*24-6)*chunks], testDF.index[(5*24-1)*chunks], facecolor='b', alpha=0.2)
        for day in range(1, 5):
            ax.axvspan(testDF.index[(day*24-6)*chunks], testDF.index[(day*24)*chunks], facecolor='b', alpha=0.2)

    ax.yaxis.set_ticks(np.arange(0,total_algos,1))
    ax.set_yticklabels(np.array(['BATT','COST','DUMB','LEAVETIME','SMART']), fontdict={'fontsize':18})
    ax.set_ylabel('Algorithms', fontdict={'fontsize':18})
    
    ax.xaxis.set_ticks(testDF.index)
    ax.set_xticklabels(createSlots(6, 3), fontdict={'fontsize':18})
    ax.set_xlabel('Hours', fontdict={'fontsize':18})
    ax.set_xlim([testDF.index[0]-dt.timedelta(hours=1), testDF.index[-1]+dt.timedelta(hours=1)])
    
    ax.set_title('Charge of Car:' + '_car' + str(car) + ' (kW)', {'fontsize': 20})
    plt.savefig(folder + name + '_car' + str(car) + '_charge.png')
    plt.close('all')
