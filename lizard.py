"""
lizard.py

Inherits from animal.
Implements a 4-legged animal

"""

# Imports
# -------------------------------------------------------------------------------------------------
from random_animal import *


# Class
# -------------------------------------------------------------------------------------------------
class Lizard(RandomAnimal):

    def __init__(self):
        # Lizard is an animal
        RandomAnimal.__init__(self)     

        # With 4 legs           
        self.addPairOfLegs(Leg(Joint(0), Joint(1), 1), Leg(Joint(2), Joint(3), -1))
        self.addPairOfLegs(Leg(Joint(4), Joint(5), 1), Leg(Joint(6), Joint(7), -1))

        # Load settings from json file
        self.loadSettings()

        # Wake the robot up slowly over a few seconds to avoid excess current draw
        self.wakeSlowly(2) 




if __name__ == "__main__":
    print("Testing Lizard")    

    c = Lizard()
    #c.log.setLevel(logging.DEBUG)

    print("Running lizard")
    c.start()
    while True:
        sleep(0.2)    