# Functions for easing
# Allows us to move motors in a more organic way, with the speed varying during the movement according to the easing function used

def easeLinear(t):
    return t

def easeAccelerating(t):
    return t*t*t*t

def easeInOutQuad(t):
    if t<.5:
        e = 2*t*t
    else: 
        e = -1+(4-2*t)*t
    return e

def easeInOutQuart(t):
    if t<.5:
        e = 8*t*t*t*t
    else: 
        t = t -1
        e = 1-8*(t)*t*t*t
    return e
