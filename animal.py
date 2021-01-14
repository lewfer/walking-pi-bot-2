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
from joint import *
from leg import *
from time import sleep
import curses
import random
import json
import logging
import sys
from head import Head
from gpiozero import Button

# Constants
# -------------------------------------------------------------------------------------------------
SETTINGSFILENAME = 'animal_settings.json'

    

# Class
# -------------------------------------------------------------------------------------------------
class Animal():
    '''Animal has a number of pairs of legs'''

    def __init__(self):
        # Construction
        self.numLegs = 0                                                # number of legs - start with none
        self.legPairs = []                                              # start with no legs
        self.head = Head(self.interrupt)
        self.leftAntenna = Button(6)
        self.rightAntenna = Button(12)

        # Robot health
        # Can use these to determine behaviour, e.g. slowing down as energy drops
        self.alertness = 120
        self.energy = 1000
        self.age = 0

        # Flag to indicate when we last saw a human
        self.lastHumanDetectAge = -999

        # Helper objects, to idenntify legs and threads
        self._legs = {}                                                  # dictionary to quickly find legs
        self._threads = {}                                               # dictionary to quickly find threads

        # Manage current and next action
        self._currentAction = None              # current action being run (one-letter code)
        self._actionThread = None               # thread on which current action is running
        self._timerDelay = 0                    # delay before next action runs
        self._timerAction = None                # action to run next (one-letter code)
        self._timerAgeStart = 0                 # age of robot when timer was started
        self._interruptId = None                # the current interrupt, if any
        self._interruptValue = None             # value associated with the interrupt
        self._interruptBeingHandled = None      # if we are currently executing the interrupt handling action
        self._threadCount = 0                   # so we can track threads
        self._stopped = False                   # flag to indicate if we want the animal to stop what it is doing (i.e. stop current thread)

        # Random action generator
        self._randomThread = None        # thread on which random action generator runs
        self._runningRandom = False      # flag to indicate that random thread is running

        # Antennae handlers
        self.leftAntenna.when_pressed = self._leftAntennaPressed
        self.rightAntenna.when_pressed = self._rightAntennaPressed

        # Set up logger to log to screen
        self.log = logging.getLogger('logger')
        self.log.setLevel(logging.INFO)
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter('%(message)s'))  
        self.log.addHandler(h)     

        # Caller can register a callback to receive messages (for display purposes)
        self.messageCallback = None

        # List of one-letter action codes and the associated actions
        self.actionFunction = {
            '*':'do_default()',
            'F':'do_forward()', 
            'B':'do_backward()',
            'L':'do_left()',
            'R':'do_right()',
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
            'T':'do_trackHotspot()'
            }

        self.log.info("Created Animal")


    # Construction
    # ---------------------------------------------------------------------------------------------

    def addPairOfLegs(self, left, right):
        '''Add legs from front to back'''
        index = len(self.legPairs)
        self.legPairs.append(LegPair(left, right))

        # Add to legs dictionary
        self._legs['L'+str(index)] = self.legPairs[index].left
        self._legs['R'+str(index)] = self.legPairs[index].right

        # Add to legs threads
        self._threads['L'+str(index)] = None
        self._threads['R'+str(index)] = None

        self.numLegs += 2


    # Settings 
    # ---------------------------------------------------------------------------------------------

    def setDefaultSettings(self):
        self.settings = {"leg_ranges": []}
        # knee order: down, mid, up
        # hip order: back, mid, forward
        for i in range(len(self.legPairs)):
            self.settings["leg_ranges"].append({"left": {"hip": [130,90,70],"knee": [50,90,130]},"right": {"hip": [50,90,110],"knee": [130,90,50]}})

        self.settings['REACHTIME'] = 1
        self.settings['PUSHTIME'] = 1
        self.settings['PUSHDELAY'] = 0

        # Random wait time between certain movements, in tenths of a second
        self.settings['RANDOMWAIT'] = 2    

        self.settings['STEPSPERDEGREE'] = 1

        # Weights for random movement action choices
        #                                 ['.','S','B','L','R','U','P','E','A','+','-']
        self.settings['RANDOMWEIGHTS'] = [  40, 10, 1,  3,  3,  2,  2,  1,  1,  20,  1]

        # Min/max time for action to run
        self.settings['RANDOMTIME'] = {'B':[2,8],'L':[2,6],'R':[2,6],'S':[2,30],'P':[2,30],'E':[2,30],'A':[2,30],'U':[5,50],'M':[10,20],'+':[2,10],'-':[2,10]}

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
        self.settings['SHORTDISTANCE'] = 20     # triggers short-distance interrupt when distance less than this
        self.settings['LONGDISTANCE'] = 200     # triggers long-distance interrupt when distance more than this
        self.settings['HUMANDETECTMIN'] = 24    # triggers human-detect interrupt when heat between min and max
        self.settings['HUMANDETECTMAX'] = 30    # triggers human-detect interrupt when head between min and max


    def loadSettings(self):
        '''Load the settings file, which contains the calibrated settings for each joint'''
        self.setDefaultSettings()
        try:
            # Try to load the settings file
            with open(SETTINGSFILENAME) as f:
                self.log.info("Settings {} found".format(SETTINGSFILENAME))
                self.settings.update(json.load(f))
                self.storeSettings() # in case we added new defaults
        except FileNotFoundError:
            # If no settings file use defaults 
            self.log.info("Settings file {} not found.  Using defaults".format(SETTINGSFILENAME))
            self.storeSettings()
            #self.factoryReset()
        self.log.info(self.settings)

        self.applySettings()

    def applySettings(self):
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

            #print(self.legPairs[pair].left.hip)
            #print(self.legPairs[pair].left.knee)
            #print(self.legPairs[pair].right.hip)
            #print(self.legPairs[pair].right.knee)

        self._setStepsPerDegree(self.settings['STEPSPERDEGREE'])

    def storeSettings(self):
        '''Store the default settings to the settings file'''
        # Save the settings dictionary to file
        with open(SETTINGSFILENAME, 'w') as f:
            json.dump(self.settings, f)

    def storeAndReapplySettings(self):
        '''Store the default settings to the settings file'''
        self.storeSettings()

        # Reload so settings are applied
        self.loadSettings()

    def factoryReset(self):
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


    # Handlers for actions 
    # ---------------------------------------------------------------------------------------------

    def do_default(self):
        """Do the default action, which is to look around and move off left, right or forward"""
        print("Do default")

        # Stop movements ready for scan
        self.stopCurrentAction()

        # Do a scan (move head from side-to-side) looking for short distances
        self.head.pauseSensors()   # pause sensors while we scan
        distances, minpos, maxpos, movement = self.head.scan()
        print(distances, minpos, maxpos)

        # Check what we saw
        if distances[minpos] < self.settings['SHORTDISTANCE'] : 
            # We are too close to something
            if minpos <= 10:  # 10 readings on the left side
                self.log.info("Veer right")
                self._handleAction(self.right, "R")
            elif minpos > 10:  # 10 readings on the right side
                self.log.info("Veer left")
                self._handleAction(self.left, "L")
            self._setTimer(2, '*')                   # back to default when finished
        elif movement:
            # We saw something move
            self._handleAction(self.detectMovement, "M")
            print("MMMM")
            minmax = self.settings['RANDOMTIME']['M']                   # min/max time for action to run (from settings)
            self._setTimer(random.randint(minmax[0],minmax[1]), 'F')   
        else:
            # We are not too close to anything
            self._handleAction(self.forward, "F")
        self.head.unPauseSensors()   # turn sensors back on 

    def endInterrupt(self):
        """Reset back to default behaviour following an interrupt"""
        self._clearInterrupt()
        self.do_default()

    def do_forward(self):
        self.head.move(0, t=1)
        self._handleAction(self.forward, "F")
        self.head.unPauseSensors()   # turn sensors back on for moving forwards

    def do_backward(self):
        self.head.move(0, t=1)
        self._handleAction(self.backward, "B")

    def clear_left(self):
        """Check if all clear on the left"""
        self.log.info("Check left")
        self.head.pauseSensors()   # pause sensors while we scan
        distances, minpos, maxpos = self.head.scanLeft()
        print(distances, minpos, maxpos)
        clear = distances[minpos] > self.settings['SHORTDISTANCE']
        self.head.unPauseSensors()   # turn sensors back on 
        return clear

    def clear_right(self):
        """Check if all clear on the right"""
        self.log.info("Check right")
        self.head.pauseSensors()   # pause sensors while we scan
        distances, minpos, maxpos = self.head.scanRight()
        print(distances, minpos, maxpos)
        clear = distances[minpos] > self.settings['SHORTDISTANCE']
        self.head.unPauseSensors()   # turn sensors back on 
        return clear

    def do_left(self):
        print("Do left")
        # Stop movements ready for scan
        self.stopCurrentAction()
        
        if self.clear_left():
            self.head.move(-100, t=1)
            self._handleAction(self.left, "L")
        elif not self.clear_right():
            # In a pickle
            self.log.info("In a pickle")
            self.do_backward()

    def do_right(self):
        print("Do right")
        # Stop movements ready for scan
        self.stopCurrentAction()

        if self.clear_right():      
            self.head.move(100, t=1)
            self._handleAction(self.right, "R")
        elif not self.clear_left():
            # In a pickle
            self.log.info("In a pickle")
            self.do_backward()

    def do_wait(self):
        self._handleAction(None, "W")

    def do_unwind(self):
        self._handleAction(self.unwind, "U")

    def do_point(self):
        self._handleAction(self.point, "P")

    def do_eat(self):
        self._handleAction(self.eat, "E")

    def do_sit(self):
        self._handleAction(self.sit, "S")

    def do_kneesup(self):
        self._handleAction(self.kneesup, "^")

    def do_kneesdown(self):
        self._handleAction(self.kneesdown, "v")

    def do_hipsbackward(self):
        self._handleAction(self.hipsbackward, "<")

    def do_hipsforward(self):
        self._handleAction(self.hipsforward, ">")

    def do_alert(self):
        self._handleAction(self.alert, "A")

    def do_detectMovement(self):
        self._handleAction(self.detectMovement, "M")

    def do_trackHotspot(self):
        self._handleAction(self.trackHotspot, "T")
    
    def do_run(self):
        self._handleAction(self.run, "+")

    def do_crawl(self):
        self._handleAction(self.crawl, "-")


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
        
    def stopCurrentAction(self):
        self._stopMovements()
        if self._actionThread: self._actionThread.join()


    def _handleAction(self, func, msg):  
        """Stop any current action and start a new one"""
        self.log.info("Handling {}".format(msg))
        self._stopMovements()
        if self._actionThread: self._actionThread.join()
        if func is not None:
            self.log.info("Start {} thread".format(msg))
            self._actionThread = Thread(target=func)
            self._actionThread.start()   
        self._currentAction = msg

    def _setTimer(self, delay, action):
        """Cancel any existing timer and replace with this one.  Timers are used to """
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
        exec("self."+self.actionFunction[self._timerAction])
        self._timerAction = None
        self._timerDelay = 0
        self._timerAgeStart = 0

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
                self._handleInterrupt()

            elif self._currentAction=="M":
                # Detecting movement, so let's finish that before we allow another random movement
                pass

            elif self.age % 5 == 0: #!!every 5 seconds
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
                    elif self.head.lastDistance<200: #!!
                        self.log.info("Not enough distance to run")
                        choice = '.'
                    else:
                        pass # !! set time proportional to last distance?

                # Start the choice, and set a timer to start moving forward again after a random period
                if choice != '.':
                    self.log.info("Initiating action {}".format(choice))
                    exec("self."+self.actionFunction[choice])
                    minmax = self.settings['RANDOMTIME'][choice]    # min/max time for action to run (from settings)
                    self._setTimer(random.randint(minmax[0],minmax[1]), '*')                   

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
                self.do_backward()
                minmax = self.settings['RANDOMTIME']['B']   
                self._setTimer(random.randint(minmax[0],minmax[1]), 'I')       

            elif self._interruptId=="left-antenna":
                self.do_right()
                minmax = self.settings['RANDOMTIME']['R']   
                self._setTimer(random.randint(minmax[0],minmax[1]), 'I')    

            elif self._interruptId=="right-antenna":
                self.do_left()
                minmax = self.settings['RANDOMTIME']['L']   
                self._setTimer(random.randint(minmax[0],minmax[1]), 'I')    

            elif self._interruptId=="human-detect":
                # If we haven't seen a human for a while, stop to detect human

                    self.lastHumanDetectAge = self.age
                    self.do_detectMovement()
                    minmax = self.settings['RANDOMTIME']['M']   
                    self._setTimer(random.randint(minmax[0],minmax[1]), 'I')   


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

    # Sensors
    # ---------------------------------------------------------------------------------------------

    def _leftAntennaPressed(self):
        self.interrupt("left-antenna", 0)

    def _rightAntennaPressed(self):
        self.interrupt("right-antenna", 0)


    # Threading
    # ---------------------------------------------------------------------------------------------
    def _runOnThread(self, legId, func, params):
        """Run the function func on the leg identified by legId with the given params.  Wait for any existing thread to finish first"""

        # Get the thread associated with the leg
        thread = self._threads[legId]

        # Wait for existing thread to finish
        if thread is not None:
            self.log.debug("\tWait for thread {} before create new {} for {}".format(thread.name, legId, func))
            thread.join()
        else:
            self.log.debug("\tNo existing thread for {}".format(legId))

        # Start the new thread
        funcEval = eval('self._legs[legId].'+func)
        threadName = legId + ":" + func + ":" + str(self._threadCount)
        self._threadCount += 1
        thread = Thread(target=funcEval, name=threadName, kwargs=params)
        thread.start()
        #oldname = thread.name
        #thread.name = legId + ":" + func
        self.log.debug("\tStarted new thread{}".format(thread.name))

        # Store the thread against the leg
        self._threads[legId] = thread

    def _joinThreads(self, legIds):
        """Wait for all threads to finish for the specified legs"""
        for legId in legIds:
            thread = self._threads[legId]
            if thread is not None:
                thread.join()

    def _stopThreads(self):
        self.log.debug("Stopping threads:", self._threads)
        # Stop all threads for all legs
        for i, k in enumerate(self._threads):
            thread = self._threads[k]
            if thread is not None:
                self.log.debug("Joining {}".format(thread.name))
                thread.join()        
                self._threads[k] = None
        
        #self.log.debug("Stopped threads: {}".format(activeCount()))





    # Actions
    # ---------------------------------------------------------------------------------------------

    def _waitRandom(self):
        '''Wait for a random time (in tenths of a second)'''
        sleep(random.randint(0,self.settings['RANDOMWAIT'])/10.0) 


    def run(self):
        self.forward(speed=2)

    def crawl(self):
        self.forward(speed=0.5)        

    def forward(self, speed=1):
        '''Move forward'''
                
        self._stopped = False

        while True:
            # Move limbs forwards, one at a time
            # ----------------------------------
            
            t = self.settings['REACHTIME'] / speed

            # Move front limbs 
            self._runOnThread('L0', 'reachForward', {'t':t})
            self._joinThreads(['L0'])
            self._waitRandom() 
            self._runOnThread('R0', 'reachForward', {'t':t})
            self._joinThreads(['R0'])
            self._waitRandom() 

            if self.numLegs > 2:
                # Move middle limbs 
                self._runOnThread('L1', 'reachForward', {'t':t})
                self._waitRandom() 
                self._runOnThread('R1', 'reachForward', {'t':t})
                self._joinThreads(['L1','R1'])
                self._waitRandom() 

            if self.numLegs > 4:
                # Move rear limbs
                self._runOnThread('L2', 'reachForward', {'t':t})
                self._joinThreads(['L2'])
                self._waitRandom() 
                self._runOnThread('R2', 'reachForward', {'t':t})
                self._joinThreads(['R2'])
                self._waitRandom()             

            # Move limbs backwards together
            # -----------------------------

            t = self.settings['PUSHTIME'] / speed

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

            # If request was made to end walk, break out of loop
            if self._stopped:
                break   


    def backward(self):
        '''Move backward'''
                
        self._stopped = False

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

    def right(self):
        '''Move right'''
                
        self._stopped = False

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
                self._runOnThread('L1', 'pushForward', {'t':t})
                self._runOnThread('R1', 'pushBackward', {'t':t})
                legs = ['L1','R1']

            if self.numLegs > 4:
                # Move rear limbs
                sleep(self.settings['PUSHDELAY'])
                self._runOnThread('L2', 'pushForward', {'t':t})
                self._runOnThread('R2', 'pushBackward', {'t':t})
                legs = ['L2','R2']

            # Wait for all legs to stop
            self._joinThreads(legs)        

            # If request was made to end walk, break out of loop
            if self._stopped:
                break    

    def left(self):
        '''Move left'''
                
        self._stopped = False

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
                self._runOnThread('L1', 'reachForward', {'t':t})
                self._waitRandom() 
                self._runOnThread('R1', 'reachBackward', {'t':t})
                self._joinThreads(['L1','R1'])
                self._waitRandom() 

            if self.numLegs > 4:
                # Move rear limbs
                self._runOnThread('L2', 'reachForward', {'t':t})
                self._joinThreads(['L2'])
                self._waitRandom() 
                self._runOnThread('R2', 'reachBackward', {'t':t})
                self._joinThreads(['R2'])
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
                self._runOnThread('L1', 'pushBackward', {'t':t})
                self._runOnThread('R1', 'pushForward', {'t':t})
                legs = ['L1','R1']

            if self.numLegs > 4:
                sleep(self.settings['PUSHDELAY'])
                self._runOnThread('L2', 'pushBackward', {'t':t})
                self._runOnThread('R2', 'pushForward', {'t':t})
                legs = ['L2','R2']

            # Wait for all legs to stop
            self._joinThreads(legs)

            # If request was made to end walk, break out of loop
            if self._stopped:
                break  

    def point(self):
        '''Point'''

        self._stopped = False
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

    def eat(self):
        '''Eat'''
        self.log.info("eat")

        self._stopped = False
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

    def wakeSlowly(self, t=5):
        '''Move all legs slowly to their mid position.  The slow wake prevents a surge in current draw that could shut down the Pi.'''
       
        self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'mid', {'t':t})
            self._runOnThread(right, 'mid', {'t':t})
        self._joinThreads(threads)

    def unwind(self, t=1):
        '''Put the animal into a relaxing state (crouched down)'''
        
        self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'unwind', {'t':t})
            self._runOnThread(right, 'unwind', {'t':t})
        self._joinThreads(threads)


    def alert(self, t=1):
        '''Put the animal into an alert state (standing upright)'''
        
        self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'alert', {'t':t})
            self._runOnThread(right, 'alert', {'t':t})
        self._joinThreads(threads) 


    def sit(self, t=1):
        '''Put the animal into an sitting state'''
        
        self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'sit', {'t':t})
            self._runOnThread(right, 'sit', {'t':t})    
        self._joinThreads(threads)         
   

    def kneesup(self, t=1):
        '''Lift knees all the way up'''
        
        self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'kneeFullUp', {'t':t})
            self._runOnThread(right, 'kneeFullUp', {'t':t})            
        self._joinThreads(threads)                     
       

    def kneesdown(self, t=1):
        '''Put knees all the way down'''
        
        self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'kneeFullDown', {'t':t})
            self._runOnThread(right, 'kneeFullDown', {'t':t})            
        self._joinThreads(threads)    
          
    def hipsbackward(self, t=1):
        '''Push hips all the way backwards'''
        
        self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'hipFullBackward', {'t':t})
            self._runOnThread(right, 'hipFullBackward', {'t':t})            
        self._joinThreads(threads)                     
       

    def hipsforward(self, t=1):
        '''Push hips all the way forwards'''
        
        self._stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self._runOnThread(left, 'hipFullForward', {'t':t})
            self._runOnThread(right, 'hipFullForward', {'t':t})            
        self._joinThreads(threads)    
          

    def detectMovement(self):
        '''Stop and check for movement.  If movement detected, track it for a while'''

        # Put in alert state
        self.alert()

        tracking = False

        noMovementCount = 0

        while True:
            if tracking:
                # Track the movement that was detected
                if self.head.trackMovement():
                    noMovementCount = 0 # reset
                    #self.log.info("Still tracking")
                else:
                    noMovementCount += 1
                    if noMovementCount > 30: #!!
                        # Waited for a while and not movement detected, so stop tracking
                        self.log.info("Stopped tracking due to no movement")
                        self._setTimer(0, self._timerAction) # start the next action immediately
            else:
                # Keep still and see if there is any movement
                if self.head.detectMovement():
                    # Significant movement detected
                    self.log.info("Movement detected so start tracking human")
                    self._setTimer(30, self._timerAction) # delay the next action, so we have time to track the movement !!
                    tracking = True

            # If request was made to end , break out of loop
            if self._stopped:
                self.log.info("Stopped detect movement")
                break         

            sleep(0.2)           

    def trackHotspot(self):
        # Put in alert state
        self.alert()

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
        
        self._stopped = False

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


    def _stopMovements(self):
        '''Stop the current action'''
        self._stopped = True

        # Stop all servos
        for pair in range(len(self.legPairs)):
            self.legPairs[pair].left.stop()
            self.legPairs[pair].right.stop()

        # Stop all threads
        self._stopThreads()



if __name__ == "__main__":
    print("Testing Animal")    


    # Create animal
    animal = Animal()

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
    