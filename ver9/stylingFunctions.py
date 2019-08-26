######################################
# FOR COLOURING CELLS IN SIMULATION DF
######################################

def crColour(val):
    if val > 0: color = 'green'
    elif val == 0: color = 'green'
    else: color = 'red'
    return 'color: %s' % color

def crBackground(val):
    if val > 0: color = '#adfc83'
    elif val == 0: color = '#daed0c'
    else: color = '#fab9b9'
    return 'background-color: %s' % color

def eventBackground(val):
    if val == 'full': color = '#00b200'
    elif val == 'charge': color = '#adfc83'
    elif val == 'drive': color = '#fab9b9'
    elif val == 'wait': color = '#daed0c'
    elif val == 'RC': color = 'red'
    else: color = None
    return 'background-color: %s' % color

def styleDF(df,col):
    DF = df.set_index(['time','totalCost',col])
    DF = DF.T.stack().T
    DF = DF.style.\
        applymap(crColour, subset=['chargeDiff']).\
        applymap(crBackground, subset=['chargeDiff']).\
        applymap(eventBackground, subset=['event'])
    return DF