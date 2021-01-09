from turtle import Turtle
from leg import Leg
from joint import Joint

# Create animal
animal = Turtle()

# With 2 legs           
animal.addPairOfLegs(Leg(Joint(0), Joint(1), 1), Leg(Joint(2), Joint(3), -1))

def set90Degrees():
    '''Set all motors to 90 degrees'''
    animal.legPairs[0].left.knee.moveDirectTo(90)
    animal.legPairs[0].left.hip.moveDirectTo(90)
    animal.legPairs[0].right.knee.moveDirectTo(90)
    animal.legPairs[0].right.hip.moveDirectTo(90)

set90Degrees()