"""
turtle.py

Inherits from animal.
Implements a 2-legged animal

"""

# Imports
# -------------------------------------------------------------------------------------------------
from animal import *


# Class
# -------------------------------------------------------------------------------------------------
class Turtle(Animal):

    def __init__(self):
        # Insect is an animal
        Animal.__init__(self)     

        # With 2 legs           
        self.addPairOfLegs(Leg(Joint(0), Joint(1), 1), Leg(Joint(2), Joint(3), -1))

        # Load settings from json file
        self.loadSettings()

        # Wake the robot up slowly over a few seconds to avoid excess current draw
        self.wakeSlowly(2) 




if __name__ == "__main__":
    print("Testing Turtle")    

    c = Turtle()
    #c.log.setLevel(logging.DEBUG)

    print("Running turtle")
    c.start()
    while True:
        sleep(0.2)    