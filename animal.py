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
        self.numLegs = 0                                                # number of legs - start with none
        self.legPairs = []                                              # start with no legs
        self.stopped = False                                            # flag to indicate if we want the animal to stop what it is doing
        self._legs = {}                                                  # dictionary to quickly find legs
        self._threads = {}                                               # dictionary to quickly find threads
        self.threadCount = 0

        # Manage current and next action
        self.currentAction = None       # current action being run (one-letter code)
        self.actionThread = None        # thread on which current action is running
        self.timerDelay = 0             # delay before next action runs
        self.timerAction = None         # action to run next (one-letter code)
        self.timerAgeStart = 0          # age of robot when timer was started
        self.interruptId = None         # the current interrupt, if any
        self.interruptValue = None      # value associated with the interrupt
        self.interruptBeingHandled = None   # if we are currently executing the interrupt handling action

        # Random action generator
        self.randomThread = None        # thread on which random action generator runs
        self.runningRandom = False      # flag to indicate that random thread is running

        # Robot health
        # Can use these to determine behaviour, e.g. slowing down as energy drops
        self.alertness = 120
        self.energy = 1000
        self.age = 0


        self.head = Head(self.interrupt)

        # Antennae
        self.leftAntenna = Button(6)
        self.rightAntenna = Button(12)
        self.antennaeThread = None
        self.leftAntenna.when_pressed = self.leftAntennaPressed
        self.rightAntenna.when_pressed = self.rightAntennaPressed

        # Set up logger to log to screen
        self.log = logging.getLogger('logger')
        self.log.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        h = logging.StreamHandler(sys.stdout)
        #h.setLevel(logging.INFO)
        h.setFormatter(formatter)  
        self.log.addHandler(h)      
        self.log.info("Created Animal")

        self.messageCallback = None

        # List of one-letter action codes and the associated actions
        self.actionFunction = {
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


    # Handlers for actions 
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
        #                                 ['F','S','B','L','R','U','P','E','A','+','-']
        self.settings['RANDOMWEIGHTS'] = [  40, 10, 1,  3,  3,  2,  2,  1,  1,  20,  1]

        # Min/max time for action to run
        self.settings['RANDOMTIME'] = {'B':[2,8],'L':[2,15],'R':[2,15],'S':[2,30],'P':[2,30],'E':[2,30],'A':[2,30],'U':[5,50],'M':[5,10],'+':[2,10],'-':[2,10]}

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
        self.settings['SHORTDISTANCE'] = 10     # triggers short-distance interrupt when distance less than this
        self.settings['LONGDISTANCE'] = 200     # triggers long-distance interrupt when distance more than this
        self.settings['HEATDETECT'] = 26        # triggers heat-detect interrupt when head more than this


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
            self.head.heatDetect = self.settings['HEATDETECT'] 

            #print(self.legPairs[pair].left.hip)
            #print(self.legPairs[pair].left.knee)
            #print(self.legPairs[pair].right.hip)
            #print(self.legPairs[pair].right.knee)

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



    # Handlers for actions 
    # ---------------------------------------------------------------------------------------------

    def endInterrupt(self):
        self.clearInterrupt()
        self.do_forward()


    def do_forward(self):
        self.handleAction(self.forward, "F")
        self.head.unPauseSensors()   # turn sensors back on for moving forwards

    def do_backward(self):
        self.handleAction(self.backward, "B")

    def do_left(self):
        self.handleAction(self.left, "L")

    def do_right(self):
        self.handleAction(self.right, "R")

    def do_wait(self):
        self.handleAction(None, "W")

    def do_unwind(self):
        self.handleAction(self.unwind, "U")

    def do_point(self):
        self.handleAction(self.point, "P")

    def do_eat(self):
        self.handleAction(self.eat, "E")

    def do_sit(self):
        self.handleAction(self.sit, "S")

    def do_kneesup(self):
        self.handleAction(self.kneesup, "^")

    def do_kneesdown(self):
        self.handleAction(self.kneesdown, "v")

    def do_hipsbackward(self):
        self.handleAction(self.hipsbackward, "<")

    def do_hipsforward(self):
        self.handleAction(self.hipsforward, ">")

    def do_alert(self):
        self.handleAction(self.alert, "A")

    def do_detectMovement(self):
        self.handleAction(self.detectMovement, "M")

    def do_trackHotspot(self):
        self.handleAction(self.trackHotspot, "T")
    
    def do_run(self):
        self.handleAction(self.run, "+")

    def do_crawl(self):
        self.handleAction(self.crawl, "-")


    # Action management
    # ---------------------------------------------------------------------------------------------
    def handleAction(self, func, msg):  
        """Stop any current action and start a new one"""
        self.stopMovements()
        if self.actionThread: self.actionThread.join()
        self.log.info("Handling {}".format(msg))
        if func is not None:
            self.actionThread = Thread(target=func)
            self.actionThread.start()   
        self.currentAction = msg

    def setTimer(self, delay, action):
        """Cancel any existing timer and replace with this one.  Timers are used to """
        self.log.info("Set timer {} in {} secs".format(action, delay))
        #if self.timer is not None:
        #    self.timer.cancel()
        self.timerAgeStart = self.age
        #self.timer = Timer(delay, self.actionFunction[action])
        #self.timer.start()
        self.timerDelay = delay
        self.timerAction = action

    def executeTimer(self):
        #!!surely need to stop previous action?
        exec("self."+self.actionFunction[self.timerAction])
        self.timerAction = None
        self.timerDelay = 0
        self.timerAgeStart = 0

    def start(self):
        """Start the robot"""
        self.do_forward()
        self.head.startSensors()
        self.startRandom()

    def stop(self):
        """Stop the robot"""
        #self.showMessage("Stopping","")
        self.log.info("Stopping")
        self.handleAction(None, "W")
        self.head.stopSensors()
        self.runningRandom = False

    def startRandom(self):
        """Start a random behaviour generator"""
        self.randomThread = Thread(target=self._runRandom)
        self.randomThread.start() 

    def _runRandom(self):
        """Continue to run random actions until stopped"""
        self.runningRandom = True
        while self.runningRandom:
            if self.timerAction is not None:
                if self.age-self.timerAgeStart >= self.timerDelay:
                    # There is a timer that has come of age, so execute it
                    self.executeTimer()
                    continue

            if self.interruptId is not None:
                self.handleInterrupt()
            elif self.age % 5 == 0: #!!every 5 seconds
                # No timer, so allow another random, weighted choice
                actions = ['F','S','B','L','R','U','P','E','A','+','-']
                weights = self.settings['RANDOMWEIGHTS']
                choice = random.choices(actions, weights)[0]
                self.log.info("random {}".format(choice))

                # Don't allow run if not enough space
                if choice=='+':
                    if self.head.lastDistance is None:
                        choice = 'F'
                    elif self.head.lastDistance<200: #!!
                        self.log.info("Not enough distance to run")
                        choice = 'F'
                    else:
                        pass # !! set time proportional to last distance?
                    
                # Start the choice, and set a timer to start moving forward again after a random period
                if choice != 'F':
                    self.log.info("Initiating action {}".format(choice))
                    exec("self."+self.actionFunction[choice])
                    minmax = self.settings['RANDOMTIME'][choice]    # min/max time for action to run (from settings)
                    self.setTimer(random.randint(minmax[0],minmax[1]), 'F')                   

            sleep(self.settings['TICKPERIOD'])

            # Adjust alertness
            if self.currentAction=='U':
                self.alertness += self.settings['UNWINDALERTNESSINCREASE']
            else:
                self.alertness -= 1

            # djust age
            self.age += 1

            self._printStatus()


    def _printStatus(self):
        """Print out the status for debugging"""
        self.log.info("{} alertness={} energy={} timernext={}_in_{}s threadcount={} interrupt={} dist={}".format(self.currentAction, self.alertness, self.energy, self.timerAction, self.timerDelay, activeCount(), self.interruptId, self.head.lastDistance))

        if self.messageCallback is not None:   
            if self.interruptId is None:
                self.messageCallback(self.actionFunction[self.currentAction],self.actionFunction[self.timerAction] if self.timerAction is not None else "")
            else:
                self.messageCallback("Interrupt",self.interruptId)
        







    # Interrupt handling
    # ---------------------------------------------------------------------------------------------
    def interrupt(self, id, value):

        # Don't allow interrupt to be interrupted
        if self.interruptId is not None:
            return

        self.log.info("Interrupt {}".format(id))            

        self.interruptId = id
        self.interruptValue = value

    def handleInterrupt(self):
        # Handle the interrupt
        if not self.interruptBeingHandled:
            self.log.info("Handle Interrupt {}".format(self.interruptId))
            self.interruptBeingHandled = True

            if self.interruptId=="short-distance":
                self.do_backward()
                minmax = self.settings['RANDOMTIME']['B']   
                self.setTimer(random.randint(minmax[0],minmax[1]), 'I')       

            elif self.interruptId=="left-antenna":
                self.do_right()
                minmax = self.settings['RANDOMTIME']['R']   
                self.setTimer(random.randint(minmax[0],minmax[1]), 'I')    

            elif self.interruptId=="right-antenna":
                self.do_left()
                minmax = self.settings['RANDOMTIME']['L']   
                self.setTimer(random.randint(minmax[0],minmax[1]), 'I')    

            elif self.interruptId=="heat-detect":
                self.do_detectMovement()
                minmax = self.settings['RANDOMTIME']['M']   
                self.setTimer(random.randint(minmax[0],minmax[1]), 'I')    

            elif self.interruptId=="long-distance":
                self.clearInterrupt()
                self.head.unPauseSensors()  
            """
                self.do_run()
                #minmax = self.settings['RANDOMTIME']['R']
                minmax[0] = 2
                minmax[1] = self.interruptValue / 20 # run time proportional to distance measured
                self.setTimer(random.randint(minmax[0],minmax[1]), 'I')
            """

    def clearInterrupt(self):
        self.interruptId = None
        self.interruptBeingHandled = False          

    # Sensors
    # ---------------------------------------------------------------------------------------------

    def leftAntennaPressed(self):
        self.interrupt("left-antenna")

    def rightAntennaPressed(self):
        self.interrupt("right-antenna")




    def setStepsPerDegree(self, spd): 
        '''Steps servo takes per angular degree.  Smaller means faster, but less smooth.  Recommended range 0.5 to 10.'''

        # Now set the steps per degree for each joint
        for pair in range(len(self.legPairs)):
            self.legPairs[pair].left.hip.stepsPerDegree = spd
            self.legPairs[pair].left.knee.stepsPerDegree = spd
            self.legPairs[pair].right.hip.stepsPerDegree = spd
            self.legPairs[pair].right.knee.stepsPerDegree = spd



    def runOnThread(self, legId, func, params):
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
        threadName = legId + ":" + func + ":" + str(self.threadCount)
        self.threadCount += 1
        thread = Thread(target=funcEval, name=threadName, kwargs=params)
        thread.start()
        #oldname = thread.name
        #thread.name = legId + ":" + func
        self.log.debug("\tStarted new thread{}".format(thread.name))

        # Store the thread against the leg
        self._threads[legId] = thread

    def joinThreads(self, legIds):
        """Wait for all threads to finish for the specified legs"""
        for legId in legIds:
            thread = self._threads[legId]
            if thread is not None:
                thread.join()

    def stopThreads(self):
        self.log.debug("Stopping threads:", self._threads)
        # Stop all threads for all legs
        for i, k in enumerate(self._threads):
            thread = self._threads[k]
            if thread is not None:
                self.log.debug("Joining {}".format(thread.name))
                thread.join()        
                self._threads[k] = None
        
        #self.log.debug("Stopped threads: {}".format(activeCount()))



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



    # Actions
    # ---------------------------------------------------------------------------------------------

    def waitRandom(self):
        '''Wait for a random time (in tenths of a second)'''
        sleep(random.randint(0,self.settings['RANDOMWAIT'])/10.0) 


    def run(self):
        self.forward(speed=2)

    def crawl(self):
        self.forward(speed=0.5)        

    def forward(self, speed=1):
        '''Move forward'''
                
        self.stopped = False

        while True:
            # Move limbs forwards, one at a time
            # ----------------------------------
            
            t = self.settings['REACHTIME'] / speed

            # Move front limbs 
            self.runOnThread('L0', 'reachForward', {'t':t})
            self.joinThreads(['L0'])
            self.waitRandom() 
            self.runOnThread('R0', 'reachForward', {'t':t})
            self.joinThreads(['R0'])
            self.waitRandom() 

            if self.numLegs > 2:
                # Move middle limbs 
                self.runOnThread('L1', 'reachForward', {'t':t})
                self.waitRandom() 
                self.runOnThread('R1', 'reachForward', {'t':t})
                self.joinThreads(['L1','R1'])
                self.waitRandom() 

            if self.numLegs > 4:
                # Move rear limbs
                self.runOnThread('L2', 'reachForward', {'t':t})
                self.joinThreads(['L2'])
                self.waitRandom() 
                self.runOnThread('R2', 'reachForward', {'t':t})
                self.joinThreads(['R2'])
                self.waitRandom()             

            # Move limbs backwards together
            # -----------------------------

            t = self.settings['PUSHTIME'] / speed

            # Move front limbs 
            self.runOnThread('L0', 'pushBackward', {'t':t})
            self.runOnThread('R0', 'pushBackward', {'t':t})
            legs = ['L0','R0']

            if self.numLegs > 2:
                # Move middle limbs 
                sleep(self.settings['PUSHDELAY'])
                self.runOnThread('L1', 'pushBackward', {'t':t})
                self.runOnThread('R1', 'pushBackward', {'t':t})
                legs += ['L1','R1']

            if self.numLegs > 4:
                # Move rear limbs
                sleep(self.settings['PUSHDELAY'])
                self.runOnThread('L2', 'pushBackward', {'t':t})
                self.runOnThread('R2', 'pushBackward', {'t':t})
                legs += ['L2','R2']

            # Wait for all legs to stop
            self.joinThreads(legs)

            # If request was made to end walk, break out of loop
            if self.stopped:
                break   


    def backward(self):
        '''Move backward'''
                
        self.stopped = False

        while True:
            # Move limbs backwards, one at a time
            # ----------------------------------
                        
            t = self.settings['REACHTIME']

            # Move front limbs
            self.runOnThread('L0', 'reachBackward', {'t':t})
            self.joinThreads(['L0'])
            self.waitRandom() 
            self.runOnThread('R0', 'reachBackward', {'t':t})
            self.joinThreads(['R0'])
            self.waitRandom() 

            if self.numLegs > 2:
                # Move middle limbs
                self.runOnThread('L1', 'reachBackward', {'t':t})
                self.waitRandom() 
                self.runOnThread('R1', 'reachBackward', {'t':t})
                self.joinThreads(['L1','R1'])
                self.waitRandom() 

            if self.numLegs > 4:
                # Move rear limbs
                self.runOnThread('L2', 'reachBackward', {'t':t})
                self.joinThreads(['L2'])
                self.waitRandom() 
                self.runOnThread('R2', 'reachBackward', {'t':t})
                self.joinThreads(['R2'])
                self.waitRandom() 

            t = self.settings['PUSHTIME']

            # Move limbs forwards together
            # -----------------------------

            # Move front limbs
            self.runOnThread('L0', 'pushForward', {'t':t})
            self.runOnThread('R0', 'pushForward', {'t':t})
            legs = ['L0','R0']

            if self.numLegs > 2:
                # Move middle limbs
                sleep(self.settings['PUSHDELAY'])
                self.runOnThread('L1', 'pushForward', {'t':t})
                self.runOnThread('R1', 'pushForward', {'t':t})
                legs += ['L1','R1']

            if self.numLegs > 4:
                # Move rear limbs
                sleep(self.settings['PUSHDELAY'])
                self.runOnThread('L2', 'pushForward', {'t':t})
                self.runOnThread('R2', 'pushForward', {'t':t})
                legs += ['L2','R2']

            # Wait for all legs to stop
            self.joinThreads(legs)

            # If request was made to end walk, break out of loop
            if self.stopped:
                break  

    def left(self):
        '''Move left'''
                
        self.stopped = False

        while True:
            # Move limbs into position, one at a time
            # ---------------------------------------
                
            t = self.settings['REACHTIME']

            # Move front limbs
            self.runOnThread('L0', 'reachForward', {'t':t})
            self.joinThreads(['L0'])
            self.waitRandom() 
            self.runOnThread('R0', 'reachBackward', {'t':t})
            self.joinThreads(['R0'])
            self.waitRandom() 

            if self.numLegs > 2:
                # Move middle limbs
                self.runOnThread('L1', 'reachBackward', {'t':t})
                self.waitRandom() 
                self.runOnThread('R1', 'reachForward', {'t':t})
                self.joinThreads(['L1','R1'])
                self.waitRandom() 

            if self.numLegs > 4:
                # Move rear limbs
                self.runOnThread('L2', 'reachBackward', {'t':t})
                self.joinThreads(['L2'])
                self.waitRandom() 
                self.runOnThread('R2', 'reachForward', {'t':t})
                self.joinThreads(['R2'])
                self.waitRandom() 


            # Move limbs forwards together
            # -----------------------------

            t = self.settings['PUSHTIME']

            # Move front limbs
            self.runOnThread('L0', 'pushBackward', {'t':t})
            self.runOnThread('R0', 'pushForward', {'t':t})
            legs = ['L0','R0']

            if self.numLegs > 2:
                # Move middle limbs
                sleep(self.settings['PUSHDELAY'])
                self.runOnThread('L1', 'pushForward', {'t':t})
                self.runOnThread('R1', 'pushBackward', {'t':t})
                legs = ['L1','R1']

            if self.numLegs > 4:
                # Move rear limbs
                sleep(self.settings['PUSHDELAY'])
                self.runOnThread('L2', 'pushForward', {'t':t})
                self.runOnThread('R2', 'pushBackward', {'t':t})
                legs = ['L2','R2']

            # Wait for all legs to stop
            self.joinThreads(legs)        

            # If request was made to end walk, break out of loop
            if self.stopped:
                break    

    def right(self):
        '''Move right'''
                
        self.stopped = False

        while True:
            # Move limbs into position, one at a time
            # ---------------------------------------
                               
            t = self.settings['REACHTIME']

            # Move front limbs
            self.runOnThread('L0', 'reachBackward', {'t':t})
            self.joinThreads(['L0'])
            self.waitRandom() 
            self.runOnThread('R0', 'reachForward', {'t':t})
            self.joinThreads(['R0'])
            self.waitRandom() 

            if self.numLegs > 2:
                # Move middle limbs
                self.runOnThread('L1', 'reachForward', {'t':t})
                self.waitRandom() 
                self.runOnThread('R1', 'reachBackward', {'t':t})
                self.joinThreads(['L1','R1'])
                self.waitRandom() 

            if self.numLegs > 4:
                # Move rear limbs
                self.runOnThread('L2', 'reachForward', {'t':t})
                self.joinThreads(['L2'])
                self.waitRandom() 
                self.runOnThread('R2', 'reachBackward', {'t':t})
                self.joinThreads(['R2'])
                self.waitRandom() 

            t = self.settings['PUSHTIME']

            # Move limbs together
            # -------------------

            # Move front limbs
            self.runOnThread('L0', 'pushForward', {'t':t})
            self.runOnThread('R0', 'pushBackward', {'t':t})
            legs = ['L0','R0']

            if self.numLegs > 2:
                sleep(self.settings['PUSHDELAY'])
                self.runOnThread('L1', 'pushBackward', {'t':t})
                self.runOnThread('R1', 'pushForward', {'t':t})
                legs = ['L1','R1']

            if self.numLegs > 4:
                sleep(self.settings['PUSHDELAY'])
                self.runOnThread('L2', 'pushBackward', {'t':t})
                self.runOnThread('R2', 'pushForward', {'t':t})
                legs = ['L2','R2']

            # Wait for all legs to stop
            self.joinThreads(legs)

            # If request was made to end walk, break out of loop
            if self.stopped:
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
            angles = (settings["left"]["hip"][LEG_FRONT]+random.randint(-jitter,jitter), settings["left"]["knee"][LEG_MID]+kneeOffsetFromMid+random.randint(-jitter,jitter))
            self.runOnThread('L0', 'setAngles', {'angles':angles,'t':t})
            
            # Set right leg position, with jitter
            angles = (settings["right"]["hip"][LEG_FRONT]+random.randint(-jitter,jitter), settings["right"]["knee"][LEG_MID]-kneeOffsetFromMid+random.randint(-jitter,jitter))
            self.runOnThread('R0', 'setAngles', {'angles':angles,'t':t})

            legs = ['L0','R0']

            if self.numLegs > 2:
                self.runOnThread('L1', 'mid', {'t':t})
                self.runOnThread('R1', 'mid', {'t':t})
                legs = ['L1','R1']

            if self.numLegs > 4:
                self.runOnThread('L2', 'mid', {'t':t})
                self.runOnThread('R2', 'mid', {'t':t})
                legs = ['L2','R2']

            # Wait for all legs to stop
            self.joinThreads(legs)       

            # If request was made to end walk, break out of loop
            if self.stopped:
                break   

    def eat(self):
        '''Eat'''
        self.log.info("eat")

        self.stopped = False
        t = 1

        while True:

            # Get settings for the leg
            settings = self.settings["leg_ranges"][0]

            jitter = 20 # !! param

            # Set left leg position, with jitter.  Hip to the front, knee to mid.
            angles = (settings["left"]["hip"][LEG_FRONT]+random.randint(-jitter,jitter), settings["left"]["knee"][LEG_MID]+random.randint(-jitter,jitter))
            self.runOnThread('L0', 'setAngles', {'angles':angles,'t':t})
            
            # Set right leg position, with jitter.  Hip to the front, knee to mid.
            angles = (settings["right"]["hip"][LEG_FRONT]+random.randint(-jitter,jitter), settings["right"]["knee"][LEG_MID]+random.randint(-jitter,jitter))
            self.runOnThread('R0', 'setAngles', {'angles':angles,'t':t})

            legs = ['L0','R0']

            if self.numLegs > 2:
                self.runOnThread('L1', 'mid', {'t':t})
                self.runOnThread('R1', 'mid', {'t':t})
                legs = ['L1','R1']

            if self.numLegs > 4:
                self.runOnThread('L2', 'mid', {'t':t})
                self.runOnThread('R2', 'mid', {'t':t})
                legs = ['L2','R2']

            # Wait for all legs to stop
            self.joinThreads(legs)                 

            # If request was made to end walk, break out of loop
            if self.stopped:
                break               

    def wakeSlowly(self, t=5):
        '''Move all legs slowly to their mid position.  The slow wake prevents a surge in current draw that could shut down the Pi.'''
       
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'mid', {'t':t})
            self.runOnThread(right, 'mid', {'t':t})
        self.joinThreads(threads)

    def unwind(self, t=1):
        '''Put the animal into a relaxing state (crouched down)'''
        
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'unwind', {'t':t})
            self.runOnThread(right, 'unwind', {'t':t})
        self.joinThreads(threads)


    def alert(self, t=1):
        '''Put the animal into an alert state (standing upright)'''
        
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'alert', {'t':t})
            self.runOnThread(right, 'alert', {'t':t})
        self.joinThreads(threads) 


    def sit(self, t=1):
        '''Put the animal into an sitting state'''
        
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'sit', {'t':t})
            self.runOnThread(right, 'sit', {'t':t})    
        self.joinThreads(threads)         
   

    def kneesup(self, t=1):
        '''Lift knees all the way up'''
        
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'kneeFullUp', {'t':t})
            self.runOnThread(right, 'kneeFullUp', {'t':t})            
        self.joinThreads(threads)                     
       

    def kneesdown(self, t=1):
        '''Put knees all the way down'''
        
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'kneeFullDown', {'t':t})
            self.runOnThread(right, 'kneeFullDown', {'t':t})            
        self.joinThreads(threads)    
          
    def hipsbackward(self, t=1):
        '''Push hips all the way backwards'''
        
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'hipFullBackward', {'t':t})
            self.runOnThread(right, 'hipFullBackward', {'t':t})            
        self.joinThreads(threads)                     
       

    def hipsforward(self, t=1):
        '''Push hips all the way forwards'''
        
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'hipFullForward', {'t':t})
            self.runOnThread(right, 'hipFullForward', {'t':t})            
        self.joinThreads(threads)    
          

    def detectMovement(self):
        # Put in alert state
        self.alert()

        tracking = False

        while True:
            if tracking:
                self.head.trackHotspot()
            else:
                # Detect movement
                movement = self.head.detectMovement()
                if movement is not None:
                    if movement>80: #!!param
                        self.log.info("Movement {} so start tracking".format(movement))
                        self.setTimer(10, self.timerAction) # delay the next action !!
                        tracking = True

            # If request was made to end , break out of loop
            if self.stopped:
                #self.log.info("Stopped detect movement")
                break         

            sleep(0.2)           

    def trackHotspot(self):
        # Put in alert state
        self.alert()

        while True:
            self.head.trackHotspot()
            
            # If request was made to end , break out of loop
            if self.stopped:
                #self.log.info("Stopped detect movement")
                break         

            sleep(0.2)            
         

    """
    def setAngles(self):
        '''Point forwards'''
        
        self.stopped = False

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


    def stopMovements(self):
        '''Stop the current action'''
        self.stopped = True

        # Stop all servos
        for pair in range(len(self.legPairs)):
            self.legPairs[pair].left.stop()
            self.legPairs[pair].right.stop()

        # Stop all threads
        self.stopThreads()



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
    