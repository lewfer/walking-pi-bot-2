"""
turtle.py

Inherits from animal.
Implements a 2-legged animal, adding additional behaviours

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

        # Set defaults if none
        if not 'TURTLEREACHSPEED' in self.settings: self.settings['TURTLEREACHSPEED'] = 1
        if not 'TURTLEPUSHSPEED' in self.settings: self.settings['TURTLEPUSHSPEED'] = 1
        if not 'TURTLEPUSHDELAY' in self.settings: self.settings['TURTLEPUSHDELAY'] = 0
        if not 'RANDOMWAIT' in self.settings: self.settings['RANDOMWAIT'] = 2    
        if not 'STEPSPERDEGREE' in self.settings: self.settings['STEPSPERDEGREE'] = 1

    def factoryReset(self):
        Animal.factoryReset(self)
        self.settings['TURTLEREACHSPEED'] = 1
        self.settings['TURTLEPUSHSPEED'] = 1
        self.settings['TURTLEPUSHDELAY'] = 0
        self.settings['RANDOMWAIT'] = 2    
        self.settings['STEPSPERDEGREE'] = 1


    def waitRandom(self):
        '''Wait for a random time (in tenths of a second)'''

        sleep(random.randint(0,self.settings['RANDOMWAIT'])/10.0) 

    """
    def forwardTurtle(self):
        '''Move forward in a turtle motion'''
                
        self.stopped = False

        while True:
            t = self.settings['TURTLEREACHSPEED']

            # Move front limbs, one at a time
            self.runOnThread('L0', 'reachForward', {'t':t})
            self.joinThreads(['L0'])
            self.waitRandom() 
            self.runOnThread('R0', 'reachForward', {'t':t})
            self.joinThreads(['R0'])
            self.waitRandom() 

            # Push all limbs together
            self.runOnThread('L0', 'pushBackward', {'t':t})
            self.runOnThread('R0', 'pushBackward', {'t':t})
            sleep(self.settings['TURTLEPUSHDELAY'])
            self.joinThreads(['L0','R0'])

            # If request was made to end walk, break out of loop
            if self.stopped:
                break 

    def backwardTurtle(self):
        '''Move backward in a turtle motion'''
                
        self.stopped = False

        while True:
            t = self.settings['TURTLEREACHSPEED']

            # Move front limbs, one at a time
            self.runOnThread('L0', 'reachBackward', {'t':t})
            self.joinThreads(['L0'])
            self.waitRandom() 
            self.runOnThread('R0', 'reachBackward', {'t':t})
            self.joinThreads(['R0'])
            self.waitRandom() 

            # Push all limbs together
            self.runOnThread('L0', 'pushForward', {'t':t})
            self.runOnThread('R0', 'pushForward', {'t':t})
            sleep(self.settings['TURTLEPUSHDELAY'])
            self.joinThreads(['L0','R0'])

            # If request was made to end walk, break out of loop
            if self.stopped:
                break  

    def rightTurtle(self):
        '''Move right in a turtle motion'''
                
        self.stopped = False

        while True:
            t = self.settings['TURTLEREACHSPEED']

            # Move front limbs, one at a time
            self.runOnThread('L0', 'reachBackward', {'t':t})
            self.joinThreads(['L0'])
            self.waitRandom() 
            self.runOnThread('R0', 'reachForward', {'t':t})
            self.joinThreads(['R0'])
            self.waitRandom() 

            # Push all limbs together
            self.runOnThread('L0', 'pushForward', {'t':t})
            self.runOnThread('R0', 'pushBackward', {'t':t})
            sleep(self.settings['TURTLEPUSHDELAY'])
            self.joinThreads(['L0','R0'])

            # If request was made to end walk, break out of loop
            if self.stopped:
                break  

    def leftTurtle(self):
        '''Move left in a turtle motion'''
                
        self.stopped = False

        while True:
            t = self.settings['TURTLEREACHSPEED']

            # Move front limbs, one at a time
            self.runOnThread('L0', 'reachForward', {'t':t})
            self.joinThreads(['L0'])
            self.waitRandom() 
            self.runOnThread('R0', 'reachBackward', {'t':t})
            self.joinThreads(['R0'])
            self.waitRandom() 

            # Push all limbs together
            self.runOnThread('L0', 'pushBackward', {'t':t})
            self.runOnThread('R0', 'pushForward', {'t':t})
            sleep(self.settings['TURTLEPUSHDELAY'])
            self.joinThreads(['L0','R0'])

            # If request was made to end walk, break out of loop
            if self.stopped:
                break     

    def forwardInsect(self):
        '''Move forward with an insect motion.  Right side moves forward (reach forward, push backward), left side moves forward (reach forward, push backward)'''

        self.stopped = False
        t = 2

        while True:
            self.log.info("forwardInsect")
            # Start L0
            self.runOnThread('R0', 'pushBackward', {'t':t})
            self.runOnThread('L0', 'reachForward', {'t':t/4})

            # Start R0
            self.runOnThread('L0', 'pushBackward', {'t':t})
            self.runOnThread('R0', 'reachForward', {'t':t/4})

            # If request was made to end walk, break out of loop
            if self.stopped:
                self.log.info("Stopped forwardInsect")
                break                      

    def backwardInsect(self):
        '''Move backward with an insect motion.  Right side moves backward (reach backward, push forward), left side moves backward (reach backward, push forward)'''

        self.stopped = False
        t = 2

        while True:
            self.log.info("backwardInsect")
            # Start L0
            self.runOnThread('R0', 'pushForward', {'t':t})
            self.runOnThread('L0', 'reachBackward', {'t':t/4})

            # Start R0
            self.runOnThread('L0', 'pushForward', {'t':t})
            self.runOnThread('R0', 'reachBackward', {'t':t/4})

            # If request was made to end walk, break out of loop
            if self.stopped:
                self.log.info("Stopped backwardInsect")
                break      

    def leftInsect(self):
        '''Move left with an insect motion.  Right side moves forward (reach forward, push backward), left side moves backward (reach backward, push forward)'''

        self.stopped = False
        t = 2

        while True:
            self.log.info("leftInsect")
            # Start L0
            self.runOnThread('R0', 'pushBackward', {'t':t})
            self.runOnThread('L0', 'reachBackward', {'t':t/4})

            # Start R0
            self.runOnThread('L0', 'pushForward', {'t':t})
            self.runOnThread('R0', 'reachForward', {'t':t/4})

            # If request was made to end walk, break out of loop
            if self.stopped:
                self.log.info("Stopped leftInsect")
                break      

    def rightInsect(self):
        '''Move right with a insect motion.  Left side moves forward (reach forward, push backward), right side moves backward (reach backward, push forward)'''

        self.stopped = False
        t = 2

        while True:
            self.log.info("rightInsect")
            # Start L0
            self.runOnThread('R0', 'pushForward', {'t':t})
            self.runOnThread('L0', 'reachForward', {'t':t/4})

            # Start R0
            self.runOnThread('L0', 'pushBackward', {'t':t})
            self.runOnThread('R0', 'reachBackward', {'t':t/4})

            # If request was made to end walk, break out of loop
            if self.stopped:
                self.log.info("Stopped rightInsect")
                break      

    def point(self):
        '''Point'''

        self.stopped = False
        t = 2

        while True:

            # Get settings for the leg
            settings = self.settings["leg_ranges"][0]

            kneeOffsetFromMid = 60
            jitter = 5 # !! param

            # Set left leg position, with jitter
            angles = (settings["left"]["hip"][2]+random.randint(-jitter,jitter), settings["left"]["knee"][LEG_MID]+kneeOffsetFromMid+random.randint(-jitter,jitter))
            self.runOnThread('L0', 'setAngles', {'angles':angles,'t':t})
            
            # Set right leg position, with jitter
            angles = (settings["right"]["hip"][2]+random.randint(-jitter,jitter), settings["right"]["knee"][LEG_MID]-kneeOffsetFromMid+random.randint(-jitter,jitter))
            self.runOnThread('R0', 'setAngles', {'angles':angles,'t':t})
            self.joinThreads(['L0','R0'])

            # If request was made to end walk, break out of loop
            if self.stopped:
                self.log.info("Stopped point")
                break                        

    def eat(self):
        '''Eat'''
        self.log.info("eat")

        self.stopped = False
        t = 2

        while True:

            # Get settings for the leg
            settings = self.settings["leg_ranges"][0]

            jitter = 10 # !! param

            # Set left leg position, with jitter.  Hip to the front, knee to mid.
            angles = (settings["left"]["hip"][LEG_FRONT]+random.randint(-jitter,jitter), settings["left"]["knee"][LEG_MID]+random.randint(-jitter,jitter))
            self.runOnThread('L0', 'setAngles', {'angles':angles,'t':t})
            
            # Set right leg position, with jitter.  Hip to the front, knee to mid.
            angles = (settings["right"]["hip"][LEG_FRONT]+random.randint(-jitter,jitter), settings["right"]["knee"][LEG_MID]+random.randint(-jitter,jitter))
            self.runOnThread('R0', 'setAngles', {'angles':angles,'t':t})
            self.joinThreads(['L0','R0'])

            # If request was made to end walk, break out of loop
            if self.stopped:
                self.log.info("Stopped eat")
                break                                    
"""


if __name__ == "__main__":
    print("Testing Turtle")    

    #from threading import active_count

    c = Turtle()
    #c.log.setLevel(logging.DEBUG)

    """
    def run(fn):
        print("Threads:",activeCount())
        print(fn)
        thread = Thread(target=eval("c."+fn))
        thread.name = "Test:" + fn
        thread.start()
        sleep(10)
        c.stop()
        thread.join()
        printThreads(c.log)

    run("forwardTurtle")
    run("backwardTurtle")
    run("leftTurtle")    
    run("rightTurtle")

    run("forwardInsect")
    run("backwardInsect")
    run("leftInsect")    
    run("rightInsect")    
    """

    print("Running turtle")
    c.start()
    while True:
        sleep(0.2)    