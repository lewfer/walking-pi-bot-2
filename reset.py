from turtle import *
from lizard import *
from leg import Leg
from joint import Joint

# Work out the mode - default to Turtle
mode = "Turtle"
try:
    f = open("mode.txt", "r")
    mode = f.read()
    mode = mode.strip()
except Exception:
    pass
print("Mode",mode)

# Create animal
animal = eval(mode+"()")

def set90Degrees():
    for legPair in animal.legPairs:
        '''Set all motors to 90 degrees'''
        legPair.left.knee.moveDirectTo(90)
        legPair.left.hip.moveDirectTo(90)
        legPair.right.knee.moveDirectTo(90)
        legPair.right.hip.moveDirectTo(90)

set90Degrees()