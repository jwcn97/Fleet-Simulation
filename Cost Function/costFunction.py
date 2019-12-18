import pandas as pd
import numpy as np

# purpose: to help conversion from DIESEL -> EV
# next steps:
# 1) more complicated schedule input, then compute max rate needed in depot => max cp needed
# 2) mileage / dwell time to see how many vehicles we are able to charge in depot

"""
Disclaimer: all calculations are done in a 1-day window period
"""
def costFunction(cpsNum, cpfNum, days, carNum):
    # OCTOPUS: (12:30 ~ 16:30), LT price: £0.05, HT price: £0.14
    # ECOTRICITY: RC price: £0.39

    battSize = 40

    ########################### DRIVING ###########################
    # ASSUME schedules are the same for all vehicles in the fleet
    mileage, mpkw = 16, 4
    drivingHours = 10.5
    kwUsed = carNum * mileage/mpkw * drivingHours

    ########################### DEPOT ###########################
    # ASSUME that charge available in the depot is fully utilised
    depotHours = 24 - drivingHours
    chargeCapacity = (cpsNum * 3 + cpfNum * 7) * depotHours

    ########################### CHARGE POINT ###########################
    # ASSUME supply < demand, any excess is topped up by RC outside depot
    if kwUsed < chargeCapacity:
        toRC = 0
        toCharge = kwUsed
    else:
        toRC = kwUsed - chargeCapacity
        toCharge = chargeCapacity

    ########################### RAPID CHARGING ###########################
    rcRate = 22
    rcHours = toRC/rcRate
    usefulHrs =  (carNum * drivingHours) - rcHours

    ########################### CALCULATE COST ###########################
    # FIXED
    infraCost = (cpsNum * 300) + (cpfNum * 800) + (carNum * 30000)

    # VARIABLE
    chargeTariff = 0.14
    rcTariff = 0.39
    if toRC > 0: connectionFee = toRC/battSize
    else:        connectionFee = 0
    revRate = 55

    chargeCost = carNum * toCharge * chargeTariff
    rcCost = toRC * rcTariff + connectionFee
    rev = usefulHrs * revRate

    return infraCost + days*(chargeCost + rcCost - rev)

def gradient_descent(days, cars):
    # set limits
    start_cps, end_cps = 1, 20
    start_cpf, end_cpf = 1, 20
    # set minimum
    min_cps = start_cps
    min_cpf = start_cpf
    min_cost = costFunction(start_cps, start_cpf, days, cars)

    # Run the gradient
    for cpsNum in range(start_cps, end_cps+1):
        for cpfNum in range(start_cpf, end_cpf+1):
            # depot supply limit
            if cpsNum * 3 + cpfNum * 7 <= 40:
                # compute cost
                cost = costFunction(cpsNum, cpfNum, days, cars)
                # update values if min is found
                if cost < min_cost:
                    min_cps, min_cpf = cpsNum, cpfNum
                    min_cost = cost
    
    # Return minimum combination of values
    return min_cps, min_cpf, min_cost

display = pd.DataFrame(columns=['simulation days', 'number of cars', 'number of slow charge points', 'number of fast charge points', 'minimum cost'])

# define limits
min_days, max_days = 15, 100
min_cars, max_cars = 5, 30

for days in range(min_days, max_days+1):
    for cars in range(min_cars, max_cars+1):
        cps, cpf, cost = gradient_descent(days, cars)
        display = display.append({
            'simulation days': days,
            'number of cars': cars,
            'number of slow charge points': cps,
            'number of fast charge points': cpf,
            'minimum cost': cost
        }, ignore_index=True)

# print(display)

display.to_csv('test2.csv')