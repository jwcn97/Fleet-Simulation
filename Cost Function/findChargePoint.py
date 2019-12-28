import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
import json

def convert(eastings, northings):
    res_list_en = convert_lonlat(eastings, northings)

def findLatLong(add):
    address = requests.get("https://www.google.com/maps/search/" + add.replace(" ", "+"))
    soup = BeautifulSoup(address.content, 'html.parser')
    # search for address metadata
    address_meta = soup.find_all("meta")[7]['content']
    # get lat long data
    pt = re.search("\?center=(.*?)\&", address_meta).group(0)[8:-1]
    # split into lat and long
    return [float(x) for x in pt.split('%2C')]

def removeBracketContents(string):
    return re.sub("[\(\[].*?[\)\]]", "", string)

def scrap(address, distance):
    [latitude, longitude] = findLatLong(address)
    cpList = requests.get("https://api.openchargemap.io/v3/poi/?"+
                          "output=json"+
                          "&verbose=false"+
                          "&levelid=3"+
                          "&latitude="+str(latitude)+
                          "&longitude="+str(longitude)+
                          "&distance="+str(distance)+
                          "&distanceunit=KM"+
                          "&maxresults=100").json()

    operators = [x['OperatorInfo']['Title'] if 'OperatorInfo' in x else None for x in cpList]
    operators = [removeBracketContents(x) if x is not None else None for x in operators]
    
    ################### USAGE TYPE #########################
    payAtLocation = [x['UsageType']['IsPayAtLocation']
                     if ('UsageType' in x) and ('IsPayAtLocation' in x['UsageType']) else None for x in cpList]
    membership = [x['UsageType']['IsMembershipRequired']
                 if ('UsageType' in x) and ('IsMembershipRequired' in x['UsageType']) else None for x in cpList]
    accessKey = [x['UsageType']['IsAccessKeyRequired']
                if ('UsageType' in x) and ('IsAccessKeyRequired' in x['UsageType']) else None for x in cpList]
    
    usageCost = [x['UsageCost'].split(';')[0] if 'UsageCost' in x else None for x in cpList]
    inOperation = [x['StatusType']['IsOperational']
                   if ('StatusType' in x) and ('IsOperational' in x['StatusType']) else None for x in cpList]
    numberOfPoints = [x['NumberOfPoints'] for x in cpList]
    
    ################### ADDRESS INFO #########################
    lat = [x['AddressInfo']['Latitude'] for x in cpList]
    lon = [x['AddressInfo']['Longitude'] for x in cpList]
    distance = [x['AddressInfo']['Distance'] for x in cpList]
    
    ################### CONNECTIONS #########################
    connections = [x['Connections'] for x in cpList]
    connectionInfo = []
    amps = []
    voltages = []
    powers = []
    currentType = []
    quantities = []
    for i in range(len(connections)):
        info = [x['ConnectionType'] if 'ConnectionType' in x else None for x in connections[i]]
        connectionInfo.append([x['Title'] if x is not None else None for x in info])
        # connectionInfo.append([x['ConnectionType'] if 'ConnectionType' in x else None for x in connections[i]])
        amps.append([x['Amps'] if 'Amps' in x else None for x in connections[i]])
        voltages.append([x['Voltage'] if 'Voltage' in x else None for x in connections[i]])
        powers.append([x['PowerKW'] if 'PowerKW' in x else None for x in connections[i]])
        currentType.append([x['CurrentType']['Title'] if 'CurrentType' in x else None for x in connections[i]])
        quantities.append([x['Quantity'] if 'Quantity' in x else None for x in connections[i]])

    data = pd.DataFrame({
        'operator': operators,
        'payAtLocation': payAtLocation,
        'membershipRequired': membership,
        'accessKeyRequired': accessKey,
        'usageCost': usageCost,
        'inOperation': inOperation,
        'numberOfPoints': numberOfPoints,
        'lat': lat,
        'long': lon,
        'distance (km)': distance,
        'connectionInfo': connectionInfo,
        'amps': amps,
        'voltages': voltages,
        'powers': powers,
        'currentType': currentType,
        'connections': quantities
    })
    
    # drop null values
    data.dropna(inplace=True)
    # reset index
    return data.reset_index(drop=True)

df = scrap(input("input address here: "), 10)
df.to_excel('cps.xlsx')
print('saved successfully')