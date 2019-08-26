import pandas as pd
import numpy as np
import datetime as dt
import time
import matplotlib.pyplot as plt

def getCarDF(df, algo, car):
    df = df.loc[df['car'] == car]
    df['algo'] = algo
    return df

def DFFunction(df, col):
    DF = df.set_index(['time',col])
    DF = DF.T.stack().T
    return DF

def createSlots(startTime, modulo):
    slots = []
    for slot in range(122):
        if slot % modulo == 0: slots.append(str((slot+startTime)%24))
        else:                  slots.append(None)
    return np.array(slots)

def compareCars(folder, name, sim, algo, total_cars):
    testDF = DFFunction(sim, 'car')
    fig, ax = plt.subplots(figsize=(60,6))
    
    for i in range(total_cars):
        ax.scatter(testDF.index, np.ones(len(testDF.index))*i, 
                    c=testDF['batt'].iloc[:,i], cmap="Greens", vmin=-11, vmax=35, 
                    s=(testDF['batt'][i]**2.1).apply(int))

    for j in range(len(testDF.index)):
        alphaVal = 0.7 if j % 24 == 0 else 0.2
        ax.axvline(x=testDF.index[j], ymin=-1, ymax=1, 
                    color='black', linestyle='-', lw=0.7, alpha=alphaVal)
        for k in range(total_cars):
            # label RC and Wait events
            if testDF['event'].iloc[j,k] == 'RC':
                ax.scatter(testDF.index[j], k, c='red', s=(testDF['batt'].iloc[j+1,k]**2.1))
            elif testDF['event'].iloc[j,k] == 'wait':
                ax.scatter(testDF.index[j], k, c='#fcbe03', s=(testDF['batt'].iloc[j,k]**2.1))

    # mark the green zone (cheap to charge)
    ax.axvspan(testDF.index[0], testDF.index[1], facecolor='b', alpha=0.2)
    ax.axvspan(testDF.index[5*24-5], testDF.index[5*24-1], facecolor='b', alpha=0.2)
    for i in range(1, 5):
        ax.axvspan(testDF.index[i*24-5], testDF.index[i*24+1], facecolor='b', alpha=0.2)

    ax.yaxis.set_ticks(np.arange(0,total_cars,1))
    ax.xaxis.set_ticks(testDF.index)
    ax.set_xticklabels(createSlots(6, 3), fontdict={'fontsize':18})
    ax.set_xlim([testDF.index[0]-dt.timedelta(hours=1), testDF.index[-1]+dt.timedelta(hours=1)])
    
    ax.set_title('Charge (kW)', {'fontsize': 20})
    plt.savefig(folder + name + '_' + algo + '_charge.png')
    plt.close('all')
    
def compareAlgo(folder, name, sim, car, total_algos):
    testDF = DFFunction(sim, 'algo')
    fig, ax = plt.subplots(figsize=(60,6))
    
    for i in range(total_algos):
        ax.scatter(testDF.index, np.ones(len(testDF.index))*i, 
                   c=testDF['batt'].iloc[:,i], cmap="Greens", vmin=-11, vmax=35, 
                   s=(testDF['batt'].iloc[:,i]**2.1).apply(int))

    for time in range(len(testDF.index)):
        alphaVal = 0.7 if time % 24 == 0 else 0.2
        lwVal = 1.1 if time % 24 == 0 else 0.7
        ax.axvline(x=testDF.index[time], ymin=-1, ymax=1, 
                   color='black', linestyle='-', lw=lwVal, alpha=alphaVal)
        
        for k in range(total_algos):
            # label RC and Wait events
            if testDF['event'].iloc[time,k] == 'RC':
                ax.scatter(testDF.index[time], k, c='red', s=(testDF['batt'].iloc[time+1,k]**2.1))
            elif testDF['event'].iloc[time,k] == 'wait':
                ax.scatter(testDF.index[time], k, c='#fcbe03', s=(testDF['batt'].iloc[time,k]**2.1))

    # mark the green zone (cheap to charge)
    ax.axvspan(testDF.index[0], testDF.index[1], facecolor='b', alpha=0.2)
    ax.axvspan(testDF.index[5*24-5], testDF.index[5*24-1], facecolor='b', alpha=0.2)
    for i in range(1, 5):
        ax.axvspan(testDF.index[i*24-5], testDF.index[i*24+1], facecolor='b', alpha=0.2)

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
