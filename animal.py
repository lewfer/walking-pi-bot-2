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
from threadhelper import *
from helpers import *
from joint import *
from leg import *
from time import sleep
import curses
import random
import json
from head import Head
from gpiozero import Button
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)

# Constants
# -------------------------------------------------------------------------------------------------
SETTINGSFILENAME = 'animal_settings.json'


# Class
# -------------------------------------------------------------------------------------------------
class Animal():
    '''Animal has a number of pairs of legs'''

    def __init__(self):
        # Set up logger to log to screen
        self.log = createLogger()    
        
      
        # Construction
        self.numLegs = 0                        # number of legs - start with none
        self.legPairs = []                      # start with no legs (they will be added later)
        self.head = Head(self.interrupt, self.log)
        self.leftAntenna = Button(6)
        self.rightAntenna = Button(12)

        self.voicePin = 16
        GPIO.setup(self.voicePin, GPIO.OUT)
        #self.pwm = GPIO.PWM(self.voicePin, 1000)

        # Robot health (not used at the moment)
        # Can use these to determine behaviour, e.g. slowing down as energy drops
        self.alertness = 120
        self.energy = 1000
        self.age = 0

        # Helper objects, to idenntify legs and threads
        self._legs = {}                         # dictionary to quickly find legs
        self._threads = {}                      # dictionary to quickly find threads

        # Actions will run on a thread
        self._actionThread = None               # thread on which current action is running
        self._threadCount = 0                   # so we can track threads

        self._stopped = False                   # flag to indicate if we want the animal to stop what it is doing (i.e. stop current thread)

        # Antennae handlers - called when antenna triggered
        self.leftAntenna.when_pressed = self._leftAntennaPressed
        self.rightAntenna.when_pressed = self._rightAntennaPressed

        # Caller can register a callback to receive messages (for display purposes)
        self.messageCallback = None

        self.stopCry()

        self.log.info("Created Animal")

    def cry(self):
        #print("CRY")
        #self.pwm.start(100)
        GPIO.output(self.voicePin, GPIO.HIGH)

    def stopCry(self):
        #print("STOP CRY")
        #self.pwm.ChangeDutyCycle(0)
        GPIO.output(self.voicePin, GPIO.LOW)

    # Construction
    # ---------------------------------------------------------------------------------------------

    def addPairOfLegs(self, left, right):
        '''Add legs two at a time from front to back'''

        index = len(self.legPairs)
        self.legPairs.append(LegPair(left, right))

        # Add to legs dictionary
        self._legs['L'+str(index)] = self.legPairs[index].left
        self._legs['R'+str(index)] = self.legPairs[index].right

        # Add to legs threads
        self._threads['L'+str(index)] = None
        self._threads['R'+str(index)] = None

        self.numLegs += 2

    # Interrupt
    # ---------------------------------------------------------------------------------------------

    def interrupt(self, id, value):
        """Virtual function can be overridden"""
        pass

    # Settings 
    # ---------------------------------------------------------------------------------------------

    def setDefaultSettings(self):
        """Set default settings for the robot.  These will apply if no settings file found."""

        # Range of servo angle movements for each joint
        self.settings = {"leg_ranges": []}
        # knee order: down, mid, up
        # hip order: back, mid, forward
        for i in range(len(self.legPairs)):
            self.settings["leg_ranges"].append({"left": {"hip": [130,90,70],"knee": [50,90,130]},"right": {"hip": [50,90,110],"knee": [130,90,50]}})

        # Speed of leg movements
        self.settings['REACHTIME'] = 1
        self.settings['PUSHTIME'] = 1
        self.settings['PUSHDELAY'] = 0

        # Random wait time between certain movements, in tenths of a second
        self.settings['RANDOMWAIT'] = 2    

        # Number of time steps taken per angular degree.  Adjust for smoother/quicker movement.  Small value means quicker and less smooth
        # Try 2, 1, 0.5, 0.25
        self.settings['STEPSPERDEGREE'] = 0.25

        # If the head tracks humans when it sees them
        self.settings['HUMANTRACKING'] = False

        # Head movement range in degrees
        self.settings['HEADHIGHANGLE'] = 180
        self.settings['HEADLOWANGLE'] = 0
        self.settings['HEADMIDANGLE'] = 90

        # Change in head angle when tracking
        self.settings['HEADTRACKDELTA'] = 10

        # Sensor thresholds
        self.settings['SHORTDISTANCE'] = 30     # triggers short-distance interrupt when distance less than this
        self.settings['LONGDISTANCE'] = 200     # triggers long-distance interrupt when distance more than this
        self.settings['HUMANDETECTMIN'] = 24    # triggers human-detect interrupt when heat between min and max
        self.settings['HUMANDETECTMAX'] = 30    # triggers human-detect interrupt when head between min and max

        self.settings['RUNSPACENEEDED'] = 100   # Space in cmneeded for robot to be able to run

        self.settings['FORWARDMOVEMENTS'] = ['shunt','swimBreast', 'swimButterfly', 'swimFrontCrawl']


    def loadSettings(self):
        '''Load the settings file, which contains the calibrated settings for each joint'''

        # Default to the defaults if no settings file
        self.setDefaultSettings()

        # Load settings over the defaults
        try:
            # Try to load the settings file
            with open(SETTINGSFILENAME) as f:
                self.log.info("Settings {} found".format(SETTINGSFILENAME))
                self.settings.update(json.load(f))  # update defaults with settings loaded from file
                self.storeSettings()                # in case we added new defaults
        except FileNotFoundError:
            # If no settings file use defaults 
            self.log.info("Settings file {} not found.  Using defaults".format(SETTINGSFILENAME))
            self.storeSettings()

        self.log.info(self.settings)

        # Apply the settings to the robot
        self.applySettings()
        
    def applySettings(self):
        '''Apply settings to the servos etc'''

        # Now set the default angles for each joint.  We need to mirror the angles left and right legs 
        for pair in range(len(self.legPairs)):

            self.legPairs[pair].left.hip.lowAngle = self.settings["leg_ranges"][pair]["left"]["hip"][LEG_FRONT]
            self.legPairs[pair].left.knee.lowAngle = self.settings["leg_ranges"][pair]["left"]["knee"][LEG_DOWN]
            self.legPairs[pair].right.hip.lowAngle = self.settings["leg_ranges"][pair]["right"]["hip"][LEG_BACK]
            self.legPairs[pair].right.knee.lowAngle = self.settings["leg_ranges"][pair]["right"]["knee"][LEG_UP]

            self.legPairs[pair].left.hip.midAngle = self.settings["leg_ranges"][pair]["left"]["hip"][LEG_MID]
            self.legPairs[pair].left.knee.midAngle = self.settings["leg_ranges"][pair]["left"]["knee"][LEG_MID]
            self.legPairs[pair].right.hip.midAngle = self.settings["leg_ranges"][pair]["right"]["hip"][LEG_MID]
            self.legPairs[pair].right.knee.midAngle = self.settings["leg_ranges"][pair]["right"]["knee"][LEG_MID]

            self.legPairs[pair].left.hip.highAngle = self.settings["leg_ranges"][pair]["left"]["hip"][LEG_BACK]
            self.legPairs[pair].left.knee.highAngle = self.settings["leg_ranges"][pair]["left"]["knee"][LEG_UP]
            self.legPairs[pair].right.hip.highAngle = self.settings["leg_ranges"][pair]["right"]["hip"][LEG_FRONT]
            self.legPairs[pair].right.knee.highAngle = self.settings["leg_ranges"][pair]["right"]["knee"][LEG_DOWN]

            self.head.joint.midAngle = self.settings['HEADMIDANGLE'] 
            self.head.joint.highAngle = self.settings['HEADHIGHANGLE']
            self.head.joint.lowAngle = self.settings['HEADLOWANGLE']

            self.head.trackDelta = self.settings['HEADTRACKDELTA'] 
            self.head.shortDistance = self.settings['SHORTDISTANCE'] 
            self.head.humanDetectMin = self.settings['HUMANDETECTMIN'] 
            self.head.humanDetectMax = self.settings['HUMANDETECTMAX'] 

        self._setStepsPerDegree(self.settings['STEPSPERDEGREE'])

    def storeSettings(self):
        '''Store the current settings to the settings file'''

        # Save the settings dictionary to file
        with open(SETTINGSFILENAME, 'w') as f:
            json.dump(self.settings, f)

    def storeAndReapplySettings(self):
        '''Store the current settings to the settings file and apply them'''

        self.storeSettings()
        self.loadSettings()

    def factoryReset(self):
        '''Return to all default settings, store in the settings file and apply to the robot'''

        self.setDefaultSettings()
        self.storeAndReapplySettings()


    def _setStepsPerDegree(self, spd): 
        '''Steps servo takes per angular degree.  Smaller means faster, but less smooth.  Recommended range 0.5 to 10.'''

        # Now set the steps per degree for each joint
        for pair in range(len(self.legPairs)):
            self.legPairs[pair].left.hip.stepsPerDegree = spd
            self.legPairs[pair].left.knee.stepsPerDegree = spd
            self.legPairs[pair].right.hip.stepsPerDegree = spd
            self.legPairs[pair].right.knee.stepsPerDegree = spd     


    # Sensors
    # ---------------------------------------------------------------------------------------------

    def _leftAntennaPressed(self):
        '''Handler called when left antenna triggered'''

        # Raise an interrupt and allow caller to deal with it
        self.interrupt("left-antenna", 0)

    def _rightAntennaPressed(self):
        '''Handler called when right antenna triggered'''

        # Raise an interrupt and allow caller to deal with it
        self.interrupt("right-antenna", 0)


    # Threading
    # ---------------------------------------------------------------------------------------------
    def _runOnThread(self, legId, func, params, waitMult=0):
        """Run the function func on the leg identified by legId with the given params.  Wait for any existing thread to finish first"""

        if waitMult>0:
            self._waitRandom(waitMult) 

        # Get the thread associated with the leg
        thread = self._threads[legId]

        # Wait for existing thread to finish so we don't try to make servo move to multiple angles at the same time!
        if thread is not None:
            #self.log.debug("\tWait for thread {} before create new {} for {}".format(thread.name, legId, func))
            thread.join()
        else:
            #self.log.debug("\tNo existing thread for {}".format(legId))
            pass

        # Start the new thread to run the function
        funcEval = eval('self._legs[legId].'+func)
        threadName = legId + ":" + func + ":" + str(self._threadCount)
        self._threadCount += 1
        thread = Thread(target=funcEval, name=threadName, kwargs=params)
        thread.start()
        #self.log.debug("\tStarted new thread{}".format(thread.name))

        # Store the thread against the leg id so we can find it again later
        self._threads[legId] = thread

    def _joinThreads(self, legIds):
        """Wait for all threads to finish for the specified legs"""

        for legId in legIds:
            thread = self._threads[legId]
            if thread is not None:
                thread.join()

    def _stopThreads(self):
        '''Stop all threads for all legs'''

        #self.log.debug("Stopping leg threads")
        for i, k in enumerate(self._threads):
            thread = self._threads[k]
            if thread is not None:
                #self.log.debug("Joining {}".format(thread.name))
                thread.join()        
                self._threads[k] = None
        
        #self.log.debug("Stopped threads: {}".format(activeCount()))

    def _stopMovements(self):
        '''Stop the servos and threads'''

        self.log.debug("_stopMovements")

        # Stop all servos
        for pair in range(len(self.legPairs)):
            self.legPairs[pair].left.stop()
            self.legPairs[pair].right.stop()

        # Stop all threads
        self._stopThreads()


    # Run and Stop Actions
    # ---------------------------------------------------------------------------------------------

    def runAction(self, func):  
        '''Stop any current action and start a new one if func is provided'''

        if func is not None:
            self.log.info("runAction {}".format(func.__name__))

        self.stopCurrentAction()
        if func is not None:
            self._actionThread = Thread(target=func)
            self._actionThread.start()   


    def stopCurrentAction(self):
        '''Stop any current action and wait for its thread to finish'''

        self.log.info("begin stopCurrentAction")
        #self._stopMovements()
        self._stopped = True

        if self._actionThread: self._actionThread.join()

        self._stopped = False
        
        self.log.info("end stopCurrentAction")




    # Actions Helpers
    # ---------------------------------------------------------------------------------------------

    def _waitRandom(self, mult=1):
        '''Wait for a random time (in tenths of a second)'''

        sleep(random.randint(0,self.settings['RANDOMWAIT']*mult)/10.0) 

    def _reachForwardPair(self, pair, t):
        # Move limbs forward, left then right or the other way
        left = "L"+str(pair)
        right = "R"+str(pair)
        if random.random()>0.5:
            self._reachForwardLeg(left, t)
            self._reachForwardLeg(right, t)
        else:
            self._reachForwardLeg(right, t)
            self._reachForwardLeg(left, t)

    def _reachForwardPairTogether(self, pair, t):
        # Move  limbs forward, both together
        left = "L"+str(pair)
        right = "R"+str(pair)
        if random.random()>0.5:
            self._runOnThread(left, 'reachForward', {'t':t}, 3)
            self._runOnThread(right, 'reachForward', {'t':t}, 3)
        else:
            self._runOnThread(right, 'reachForward', {'t':t}, 3)
            self._runOnThread(left, 'reachForward', {'t':t}, 3)

        self._joinThreads([left, right])
                
    def _reachForwardLeg(self, leg, t):
        self._runOnThread(leg, 'reachForward', {'t':t}, 3)
        self._joinThreads([leg])     

    def _reachForwardLeft(self, t):
        legs = ['L0']
        self._runOnThread('L0', 'reachForward', {'t':t}, 3)
        if self.numLegs > 2:
            self._runOnThread('L1', 'reachForward', {'t':t}, 3)
            legs += ['L1']
        if self.numLegs > 4:
            self._runOnThread('L2', 'reachForward', {'t':t}, 3)                
            legs += ['L2']
        self._joinThreads(legs)

    def _reachForwardRight(self, t):
        legs = ['R0']
        self._runOnThread('R0', 'reachForward', {'t':t}, 3)
        if self.numLegs > 2:
            self._runOnThread('R1', 'reachForward', {'t':t}, 3)
            legs += ['R1']
        if self.numLegs > 4:
            self._runOnThread('R2', 'reachForward', {'t':t}, 3)                
            legs += ['R2']
        self._joinThreads(legs)   

    def _reachBackwardLeft(self, t):
        legs = ['L0']
        self._runOnThread('L0', 'reachBackward', {'t':t}, 3)
        if self.numLegs > 2:
            self._runOnThread('L1', 'reachBackward', {'t':t}, 3)
            legs += ['L1']
        if self.numLegs > 4:
            self._runOnThread('L2', 'reachBackward', {'t':t}, 3)                
            legs += ['L2']
        self._joinThreads(legs)

    def _reachBackwardRight(self, t):
        legs = ['R0']
        self._runOnThread('R0', 'reachBackward', {'t':t}, 3)
        if self.numLegs > 2:
            self._runOnThread('R1', 'reachBackward', {'t':t}, 3)
            legs += ['R1']
        if self.numLegs > 4:
            self._runOnThread('R2', 'reachBackward', {'t':t}, 3)                
            legs += ['R2']
        self._joinThreads(legs)          

    def _pushBackAll(self, t):
        # Move front limbs 
        self._runOnThread('L0', 'pushBackward', {'t':t})
        self._runOnThread('R0', 'pushBackward', {'t':t})
        legs = ['L0','R0']

        if self.numLegs > 2:
            # Move middle limbs 
            sleep(self.settings['PUSHDELAY'])
            self._runOnThread('L1', 'pushBackward', {'t':t})
            self._runOnThread('R1', 'pushBackward', {'t':t})
            legs += ['L1','R1']

        if self.numLegs > 4:
            # Move rear limbs
            sleep(self.settings['PUSHDELAY'])
            self._runOnThread('L2', 'pushBackward', {'t':t})
            self._runOnThread('R2', 'pushBackward', {'t':t})
            legs += ['L2','R2']

        # Wait for all legs to stop
        self._joinThreads(legs)

    def _pushBackLeft(self, t):
        legs = ['L0']
        self._runOnThread('L0', 'pushBackward', {'t':t})
        if self.numLegs > 2:
            sleep(self.settings['PUSHDELAY'])
            self._runOnThread('L1', 'pushBackward', {'t':t})
            legs += ['L1']
        if self.numLegs > 4:
            sleep(self.settings['PUSHDELAY'])
            self._runOnThread('L2', 'pushBackward', {'t':t})
            legs += ['L2']
        self._joinThreads(legs)   

    def _pushBackRight(self,t):
        legs = ['R0']
        self._runOnThread('R0', 'pushBackward', {'t':t})
        if self.numLegs > 2:
            sleep(self.settings['PUSHDELAY'])
            self._runOnThread('R1', 'pushBackward', {'t':t})
            legs += ['R1']
        if self.numLegs > 4:
            sleep(self.settings['PUSHDELAY'])
            self._runOnThread('R2', 'pushBackward', {'t':t})
            legs += ['R2']
        self._joinThreads(legs)             

    def _pushForwardLeft(self, t):
        legs = ['L0']
        self._runOnThread('L0', 'pushForward', {'t':t})
        if self.numLegs > 2:
            sleep(self.settings['PUSHDELAY'])
            self._runOnThread('L1', 'pushForward', {'t':t})
            legs += ['L1']
        if self.numLegs > 4:
            sleep(self.settings['PUSHDELAY'])
            self._runOnThread('L2', 'pushForward', {'t':t})
            legs += ['L2']
        self._joinThreads(legs)   

    def _pushForwardRight(self,t):
        legs = ['R0']
        self._runOnThread('R0', 'pushForward', {'t':t})
        if self.numLegs > 2:
            sleep(self.settings['PUSHDELAY'])
            self._runOnThread('R1', 'pushForward', {'t':t})
            legs += ['R1']
        if self.numLegs > 4:
            sleep(self.settings['PUSHDELAY'])
            self._runOnThread('R2', 'pushForward', {'t':t})
            legs += ['R2']
        self._joinThreads(legs)             


    # Actions 
    # ---------------------------------------------------------------------------------------------

    def _run(self):
        '''Move forward at speed'''

        self._forward(speed=10)

    def _crawl(self):
        '''Move forward slowly'''

        self._forward(speed=0.5)        

    def _forward(self, speed=1):
        '''Move forward in a random way'''

        actions = []
        for movement in self.settings['FORWARDMOVEMENTS']:
            actions.append('self._' + movement + '(speed)')
        #print(actions)
        #actions = ['self._shunt(speed)','self._swimBreast(speed)', 'self._swimButterfly(speed)', 'self._swimFrontCrawl(speed)']
        choice = random.choice(actions)
        self.log.info("Forward: " + choice)
        exec(choice)

    def _shunt(self, speed=1):
        '''Move forward'''

        #self._stopped = False

        while True:
            # Move limbs forwards, one at a time
            t = self.settings['REACHTIME'] / speed
            self._reachForwardPair(0, t)
            if self.numLegs > 2:
                self._reachForwardPair(1, t)
            if self.numLegs > 4:
                self._reachForwardPair(2, t)

            # Move limbs backwards together
            t = self.settings['PUSHTIME'] / speed
            self._pushBackAll(t)

            # If request was made to end walk, break out of loop
            if self._stopped:
                break   

        self._stopMovements()

    def _swimBreast(self, speed=1):
        '''Move forward in swim motion (one side then other).  Breast stroke, so push back together'''

        #self._stopped = False

        while True:
            # Move limbs forwards, one at a time
            t = self.settings['REACHTIME'] / speed
            if random.random()>0.5:
                self._reachForwardLeft(t)
                self._reachForwardRight(t)
            else:
                self._reachForwardRight(t)
                self._reachForwardLeft(t)

            # Move limbs backwards together
            t = self.settings['PUSHTIME'] / speed
            self._pushBackAll(t)

            # If request was made to end walk, break out of loop
            if self._stopped:
                break   

        self._stopMovements()        

    def _swimButterfly(self, speed=1):
        '''Move forward in swim motion (one side then other).  Breast stroke, so push back together'''

        #self._stopped = False

        while True:
            # Move limbs forwards, one at a time
            t = self.settings['REACHTIME'] / speed
            self._reachForwardPairTogether(0, t)
            if self.numLegs > 2:
                self._reachForwardPairTogether(1, t)
            if self.numLegs > 4:
                self._reachForwardPairTogether(2, t)


            # Move limbs backwards together
            t = self.settings['PUSHTIME'] / speed
            self._pushBackAll(t)

            # If request was made to end walk, break out of loop
            if self._stopped:
                break   

        self._stopMovements()        

    def _swimFrontCrawl(self, speed=1):
        '''Move forward in swim motion (one side then other).  Front crawl, so push back on each side.'''

        #self._stopped = False

        while True:
            # Move limbs forwards, one at a time
            t = self.settings['REACHTIME'] / speed
            if random.random()>0.5:
                self._reachForwardLeft(t)
                self._reachForwardRight(t)
            else:
                self._reachForwardRight(t)
                self._reachForwardLeft(t)

            # Move limbs backwards together
            t = self.settings['PUSHTIME'] / speed
            if random.random()>0.5:
                self._pushBackLeft(t)
                self._waitRandom(3) 
                self._pushBackRight(t)
            else:
                self._pushBackRight(t)
                self._waitRandom(3) 
                self._pushBackLeft(t)

            # If request was made to end walk, break out of loop
            if self._stopped:
                break   

        self._stopMovements()   

    def _backward(self):
        '''Move backward'''
                
        #self._stopped = False

        while True:
            # Move limbs backwards, one at a time
            # ----------------------------------
                        
            t = self.settings['REACHTIME']

            # Move front limbs
            self._runOnThread('L0', 'reachBackward', {'t':t})
            self._joinThreads(['L0'])
            self._waitRandom() 
            self._runOnThread('R0', 'reachBackward', {'t':t})
            self._joinThreads(['R0'])
            self._waitRandom() 

            if self.numLegs > 2:
                # Move middle limbs
                self._runOnThread('L1', 'reachBackward', {'t':t})
                self._waitRandom() 
                self._runOnThread('R1', 'reachBackward', {'t':t})
                self._joinThreads(['L1','R1'])
                self._waitRandom() 

            if self.numLegs > 4:
                # Move rear limbs
                self._runOnThread('L2', 'reachBackward', {'t':t})
                self._joinThreads(['L2'])
                self._waitRandom() 
                self._runOnThread('R2', 'reachBackward', {'t':t})
                self._joinThreads(['R2'])
                self._waitRandom() 

            t = self.settings['PUSHTIME']

            # Move limbs forwards together
            # -----------------------------

            # Move front limbs
            self._runOnThread('L0', 'pushForward', {'t':t})
            self._runOnThread('R0', 'pushForward', {'t':t})
            legs = ['L0','R0']

            if self.numLegs > 2:
                # Move middle limbs
                sleep(self.settings['PUSHDELAY'])
                self._runOnThread('L1', 'pushForward', {'t':t})
                self._runOnThread('R1', 'pushForward', {'t':t})
                legs += ['L1','R1']

            if self.numLegs > 4:
                # Move rear limbs
                sleep(self.settings['PUSHDELAY'])
                self._runOnThread('L2', 'pushForward', {'t':t})
                self._runOnThread('R2', 'pushForward', {'t':t})
                legs += ['L2','R2']

            # Wait for all legs to stop
            self._joinThreads(legs)

            # If request was made to end walk, break out of loop
            if self._stopped:
                break  

        self._stopMovements()


    def _backLeft(self):
        '''Move backward and left'''
                
        #self._stopped = False

        t1 = self.settings['REACHTIME']
        t2 = self.settings['PUSHTIME']

        # Move left legs into position
        if self.numLegs > 4:
            self._runOnThread('L0', 'kneeOffFloor', {'t':t1})
            self._runOnThread('L1', 'kneeOffFloor', {'t':t1})
            self._runOnThread('L2', 'reachBackward', {'t':t1})
            self._joinThreads(['L0','L1','L2'])
            self._waitRandom() 
        elif self.numLegs > 2:
            self._runOnThread('L0', 'kneeOffFloor', {'t':t1})
            self._runOnThread('L1', 'reachBackward', {'t':t1})
            self._joinThreads(['L0','L1'])
            self._waitRandom()    
        else:
            self._runOnThread('L0', 'reachBackward', {'t':t1})
            self._joinThreads(['L0'])
            self._waitRandom()          

        while True:
            # Move limbs backwards
            self._reachBackwardRight(t2)

            # Move limbs forwards 
            self._pushForwardRight(t2)

            # If request was made to end walk, break out of loop
            if self._stopped:
                break  

        self._stopMovements()


    def _backRight(self):
        '''Move backward and right'''
                
        #self._stopped = False


        t1 = self.settings['REACHTIME']
        t2 = self.settings['PUSHTIME']

        # Move right legs into position
        if self.numLegs > 4:
            self._runOnThread('R0', 'kneeOffFloor', {'t':t1})
            self._runOnThread('R1', 'kneeOffFloor', {'t':t1})
            self._runOnThread('R2', 'reachBackward', {'t':t1})
            self._joinThreads(['R0','R1','R2'])
            self._waitRandom() 
        elif self.numLegs > 2:
            self._runOnThread('R0', 'kneeOffFloor', {'t':t1})
            self._runOnThread('R1', 'reachBackward', {'t':t1})
            self._joinThreads(['R0','R1'])
            self._waitRandom()    
        else:
            self._runOnThread('R0', 'reachBackward', {'t':t1})
            self._joinThreads(['R0'])
            self._waitRandom()                       

        while True:
            # Move limbs backwards
            self._reachBackwardLeft(t2)

            # Move limbs forwards
            self._pushForwardLeft(t2)

            # If request was made to end walk, break out of loop
            if self._stopped:
                break  

        self._stopMovements()



    def _right(self):
        '''Move right'''
                
        #self._stopped = False

        while True:
            # Move limbs into position, one at a time
            # ---------------------------------------
                
            t = self.settings['REACHTIME']

            # Move front limbs
            self._runOnThread('L0', 'reachForward', {'t':t})
            self._joinThreads(['L0'])
            self._waitRandom() 
            self._runOnThread('R0', 'reachBackward', {'t':t})
            self._joinThreads(['R0'])
            self._waitRandom() 

            if self.numLegs > 2:
                # Move middle limbs
                self._runOnThread('L1', 'reachForward', {'t':t})
                self._waitRandom() 
                self._runOnThread('R1', 'reachBackward', {'t':t})
                self._joinThreads(['L1','R1'])
                self._waitRandom() 

            if self.numLegs > 4:
                # Move rear limbs
                self._runOnThread('L2', 'reachForward', {'t':t})
                self._waitRandom() 
                self._runOnThread('R2', 'reachBackward', {'t':t})
                self._joinThreads(['L2','R2'])
                self._waitRandom() 


            # Move limbs forwards together
            # -----------------------------

            t = self.settings['PUSHTIME']

            # Move front limbs
            self._runOnThread('L0', 'pushBackward', {'t':t})
            self._runOnThread('R0', 'pushForward', {'t':t})
            legs = ['L0','R0']

            if self.numLegs > 2:
                # Move middle limbs
                sleep(self.settings['PUSHDELAY'])
                self._runOnThread('L1', 'pushBackward', {'t':t})
                self._runOnThread('R1', 'pushForward', {'t':t})
                legs += ['L1','R1']

            if self.numLegs > 4:
                # Move rear limbs
                sleep(self.settings['PUSHDELAY'])
                self._runOnThread('L2', 'pushBackward', {'t':t})
                self._runOnThread('R2', 'pushForward', {'t':t})
                legs += ['L2','R2']

            # Wait for all legs to stop
            self._joinThreads(legs)        

            # If request was made to end walk, break out of loop
            if self._stopped:
                break    

        self._stopMovements()


    def _left(self):
        '''Move left'''
                
        #self._stopped = False

        while True:
            # Move limbs into position, one at a time
            # ---------------------------------------
                               
            t = self.settings['REACHTIME']

            # Move front limbs
            self._runOnThread('L0', 'reachBackward', {'t':t})
            self._joinThreads(['L0'])
            self._waitRandom() 
            self._runOnThread('R0', 'reachForward', {'t':t})
            self._joinThreads(['R0'])
            self._waitRandom() 

            if self.numLegs > 2:
                # Move middle limbs
                self._runOnThread('L1', 'reachBackward', {'t':t})
                self._waitRandom() 
                self._runOnThread('R1', 'reachForward', {'t':t})
                self._joinThreads(['L1','R1'])
                self._waitRandom() 

            if self.numLegs > 4:
                # Move rear limbs
                self._runOnThread('L2', 'reachBackward', {'t':t})
                self._waitRandom() 
                self._runOnThread('R2', 'reachForward', {'t':t})
                self._joinThreads(['L2','R2'])
                self._waitRandom() 

            t = self.settings['PUSHTIME']

            # Move limbs together
            # -------------------

            # Move front limbs
            self._runOnThread('L0', 'pushForward', {'t':t})
            self._runOnThread('R0', 'pushBackward', {'t':t})
            legs = ['L0','R0']

            if self.numLegs > 2:
                sleep(self.settings['PUSHDELAY'])
                self._runOnThread('L1', 'pushForward', {'t':t})
                self._runOnThread('R1', 'pushBackward', {'t':t})
                legs += ['L1','R1']

            if self.numLegs > 4:
                sleep(self.settings['PUSHDELAY'])
                self._runOnThread('L2', 'pushForward', {'t':t})
                self._runOnThread('R2', 'pushBackward', {'t':t})
                legs += ['L2','R2']

            # Wait for all legs to stop
            self._joinThreads(legs)

            # If request was made to end walk, break out of loop
            if self._stopped:
                break  

        self._stopMovements()


    def _point(self):
        '''Point'''

        #self._stopped = False
        t = 2

        while True:

            # Get settings for the leg
            settings = self.settings["leg_ranges"][0]

            kneeOffsetFromMid = 60
            jitter = 5 # !! param

            # Set left leg position, with jitter
            angles = (settings["left"]["hip"][LEG_FRONT]+random.randint(-jitter,jitter), settings["left"]["knee"][LEG_MID]+kneeOffsetFromMid+random.randint(-jitter,jitter))
            self._runOnThread('L0', 'setAngles', {'angles':angles,'t':t})
            
            # Set right leg position, with jitter
            angles = (settings["right"]["hip"][LEG_FRONT]+random.randint(-jitter,jitter), settings["right"]["knee"][LEG_MID]-kneeOffsetFromMid+random.randint(-jitter,jitter))
            self._runOnThread('R0', 'setAngles', {'angles':angles,'t':t})

            legs = ['L0','R0']

            if self.numLegs > 2:
                self._runOnThread('L1', 'mid', {'t':t})
                self._runOnThread('R1', 'mid', {'t':t})
                legs = ['L1','R1']

            if self.numLegs > 4:
                self._runOnThread('L2', 'mid', {'t':t})
                self._runOnThread('R2', 'mid', {'t':t})
                legs = ['L2','R2']

            # Wait for all legs to stop
            self._joinThreads(legs)       

            # If request was made to end walk, break out of loop
            if self._stopped:
                break   

        self._stopMovements()


    def _eat(self):
        '''Eat'''

        #self._stopped = False
        t = 1

        while True:

            # Get settings for the leg
            settings = self.settings["leg_ranges"][0]

            jitter = 20 # !! param

            # Set left leg position, with jitter.  Hip to the front, knee to mid.
            angles = (settings["left"]["hip"][LEG_FRONT]+random.randint(-jitter,jitter), settings["left"]["knee"][LEG_MID]+random.randint(-jitter,jitter))
            self._runOnThread('L0', 'setAngles', {'angles':angles,'t':t})
            
            # Set right leg position, with jitter.  Hip to the front, knee to mid.
            angles = (settings["right"]["hip"][LEG_FRONT]+random.randint(-jitter,jitter), settings["right"]["knee"][LEG_MID]+random.randint(-jitter,jitter))
            self._runOnThread('R0', 'setAngles', {'angles':angles,'t':t})

            legs = ['L0','R0']

            if self.numLegs > 2:
                self._runOnThread('L1', 'mid', {'t':t})
                self._runOnThread('R1', 'mid', {'t':t})
                legs = ['L1','R1']

            if self.numLegs > 4:
                self._runOnThread('L2', 'mid', {'t':t})
                self._runOnThread('R2', 'mid', {'t':t})
                legs = ['L2','R2']

            # Wait for all legs to stop
            self._joinThreads(legs)                 

            # If request was made to end walk, break out of loop
            if self._stopped:
                break               

        self._stopMovements()


    def wakeSlowly(self, t=5):
        '''Move all legs slowly to their mid position.  The slow wake prevents a surge in current draw that could shut down the Pi.'''
       
        #self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'mid', {'t':t})
            self._runOnThread(right, 'mid', {'t':t})

        # Wait for all threads to stop
        self._joinThreads(threads)

    def _scare(self, t=1):
        '''Scare'''
        self._hipsbackward(t)
        self._kneesup(t)   

    def _bounce(self, t=1):
        if len(self.legPairs)==2:
            # Set up a thread for each leg movement and move all legs simultaneously
            left = 'L0'
            right = 'R0'
            #threads = ['L0','R0','L1','R1']
            threads = ['L0','R0']
            for i in range(3):
                self._runOnThread('L0', 'kneeOffFloor', {'t':t})
                self._runOnThread('R0', 'kneeOffFloor', {'t':t})   
                #self._runOnThread('L1', 'kneeFullDown', {'t':t})
                #self._runOnThread('R1', 'kneeFullDown', {'t':t})     
                self._joinThreads(threads)    
                
                self._runOnThread('L0', 'kneeFullDown', {'t':t})
                self._runOnThread('R0', 'kneeFullDown', {'t':t})       
                #self._runOnThread('L1', 'kneeOffFloor', {'t':t})
                #self._runOnThread('R1', 'kneeOffFloor', {'t':t})                   
                self._joinThreads(threads)   
        else:
            # Set up a thread for each leg movement and move all legs simultaneously
            left = 'L0'
            right = 'R0'
            threads = ['L0','R0']
            for i in range(3):
                self._runOnThread('L0', 'kneeOffFloor', {'t':t})
                self._runOnThread('R0', 'kneeOffFloor', {'t':t})      
                self._joinThreads(threads)    
                 
                self._runOnThread('L0', 'kneeFullDown', {'t':t})
                self._runOnThread('R0', 'kneeFullDown', {'t':t})              
                self._joinThreads(threads)  

    def _unwind(self, t=1):
        '''Put the animal into a relaxing state (crouched down)'''
        
        #self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'unwind', {'t':t})
            self._runOnThread(right, 'unwind', {'t':t})

        # Wait for all threads to stop
        self._joinThreads(threads)


    def _alert(self, t=1):
        '''Put the animal into an alert state (standing upright)'''
        
        #self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'alert', {'t':t})
            self._runOnThread(right, 'alert', {'t':t})

        # Wait for all threads to stop
        self._joinThreads(threads) 


    def _sit(self, t=1):
        '''Put the animal into an sitting state'''
        
        #self._stopped = False

        # Rear legs down
        threads = []
        if len(self.legPairs)>=2:
            pair = len(self.legPairs)-1
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'kneeFullDown', {'t':t})
            self._runOnThread(right, 'kneeFullDown', {'t':t})        

        # Front legs up       
        left = 'L0'
        right = 'R0'
        threads += [left,right]
        self._runOnThread(left, 'sit', {'t':t})
        self._runOnThread(right, 'sit', {'t':t}) 

        """   

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'sit', {'t':t})
            self._runOnThread(right, 'sit', {'t':t})    

        """

        # Wait for all threads to stop
        self._joinThreads(threads)        


    def _jump(self):
        self._alert(t=0)


    def _turn(self):
        '''Turn around'''

        #self._stopped = False

        speed = 10

        for i in range(7): #!! will depend on size/shape of robot
            # Move limbs into position, one at a time
            # ---------------------------------------
                               
            t = self.settings['REACHTIME'] / speed

            # Move front limbs
            self._runOnThread('L0', 'reachBackward', {'t':t})
            self._joinThreads(['L0'])
            self._waitRandom() 
            self._runOnThread('R0', 'reachForward', {'t':t})
            self._joinThreads(['R0'])
            self._waitRandom() 

            if self.numLegs > 2:
                # Move middle limbs
                self._runOnThread('L1', 'reachBackward', {'t':t})
                self._waitRandom() 
                self._runOnThread('R1', 'reachForward', {'t':t})
                self._joinThreads(['L1','R1'])
                self._waitRandom() 

            if self.numLegs > 4:
                # Move rear limbs
                self._runOnThread('L2', 'reachBackward', {'t':t})
                self._joinThreads(['L2'])
                self._waitRandom() 
                self._runOnThread('R2', 'reachForward', {'t':t})
                self._joinThreads(['R2'])
                self._waitRandom() 

            t = self.settings['PUSHTIME'] / speed

            # Move limbs together
            # -------------------

            # Move front limbs
            self._runOnThread('L0', 'pushForward', {'t':t})
            self._runOnThread('R0', 'pushBackward', {'t':t})
            legs = ['L0','R0']

            if self.numLegs > 2:
                sleep(self.settings['PUSHDELAY'])
                self._runOnThread('L1', 'pushForward', {'t':t})
                self._runOnThread('R1', 'pushBackward', {'t':t})
                legs = ['L1','R1']

            if self.numLegs > 4:
                sleep(self.settings['PUSHDELAY'])
                self._runOnThread('L2', 'pushForward', {'t':t})
                self._runOnThread('R2', 'pushBackward', {'t':t})
                legs = ['L2','R2']

            # Wait for all legs to stop
            self._joinThreads(legs)

            # If request was made to end walk, break out of loop
            if self._stopped:
                break  

        self._stopMovements()

    def _kneesup(self, t=1):
        '''Lift knees all the way up'''
        
        #self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'kneeFullUp', {'t':t})
            self._runOnThread(right, 'kneeFullUp', {'t':t})            

        # Wait for all threads to stop
        self._joinThreads(threads)                     
       

    def _kneesdown(self, t=1):
        '''Put knees all the way down'''
        
        #self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'kneeFullDown', {'t':t})
            self._runOnThread(right, 'kneeFullDown', {'t':t})            

        # Wait for all threads to stop
        self._joinThreads(threads)    
          
    def _hipsbackward(self, t=1):
        '''Push hips all the way backwards'''
        
        #self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'hipFullBackward', {'t':t})
            self._runOnThread(right, 'hipFullBackward', {'t':t})            

        # Wait for all threads to stop
        self._joinThreads(threads)                     
       

    def _hipsforward(self, t=1):
        '''Push hips all the way forwards'''
        
        #self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'hipFullForward', {'t':t})
            self._runOnThread(right, 'hipFullForward', {'t':t})            

        # Wait for all threads to stop
        self._joinThreads(threads)    

    def _detectMovement(self):
        '''Stop and check for movement. '''

        #self._stopped = False

        # Put in alert state
        self._alert()

        noMovementCount = 0

        while True:
            # Keep still and see if there is any movement
            if self.head.detectMovement():
                # Significant movement detected
                self.log.info("Movement detected")
                #self._setTimer(30, self._timerAction) # delay the next action, so we have time to track the movement !!
                #!! would want to do something, e.g. track or call back 

            # If request was made to end , break out of loop
            if self._stopped:
                self.log.info("Stopped detect movement")
                break         

            sleep(0.2)       

    def _trackMovement(self):
        '''Stop and check for movement.  If movement detected, track it for a while'''

        self.log.info("_trackMovement")

        #self._stopped = False

        #self.cry()

        #sleep(random.randint(2, 5))

        # Bounce for a bit
        #self._bounce()

        # Put in alert state
        #self._scare()

        #self.stopCry()


        #self._setTimer(30, self._timerAction) # delay the next action, so we have time to track the movement !!

        if self.settings['HUMANTRACKING']:
            noMovementCount = 0

            while True:
                print("Stopped",self._stopped)
                # Track the movement that was detected
                if self.head.trackMovement():
                    noMovementCount = 0 # reset
                    #self.log.info("Still tracking")
                else:
                    noMovementCount += 1
                    if noMovementCount > 30: #!!
                        # Waited for a while and not movement detected, so stop tracking
                        self.log.info("Stopped tracking due to no movement")
                        #self._setTimer(0, self._timerAction) # start the next action immediately
                        self._stopped = True

                # If request was made to end , break out of loop
                if self._stopped:
                    self.log.info("Stopped track movement")
                    break         

                sleep(0.1)
        else:
            # Just do one movement
            self.head.trackMovement()
        

    def _trackHotspot(self):
        # Put in alert state
        self._alert()

        self.log.info("Tracking human")

        while True:
            # Turn head.  col is column in which heat detected (0=left, 7=right)
            col = self.head.trackHotspot()
            
            if col is None:
                break

            self._printTracking(col)

            # If request was made to end , break out of loop
            if self._stopped:
                #self.log.info("Stopped detect movement")
                break         

            sleep(0.2)            

        self.log.info("Stopped tracking human")

    def _printTracking(self, col):
        if self.messageCallback is not None:   
            marker = '^'.rjust(col*2)
            line1 = "Tracking"
            line2 = marker
            self.messageCallback(line1, line2)         

    """
    def setAngles(self):
        '''Point forwards'''
        
        #self._stopped = False

        # Set up a thread for each limb movement
        threads = []
        for pair in range(len(self.legPairs)):
            settings = self.settings["leg_ranges"][pair]
            print(settings["left"]["hip"])
            angles = (settings["left"]["hip"][2], settings["left"]["knee"][1])
            threads.append(Thread(target=self.legPairs[pair].left.setAngles, kwargs={"angles":angles, "t":1}))
            angles = (settings["right"]["hip"][2], settings["right"]["knee"][1])
            threads.append(Thread(target=self.legPairs[pair].right.setAngles, kwargs={"angles":angles, "t":1}))

        # Move all legs into position simulaneously
        runThreadsTogether(threads) 
    """

if __name__ == "__main__":
    print("Testing Animal")    


    # Create animal
    animal = Animal()

    #animal.log.setLevel(logging.DEBUG)

    # With 2 legs           
    animal.addPairOfLegs(Leg(Joint(0), Joint(1), 1), Leg(Joint(2), Joint(3), -1))
    
    # With 4 legs           
    animal.addPairOfLegs(Leg(Joint(4), Joint(5), 1), Leg(Joint(6), Joint(7), -1))

    # Load settings from json file
    animal.loadSettings()

    print("wakeSlowly")
    animal.wakeSlowly(2) 

    t = 10



    # Run through all the actions

    animal.runAction(animal._sit)
    sleep(t)

    """
    for i in range(20):
      animal.runAction(animal._forward)
      sleep(t)

    animal.runAction(animal._backward)
    sleep(t)

    animal.runAction(animal._right)
    sleep(t)

    animal.runAction(animal._left)
    sleep(t)

    animal.runAction(animal._backRight)
    sleep(t)

    animal.runAction(animal._backLeft)
    sleep(t)
    """

    """ 
    animal.runAction(animal._point)
    sleep(t)

    animal.runAction(animal._eat)
    sleep(t)

    animal.runAction(animal._unwind)
    sleep(t)

    animal.runAction(animal._alert)
    sleep(t)

    animal.runAction(animal._sit)
    sleep(t)

    animal.runAction(animal._kneesup)
    sleep(t)

    animal.runAction(animal._kneesdown)
    sleep(t) 

    animal.runAction(animal._hipsbackward)
    sleep(t) 

    animal.runAction(animal._hipsforward)
    sleep(t)   

    animal.runAction(animal._detectMovement)
    sleep(10)   

    animal.runAction(animal._trackMovement)
    sleep(30)   
    """

    animal.stopCurrentAction()

