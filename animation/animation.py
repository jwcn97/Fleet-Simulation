import numpy as np
import pandas as pd
import pylab as plt
import matplotlib as mpl
import scipy as sp
import random as rd
import time as tm

#----------------------------------------------------------------------
# INPUT DATA
data = pd.read_excel('output.xlsx')

#----------------------------------------------------------------------
# PARAMETERS SETUP
total_cars = 4
rapid_charges, idle_cases = 0, 0

width = int(total_cars*25.25)
height = int(total_cars*25.25)
i = int((width-total_cars/4)/total_cars)
j = int((height-total_cars/4)/total_cars)

battSize = int(data.iloc[2,total_cars+1])
print(battSize)
max_time = len(data)-2
chunks = int(max_time/5/24)
start = int(input("start index: "))*chunks
start = start if start < max_time else max_time-1*chunks
end = int(input("end index: "))*chunks
end = end if end > start and end <= max_time else max_time
time_delay = 0.2

#-----------------------------------------------------------------------
# VISUALISATION SETUP

# sorts out the colours in the animation (as rgb values)
# The first element ("x") defines interpolation intervals over the full range of 0 to 1, and it must span that whole range.
# In other words, the values of x divide the 0-to-1 range into a set of segments, and y gives the end-point color values for each segment.

cdict = {       # color1: white,   color2: black,   color3: blue,   color4: yellow,   color5: green,   color6: orange
    'red'  :  ( (0.0, 1.0, 1.0), (0.2, 0.0, 0.0), (0.4, 0.0, 0.0), (0.6, 0.5, 0.5), (0.8, 0.0, 0.0), (1.0, 255./256, 255./256)),
    'green':  ( (0.0, 1.0, 1.0), (0.2, 0.0, 0.0), (0.4, 0.0, 0.0), (0.6, 0.5, 0.5), (0.8, 1.0, 1.0), (1.0, 160./256, 160./256)),
    'blue' :  ( (0.0, 1.0, 1.0), (0.2, 0.0, 0.0), (0.4, 1.0, 1.0), (0.6, 0.0, 0.0), (0.8, 0.0, 0.0), (1.0, 0.0, 0.0))
}

# set states
empty, grid, batt_lvl, idle, depo_empty, depo_used = range(6)
RC = depo_used # the colours being used are the same

def visualise(figure, matrix, time, cm, index):
    figure
    plt.cla()                                       # Clear whatever was on the plot before
    plt.pcolor(matrix.T, vmin=0, vmax=5, cmap=cm)   # Draw the figure
    plt.axis('square')                              # Set the scale of x and y as equal
    
    timeStr = "Day" + str(time)[9:]
    spaces = 11
    timeStr1 = timeStr.rjust(len(timeStr)+spaces)   # add spaces to the left
    timeStr2 = timeStr1.ljust(len(timeStr1)+spaces) # add spaces to the right
    plt.title("DEPOT" + timeStr2 + "DRIVE",          # set title
              fontweight='bold',
              fontsize=17)
    
    # set total cost label
    label = data.iloc[(index+2),(total_cars+5)]
    plt.text(54, 53, "Total Cost:", color='white', fontsize=15)
    plt.text(58, 46, "£"+str(label), color='white', fontsize=15)
    
    # set battery label for each car
    for x in range(total_cars):
        label = data.iloc[(index+2),(x+total_cars+1)]
        plt.text(34, 14+x*25, "car "+str(x), color='white', fontsize=15)
        plt.text(31, 9+x*25, str(label)+" kW", color='white', fontsize=15)
        
    figure.canvas.draw()                            # Update the plot on the screen:
    figure.canvas.flush_events()

#-----------------------------------------------------------------------
# GRAPH SETUP

# Turn on interactive plotting (to animate the simulation)
plt.ion()
# Create the figure on which to plot
fig1 = plt.figure(num=1, figsize=(total_cars*2,total_cars*2))
# Show the figure (empty at the moment)
fig1.clear()
plt.show()
# allow for live updating
fig1.canvas.draw()
fig1.canvas.flush_events()

##################################
# START OF SIMULATION
##################################
cm = mpl.colors.LinearSegmentedColormap('my_colormap', cdict, 1024)
matrix = sp.zeros([width, height])

# Create grids
for x in range(width):    # Go through the cells from left to right
    for y in range(height):    # And from top to bottom
        random = rd.random()       # Pick a random number
        matrix[x,y] = grid

# Create horizontal and vertical row thinning by emptying out rows
constanti, constantj = i, j
while i<width:
    matrix[0:width,i] = empty
    i += constanti
while j<height:
    matrix[j,0:height] = empty
    j += constantj
i, j = constanti, constantj

# Define areas with white borders
matrix[0:width,0] = empty
matrix[0:width,height-1] = empty
matrix[0,0:height] = empty
matrix[width-1,0:height] = empty

# Start the timer
for index in range(start, end):
    time = data.iloc[index+2,0]
    for car in range(total_cars):
        event = data.iloc[(index+2),(car+1)]
        batt = data.iloc[(index+2),(car+total_cars+1)]
        lvl = int(batt*20/battSize)

        # move vehicle
        state = None
        if event == 'drive':
            state = depo_empty
            matrix[3:i-2, (car*j+3):(car*j+j-2)] = grid                   # set depo to unoccupied
            matrix[width-i+2:width-3, (car*j+3+lvl):(car*j+j-2)] = grid   # reset area outside depo not occupied by battery
            matrix[width-i+2:width-3, (car*j+3):(car*j+3+lvl)] = batt_lvl # set battery level outside depo
        elif event == 'RC':
            state = depo_empty
            rapid_charges += 1                                            # update rapid charge cases
            matrix[3:i-2, (car*j+3):(car*j+j-2)] = grid                   # remove vehicle from inside depo
            matrix[width-i+10:width-11,(car*j+11):(car*j+j-4)] = RC       # flag the RC grid with exclamation mark
            matrix[width-i+10:width-11,(car*j+5):(car*j+9)] = RC
        elif event == 'wait' or event == 'full':
            state = depo_used
            idle_cases += 1                                               # update idle cases
            matrix[3:i-2, (car*j+3):(car*j+3+lvl)] = idle                 # set battery level inside depo
            matrix[width-i+2:width-3, (car*j+3):(car*j+j-2)] = grid       # remove vehicle from outside depo
        elif event == 'charge':
            state = depo_used
            matrix[3:i-2, (car*j+3):(car*j+3+lvl)] = batt_lvl             # set battery level inside depo
            matrix[width-i+2:width-3, (car*j+3):(car*j+j-2)] = grid       # remove vehicle from outside depo

        # change depo state        
        matrix[1:i, (car*j+1):(car*j+3)] = state    # color bottom line
        matrix[1:i, (car*j+j-2):(car*j+j)] = state  # color top line
        matrix[1:3, (car*j+1):(car*j+j)] = state    # color left line
        matrix[i-2:i, (car*j+1):(car*j+j)] = state  # color right line

    # Draw the picture
    visualise(fig1, matrix, time, cm, index)
    # Apply the time delay
    plt.pause(time_delay)
    
print("========================================")
print("rapid charges = " + str(rapid_charges))
print("idle cases = " + str(idle_cases))
print("========================================")
input("Enter to exit")