"""
animal.py

Implementation of Animal class.
An Animal is a robot with a number of pairs of legs.

Each leg will have one and only one thread running movements at a time.  
This prevents multiple threads trying to move a single servo at the same time, which causes erratic movements. 

Animal settings are stored in a json file.

You can run specific behaviours, e.g. animal.forward().

You can also start its random movement mode by calling animal.start()
"""

# Imports
# -------------------------------------------------------------------------------------------------
from animal import Animal

from leg import Leg
from joint import Joint

from threadhelper import *

import random

from time import sleep
"""
from threadhelper import *
from joint import *
import curses
import json
import logging
import sys
from head import Head
from gpiozero import Button
"""

    

# Class
# -------------------------------------------------------------------------------------------------
class RandomAnimal(Animal):
    '''Animal has a number of pairs of legs'''

    def __init__(self):

        Animal.__init__(self)

        # Flag to indicate when we last saw a human
        self.lastHumanDetectAge = -999

        # Manage current and next action
        self._currentAction = None              # current action being run (one-letter code)
        self._timerDelay = 0                    # delay before next action runs
        self._timerAction = None                # action to run next (one-letter code)
        self._timerAgeStart = 0                 # age of robot when timer was started
        self._interruptId = None                # the current interrupt, if any
        self._interruptValue = None             # value associated with the interrupt
        self._interruptBeingHandled = None      # if we are currently executing the interrupt handling action

        # Random action generator
        self._randomThread = None        # thread on which random action generator runs
        self._runningRandom = False      # flag to indicate that random thread is running

        self._threadCount = 0                   # so we can track threads


        # List of one-letter action codes and the associated actions
        self.actionFunction = {
            '*':'do_default()',
            'F':'do_forward()', 
            'B':'do_backward()',
            'L':'do_left()',
            'R':'do_right()',
            'l':'do_backLeft()',
            'r':'do_backRight()',
            'W':'do_wait()',
            'U':'do_unwind()',
            'P':'do_point()',
            'E':'do_eat()',
            'S':'do_sit()',
            '^':'do_kneesup()',
            'v':'do_kneesdown()',
            '<':'do_hipsbackward()',
            '>':'do_hipsforward()',
            'A':'do_alert()',
            '+':'do_run()',
            '-':'do_crawl()',
            'I':'endInterrupt()',
            'M':'do_detectMovement()',
            'T':'do_trackMovement()'
            }




    # Settings 
    # ---------------------------------------------------------------------------------------------

    def setDefaultSettings(self):

        Animal.setDefaultSettings(self)   

        # Weights for random movement action choices
        #                                 ['.','S','B','L','R','U','P','E','A','+','-']
        self.settings['RANDOMWEIGHTS'] = [  40, 10, 1,  3,  3,  2,  2,  1,  1,  20,  1]

        # Min/max time for action to run
        self.settings['RANDOMTIME'] = {'B':[2,8],'L':[2,6],'R':[2,6],'S':[2,30],'P':[2,30],'E':[2,30],'A':[2,30],'U':[5,50],'M':[10,20],'T':[10,20],'+':[20,30],'-':[2,10]}

        # Number of seconds to wait before generating another random action
        self.settings['TICKPERIOD'] = 1

        # Number of alertness points to add for each tick when the animal is unwinding
        self.settings['UNWINDALERTNESSINCREASE'] = 5

        # Head movement range in degrees
        self.settings['HEADHIGHANGLE'] = 135
        self.settings['HEADLOWANGLE'] = 45
        self.settings['HEADMIDANGLE'] = 90

        # Change in head angle when tracking
        self.settings['HEADTRACKDELTA'] = 10

        # Sensor thresholds
        self.settings['SHORTDISTANCE'] = 30     # triggers short-distance interrupt when distance less than this
        self.settings['LONGDISTANCE'] = 200     # triggers long-distance interrupt when distance more than this
        self.settings['HUMANDETECTMIN'] = 24    # triggers human-detect interrupt when heat between min and max
        self.settings['HUMANDETECTMAX'] = 30    # triggers human-detect interrupt when head between min and max







    # Handlers for actions 
    # ---------------------------------------------------------------------------------------------

    def do_default(self):
        """Do the default action, which is to look around and move off left, right or forward"""
        print("Do default")

        # Stop movements ready for scan
        self.stopCurrentAction()

        # Do a scan (move head from side-to-side) looking for short distances
        self.log.info("\tScanning")
        self.head.pauseSensors()   # pause sensors while we scan
        #distances, minpos, maxpos, movement = self.head.scan()
        minPos, minDist, maxPos, maxDist, minLeftDist, minRightDist, maxLeftDist, maxRightDist, movement = self.head.scan()
        print("\tScan minpos={} maxpos={}".format(minPos, maxPos))

        # Check what we saw
        if movement:
            # We saw something move
            self.log.info("\tSaw a movement")
            self._handleAction(self._trackMovement, "T")
            self._setTimer(self._randint(self.settings['RANDOMTIME']['T']), 'F')   
            
        elif minDist < self.settings['SHORTDISTANCE'] : 
            # We are too close to something.  Check if something is left or right.  10 readings on the right side, 11 readings on the left side
            #obstacleLeft = min(distances[:11]) < self.settings['SHORTDISTANCE']     # something on left
            obstacleLeft = minLeftDist < self.settings['SHORTDISTANCE']     # something on left
            #obstacleRight = min(distances[11:]) < self.settings['SHORTDISTANCE']    # something on right
            obstacleRight = minRightDist < self.settings['SHORTDISTANCE']    # something on right
            shortestLeft = minPos <= 0                                             # shortest distance is on left
            shortestRight = minPos > 0                                             # shortest distance is on right
            if obstacleLeft and obstacleRight:
                # Something on left and right, so back out
                if shortestLeft:
                    self.log.info("\tObstacle on LEFT and right, so back out left")
                    self._handleAction(self._backLeft, "l")
                else:
                    self.log.info("\tObstacle on left and RIGHT, so back out right")
                    self._handleAction(self._backRight, "r")
            elif shortestLeft:  
                self.log.info("\tObstacle on left, so veer right")
                self._handleAction(self._right, "R")
            elif shortestRight:  
                self.log.info("\tObstacle in right, so veer left")
                self._handleAction(self._left, "L")
            self._setTimer(self._randint(self.settings['RANDOMTIME']['R']), 'F')                   # back to default when finished
        else:
            # We are not too close to anything
            self.log.info("\tNo issues seen, so move F")
            self._handleAction(self._forward, "F")
        self.head.unPauseSensors()   # turn sensors back on 

    def endInterrupt(self):
        """Reset back to default behaviour following an interrupt"""
        self._clearInterrupt()
        self.do_default()

    def do_forward(self):
        self.head.move(0, t=1)
        self._handleAction(self._forward, "F")
        self.head.unPauseSensors()   # turn sensors back on for moving forwards

    def do_backward(self):
        self.head.move(0, t=1)
        self._handleAction(self._backward, "B")

    def do_backLeft(self):
        self.head.move(0, t=1)
        self._handleAction(self._backLeft, "l")

    def do_backRight(self):
        self.head.move(0, t=1)
        self._handleAction(self._backRight, "r")

    def clear_left(self):
        """Check if all clear on the left"""
        self.log.info("\tCheck for obstacles on left")
        self.head.pauseSensors()   # pause sensors while we scan
        #distances, minpos, maxpos = self.head.scanLeft()
        minPos, minDist, maxPos, maxDist = self.head.scanLeft()
        print("\tminpos={} maxpos={}".format(minPos, maxPos))
        clear = minDist > self.settings['SHORTDISTANCE']
        self.head.unPauseSensors()   # turn sensors back on 
        return clear

    def clear_right(self):
        """Check if all clear on the right"""
        self.log.info("\tCheck for obstacles on right")
        self.head.pauseSensors()   # pause sensors while we scan
        minPos, minDist, maxPos, maxDist = self.head.scanRight()
        print("\tminpos={} maxpos={}".format(minPos, maxPos))
        clear = minDist > self.settings['SHORTDISTANCE']
        self.head.unPauseSensors()   # turn sensors back on 
        return clear

    def do_left(self):
        #print("Do left")
        # Stop movements ready for scan
        self.stopCurrentAction()
        
        if self.clear_left():
            self.log.info("\tAll clear")
            self.head.move(-100, t=1)
            self._handleAction(self._left, "L")
        elif not self.clear_right():
            # In a pickle
            self.log.info("\tIn a pickle - blocked left and right")
            self.do_backLeft()
        else:
            self.log.info("\tBlocked on left")

    def do_leftNoCheck(self):
        #print("Do left")
        self._handleAction(self._left, "L")
        

    def do_right(self):
        #print("Do right")
        # Stop movements ready for scan
        self.stopCurrentAction()

        if self.clear_right():      
            self.log.info("\tAll clear")
            self.head.move(100, t=1)
            self._handleAction(self._right, "R")
        elif not self.clear_left():
            # In a pickle
            self.log.info("\tIn a pickle - blocked left and right")
            self.do_backRight()
        else:
            self.log.info("\tBlocked on right")

    def do_rightNoCheck(self):
        #print("Do right")
        self._handleAction(self._right, "R")         

    def do_wait(self):
        self._handleAction(None, "W")

    def do_unwind(self):
        self._handleAction(self._unwind, "U")

    def do_point(self):
        self._handleAction(self._point, "P")

    def do_eat(self):
        self._handleAction(self._eat, "E")

    def do_sit(self):
        self._handleAction(self._sit, "S")

    def do_kneesup(self):
        self._handleAction(self._kneesup, "^")

    def do_kneesdown(self):
        self._handleAction(self._kneesdown, "v")

    def do_hipsbackward(self):
        self._handleAction(self._hipsbackward, "<")

    def do_hipsforward(self):
        self._handleAction(self._hipsforward, ">")

    def do_alert(self):
        self._handleAction(self._alert, "A")

    def do_detectMovement(self):
        self._handleAction(self._detectMovement, "M")

    def do_trackMovement(self):
        self._handleAction(self._trackMovement, "T")
    
    def do_run(self):
        self._handleAction(self._run, "+")

    def do_crawl(self):
        self._handleAction(self._crawl, "-")


    # Action management
    # ---------------------------------------------------------------------------------------------

    def start(self):
        """Start the robot"""
        self.do_forward()
        self.head.startSensors()
        self._startRandom()

    def stop(self):
        """Stop the robot"""
        #self.showMessage("Stopping","")
        self.log.info("Stopping")
        self._handleAction(None, "W")
        self.head.stopSensors()
        self._runningRandom = False
        

    def _handleAction(self, func, msg):  
        """Stop any current action and start a new one"""
        self.runAction(func)
        self._currentAction = msg


    def _setTimer(self, delay, action):
        """Cancel any existing timer and replace with this one.  Timers are used to """
        #print("timer", action, delay)
        #self.log.info("Set timer {} in {} secs".format(action, delay))
        #if self.timer is not None:
        #    self.timer.cancel()
        self._timerAgeStart = self.age
        #self.timer = Timer(delay, self.actionFunction[action])
        #self.timer.start()
        self._timerDelay = delay
        self._timerAction = action

    def _executeTimer(self):
        #!!surely need to stop previous action?
        print("_executeTimer", self._timerAction)
        action = self._timerAction
        self._timerAction = None
        self._timerDelay = 0
        self._timerAgeStart = 0
        exec("self."+self.actionFunction[action])

    def _startRandom(self):
        """Start a random behaviour generator"""
        self._randomThread = Thread(target=self._runRandom)
        self._randomThread.start() 

    def _runRandom(self):
        """Continue to run random actions until stopped"""
        self._runningRandom = True
        while self._runningRandom:
            if self._timerAction is not None:
                if self.age-self._timerAgeStart >= self._timerDelay:
                    # There is a timer that has come of age, so execute it
                    self._executeTimer()
                    continue

            if self._interruptId is not None:
                # There was an interrupt that needs to be handled
                self._handleInterrupt()

            elif self._currentAction=="T":
                # Tracking movement, so let's finish that before we allow another random movement
                pass

            elif self._currentAction=="F" and self.age % 5 == 0: #!!every 5 seconds
                # No timer, so allow another random, weighted choice
                # . means no change to current action
                actions = ['.','S','B','L','R','U','P','E','A','+','-']
                weights = self.settings['RANDOMWEIGHTS']
                choice = random.choices(actions, weights)[0]
                self.log.info("random {}".format(choice))

                # Don't allow run if not enough space
                if choice=='+':
                    if self.head.lastDistance is None:
                        choice = '.'
                    elif self.head.lastDistance<100: #!!
                        self.log.info("Not enough distance to run")
                        choice = '.'
                    else:
                        pass # !! set time proportional to last distance?

                # Start the choice, and set a timer to start moving forward again after a random period
                if choice != '.':
                    self.log.info("Initiating action {}".format(choice))
                    exec("self."+self.actionFunction[choice])
                    self._setTimer(self._randint(self.settings['RANDOMTIME'][choice]), '*')                   

            sleep(self.settings['TICKPERIOD'])

            # Adjust alertness
            if self._currentAction=='U':
                self.alertness += self.settings['UNWINDALERTNESSINCREASE']
            else:
                self.alertness -= 1

            # Adjust age
            self.age += 1

            self._printStatus()


    def _printStatus(self):
        """Print out the status for debugging"""

        if self._interruptId != "human-detect": # and self._currentAction!="M":
            self.log.info("\t{} age={} alertness={} energy={} timernext={}_in_{}s threadcount={} interrupt={} dist={} temp={},{} human={}".format(
                self._currentAction, self.age, self.alertness, self.energy, 
                self._timerAction, self._timerDelay, activeCount(), self._interruptId, 
                self.head.lastDistance, self.head.lastMinTemperature,self.head.lastMaxTemperature,
                self.lastHumanDetectAge))

            if self.messageCallback is not None:   
                line1 = "{}{}{} {}".format(self._currentAction, 
                            " " if self._timerAction is None else self._timerAction,
                            self._timerDelay,
                            self._interruptId if self._interruptId is not None else "")
                line2 = "d={} t={}".format(self.head.lastDistance,
                            self.head.lastMaxTemperature)
                self.messageCallback(line1, line2)

        


    # Interrupt handling
    # ---------------------------------------------------------------------------------------------
    def interrupt(self, id, value):

        # Don't allow interrupt to be interrupted
        if self._interruptId is not None:
            return

        # !! ignore for now
        if id=="human-detect":
            #print("Ignoring heat detect")
            self.head.unPauseSensors()  
            return

        if id=="human-detect" and self.age-self.lastHumanDetectAge < 60:
            print("Bored of humans")  
            self.head.unPauseSensors()  
            return

        self.log.info("Interrupt {}".format(id))            

        self._interruptId = id
        self._interruptValue = value


    def _handleInterrupt(self):
        # Handle the interrupt
        if not self._interruptBeingHandled:
            self.log.info("Handle Interrupt {}".format(self._interruptId))
            self._interruptBeingHandled = True

            if self._interruptId=="short-distance":
                # End interrupt so we do default scan
                self.endInterrupt()
                #self.do_backward()
                #minmax = self.settings['RANDOMTIME']['B']   
                #self._setTimer(random.randint(minmax[0],minmax[1]), 'I')       

            elif self._interruptId=="left-antenna":
                self.do_right()
                self._setTimer(self._randint(self.settings['RANDOMTIME']['R']), 'I')    

            elif self._interruptId=="right-antenna":
                self.do_left()
                self._setTimer(self._randint(self.settings['RANDOMTIME']['L']), 'I')    

            elif self._interruptId=="human-detect":
                # 
                self.lastHumanDetectAge = self.age
                self.do_trackMovement()
                self._setTimer(self._randint(self.settings['RANDOMTIME']['T']), 'I')   


            elif self._interruptId=="long-distance":
                self._clearInterrupt()
                self.head.unPauseSensors()  
            """
                self.do_run()
                #minmax = self.settings['RANDOMTIME']['R']
                minmax[0] = 2
                minmax[1] = self._interruptValue / 20 # run time proportional to distance measured
                self._setTimer(random.randint(minmax[0],minmax[1]), 'I')
            """

    def _clearInterrupt(self):
        self._interruptId = None
        self._interruptBeingHandled = False          

    def _randint(minmax):
        return random.randint(minmax[0],minmax[1])



if __name__ == "__main__":
    print("Testing RandomAnimal")    


    # Create animal
    animal = RandomAnimal()

    #animal.log.setLevel(logging.DEBUG)

    # With 2 legs           
    animal.addPairOfLegs(Leg(Joint(0), Joint(1), 1), Leg(Joint(2), Joint(3), -1))

    # Load settings from json file
    animal.loadSettings()

    print("wakeSlowly(2)")
    #animal.wakeSlowly(5) 
    #sleep(2)

    #animal.forward()

    # Run through all possible actions
    """
    for func in animal.actionFunction.values():
        print(func)
        eval("animal."+func)
        sleep(5)
    """

    
    # Run the animal in random mode

    print("Running animal")
    animal.start()
    while True:
        sleep(0.2)
    