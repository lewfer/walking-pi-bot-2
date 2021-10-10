"""
random_animal.py

Implementation of RandomAnimal class.

A RandomAnimal is an animal that does random actions.

Actions run for a while until another action is triggered.
Another action can be triggered by a timer (e.g run forwards in 5 seconds time)
or by an interrupt (e.g. obstacle detected).

"""

# Imports
# -------------------------------------------------------------------------------------------------
from animal import *


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
        self._randomThread = None               # thread on which random action generator runs
        self._runningRandom = False             # flag to indicate that random thread is running

        self._threadCount = 0                   # so we can track threads

        # List of one-letter action codes and the associated actions
        self.actionFunction = {
            '*':'do_default()',
            'K':'do_look()',
            'F':'do_forward()', 
            'B':'do_backward()',
            'L':'do_left()',
            'R':'do_right()',
            'l':'do_backLeft()',
            'r':'do_backRight()',
            '\\':'do_leftNoCheck()',
            '/':'do_rightoCheck()',            
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
            'M':'do_detectMovement()',
            'T':'do_trackMovement()',
            'J':'do_jump()',
            'O':'do_turn()',
            'N':'do_bounce()'
            }

        self.actionName = {
            '*':'default',
            'K':'look',
            'F':'forward', 
            'B':'backward',
            'L':'left',
            'R':'right',
            'l':'backLeft',
            'r':'backRight',
            '\\':'leftNoCheck',
            '/':'rightoCheck',            
            'W':'wait',
            'U':'unwind',
            'P':'point',
            'E':'eat',
            'S':'sit',
            '^':'kneesup',
            'v':'kneesdown',
            '<':'hipsbackward',
            '>':'hipsforward',
            'A':'alert',
            '+':'run',
            '-':'crawl',
            'M':'detectMovement',
            'T':'trackMovement',
            'J':'jump',
            'O':'turn',
            'N':'bounce'
            }            


    # Settings 
    # ---------------------------------------------------------------------------------------------

    def setDefaultSettings(self):
        '''Override Animal method to set additional settings for RandomAnimal'''

        Animal.setDefaultSettings(self)   

        # Weights for random movement action choices
        #                                 ['.','S','B','L','R','U','P','E','A','+','-', 'K', 'N', 'O']
        self.settings['RANDOMWEIGHTS'] =  [ 120, 10, 1,  3,  3,  2,  0,  1,  1, 40,  1,  20,  2,  50]

        # Min/max time for action to run
        self.settings['RANDOMTIME'] = {"B": [2, 8], "L": [2, 6], "R": [2, 6], "S": [1, 3], "P": [2, 30], "E": [2, 30], "A": [2, 30], "U": [5, 50], "M": [10, 20], "T": [5, 10], "+": [20, 30], "-": [2, 10], "K": [1, 2], "N": [4, 6], "O": [10, 15]}

        # Number of seconds to wait before generating another random action
        self.settings['TICKPERIOD'] = 1

        # Number of alertness points to add for each tick when the animal is unwinding
        self.settings['UNWINDALERTNESSINCREASE'] = 5





    # Handlers for actions 
    # ---------------------------------------------------------------------------------------------

    def do_default(self):
        """Do the default action, which is to look around and take appropriate action."""

        self.log.info("Do default")

        # Get ready for scan
        self.stopCurrentAction()        # stop anything we are doing
        self.head.pauseSensors()        # don't monitor sensors

        # Do a scan (move head from side-to-side) looking for short distances
        self.log.info("\tScanning")
        minPos, minDist, maxPos, maxDist, minLeftDist, minRightDist, maxLeftDist, maxRightDist, movement, rearMovement = self.head.scan()
        #print("\tScan minpos={} maxpos={} movement={}".format(minPos, maxPos, movement))

        # Check what we saw
        if movement:
            # We saw something move, so track it for a while
            self.log.info("\tSaw a movement")
            self.do_trackMovement()
            self._setTimer(self._randint(self.settings['RANDOMTIME']['T']), 'F')   

        #elif rearMovement:
        #    self.log.info("\tSaw a rear movement")
        #    self.do_turn()
        #    self._setTimer(16, 'K') #!!turn time
            
        elif minDist < self.settings['SHORTDISTANCE'] : 
            # We saw an obstacle close by

            # We are now in escape mode
            self._interruptId = "escape"
            self._interruptValue = 0

            # We are too close to something.  Check if something is left or right.  
            obstacleLeft = minLeftDist < self.settings['SHORTDISTANCE']         # something on left?
            obstacleRight = minRightDist < self.settings['SHORTDISTANCE']       # something on right?
            shortestLeft = minPos < 0                                           # shortest distance is on left?
            shortestRight = minPos > 0                                          # shortest distance is on right?
            longestLeft = maxPos < 0                                            # longest distance is on left?
            longestRight = maxPos > 0                                           # longest distance is on right?

            # Depending on where obstacle is take action
            if obstacleLeft and obstacleRight:
                # Something on left and right, so back out so we point in the direction where there is most space
                if longestRight: 
                    self.log.info("\tObstacle on left and right, more space right, so back out left")
                    self.do_backLeft()
                elif longestLeft:
                    self.log.info("\tObstacle on left and right, more space left, so back out right")
                    self.do_backRight()
                else:
                    self.log.info("\tObstacle on left and right, more space straight, so default to back out right")
                    self.do_backRight()
            elif shortestLeft:  
                self.log.info("\tObstacle on left, so veer right")
                self.do_rightNoCheck()
            elif shortestRight:  
                self.log.info("\tObstacle in right, so veer left")
                self.do_leftNoCheck()
            else:
                self.log.info("\tObstacle straight ahead, so back out")
                self.do_backward()

            # Whatever we decided to do, return to going forward eventually
            self._setTimer(30, 'F')                   #  !!
        else:
            # We are not too close to anything
            self.log.info("\tNo issues seen, so move F")
            self.do_forward()

    def do_look(self):
        """Take a look around"""

        self.log.info("Do look")

        self._timerAction = None

        # Get ready for scan
        self.stopCurrentAction()        # stop anything we are doing
        self.head.pauseSensors()        # don't monitor sensors

        # Do a scan (move head from side-to-side) looking for short distances
        self.log.info("Looking")
        movement, rearMovement = self.head.look()
        #print("\tScan minpos={} maxpos={} movement={}".format(minPos, maxPos, movement))

        # Check what we saw
        if movement:
            # We saw something move, so track it for a while
            self.log.info("\tSaw a movement")
            self.cry()
            self.do_trackMovement()
            self._setTimer(self._randint(self.settings['RANDOMTIME']['T']), 'F')   

        elif rearMovement:
            self.log.info("\tSaw a rear movement")  
            self.do_turn()            
            self._setTimer(16, 'K') #!!turn time

        else:
            # Carry on
            self.log.info("\tNo issues seen, so move F")
            self.do_forward()   


    def do_forward(self):
        '''Forwards is often called after an interrupt, so we also restart the sensors and clear any interrupt'''
        self.head.move(0, t=1)                  # point head forwards
        self.head.unPauseSensors()              # turn sensors back on 
        self._clearInterrupt()                  # clear out any interrupt
        self.stopCry()
        self._handleAction(self._forward, "F")

    def do_backward(self):
        self.head.move(0, t=1)                  # point head forwards
        self._handleAction(self._backward, "B")

    def do_backLeft(self):
        self.head.move(0, t=1)                  # point head forwards
        self._handleAction(self._backLeft, "l")

    def do_backRight(self):
        self.head.move(0, t=1)                  # point head forwards
        self._handleAction(self._backRight, "r")

    def clear_left(self):
        """Check if all clear on the left"""
        self.log.info("\tCheck for obstacles on left")
        self.head.pauseSensors()   # pause sensors while we scan
        minPos, minDist, maxPos, maxDist = self.head.scanLeft()
        self.log.info("\tminpos={} maxpos={}".format(minPos, maxPos))
        clear = minDist > self.settings['SHORTDISTANCE']
        self.head.unPauseSensors()   # turn sensors back on 
        return clear

    def clear_right(self):
        """Check if all clear on the right"""
        self.log.info("\tCheck for obstacles on right")
        self.head.pauseSensors()   # pause sensors while we scan
        minPos, minDist, maxPos, maxDist = self.head.scanRight()
        self.log.info("\tminpos={} maxpos={}".format(minPos, maxPos))
        clear = minDist > self.settings['SHORTDISTANCE']
        self.head.unPauseSensors()   # turn sensors back on 
        return clear

    def do_left(self):
        # Stop movements ready for scan
        self.stopCurrentAction()
        
        # Check if we can move left
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
        '''Move left without checking for obstacles'''
        #print("Do left")
        self._handleAction(self._left, "L")
        
    def do_right(self):
        # Stop movements ready for scan
        self.stopCurrentAction()

        # Check if we can move right
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
        '''Move right without checking for obstacles'''
        #print("Do right")
        self._handleAction(self._right, "R")         

    def do_wait(self):
        self._handleAction(None, "W")

    def do_unwind(self):
        self._setTimer(self._timerDelay, 'J')   
        self._handleAction(self._unwind, "U")

    def do_bounce(self): 
        self._handleAction(self._bounce, "N")

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

    def do_turn(self):
        self._handleAction(self._turn, "O")

    def do_jump(self):
        self._handleAction(self._jump, "J")
        self._setTimer(5, 'F') 


    def do_checkEscape(self):
        '''Check if we have escaped from obstacles' by looking for a good distance ahead'''
        dist = self.head.distanceSensor.readMedianCm(3)
        if dist > self.settings['SHORTDISTANCE'] * 2:
            # We have escaped
            self._setTimer(0, self._timerAction) # Start immediately
            print("Escaped", dist)
            #self.stopCry()
        else:
            #print("Still stuck", dist, "cm")
            #self.cry()
            pass

    def do_checkEscapeLeftAntenna(self):
        '''Check if we have escaped from a stuck left antenna'''
        if self.leftAntenna.is_pressed:
            #print("Still stuck")
            #self.cry()
            pass
        else:
            # We have escaped
            self._setTimer(0, self._timerAction) # Start immediately
            print("Escaped")
            #self.stopCry()
            pass

    def do_checkEscapeRightAntenna(self):
        '''Check if we have escaped from a stuck right antenna'''
        if self.rightAntenna.is_pressed:
            #print("Still stuck")
            #self.cry()
            pass
        else:
            # We have escaped
            self._setTimer(0, self._timerAction) # Start immediately
            print("Escaped")
            #self.stopCry()
            pass


    # Action management
    # ---------------------------------------------------------------------------------------------

    def start(self):
        """Start the robot in random mode"""
        self.do_forward()
        self.head.startSensors()
        self._startRandom()
        
        self.stopCry()


    def stop(self):
        """Stop the robot random mode"""
        #self.showMessage("Stopping","")
        self.log.info("Stopping")
        self._handleAction(None, "W")
        self.head.stopSensors()
        self._runningRandom = False
        

    def _handleAction(self, func, msg):  
        """Stop any current action and start a new one"""

        #if not self._stopped:
        self.runAction(func)
        self._currentAction = msg

    def _setTimer(self, delay, action):
        """Set a new timer to run action after delay seconds """
        self.log.debug("_setTimer {} {}".format(delay, action))
        self._timerAgeStart = self.age      # record age when we set the timer
        self._timerDelay = delay            # how long to wait
        self._timerAction = action          # the action to carry out when timer comes of age

    def _executeTimer(self):
        """Execute the current timer"""
        self.log.info("_executeTimer {}".format(self._timerAction))
        action = self._timerAction
        self._timerAction = None                    # remove timer
        self._timerDelay = 0
        self._timerAgeStart = 0
        exec("self."+self.actionFunction[action])   # run the action

    def _startRandom(self):
        """Start a random behaviour generator"""
        self._randomThread = Thread(target=self._runRandom)
        self._randomThread.start() 

    def _runRandom(self):
        """Continue to run random actions until stopped"""
        self._runningRandom = True
        while self._runningRandom:
            #print(".")

            # Timers take first priority
            if self._timerAction is not None:
                if self.age-self._timerAgeStart >= self._timerDelay:
                    # There is a timer that has come of age, so execute it
                    self._executeTimer()
                    continue

            # Now handle other situations in priority order
            if self._interruptId=="escape":
                # We are currently trying to escape, so check if we can
                self.do_checkEscape()

            elif self._interruptId=="escape-left-antenna":
                # We are currently trying to escape, so check if we can
                self.do_checkEscapeLeftAntenna()

            elif self._interruptId=="escape-right-antenna":
                # We are currently trying to escape, so check if we can
                self.do_checkEscapeRightAntenna()

            elif self._interruptId is not None:
                # There was an interrupt that needs to be handled
                self._handleInterrupt()

            elif self._currentAction=="T":
                # Tracking movement, so let's finish that before we allow another random movement
                pass

            elif self._currentAction=="F" and self.age % 5 == 0: # every 5 seconds
                # No timer, so allow another random, weighted choice
                # . means no change to current action
                actions = ['.','S','B','L','R','U','P','E','A','+','-','K','N','O']
                #actions = ['.','.','.','.','.','.','.','.','.','.','.','K'] #!!
                weights = self.settings['RANDOMWEIGHTS']
                choice = random.choices(actions, weights)[0]
                self.log.info("random {}".format(choice))

                # Don't allow run if not enough space
                if choice=='+':
                    if self.head.lastDistance is None or self.head.lastDistance<self.settings['RUNSPACENEEDED']:
                        self.log.info("Not enough distance to run")
                        choice = '.'

                # Start the choice, and set a timer to run default behaviour again after a random period
                if choice != '.':
                    self.log.info("Initiating action {}".format(choice))
                    exec("self."+self.actionFunction[choice])

                    if choice in ['S','U']:
                        self._setTimer(self._randint(self.settings['RANDOMTIME'][choice]), 'J')                   
                    elif choice != 'K':
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
            actionName = "none" if self._timerAction is None else self.actionName[self._timerAction]
            if self._timerDelay == 0:
                timerMsg = "{}_when_done".format(actionName)
            else:
                timerMsg = "{}_in_{}s (of {}s)".format(actionName, self._timerDelay-(self.age-self._timerAgeStart), self._timerDelay)

            # age={} alertness={} energy={}  human={} self.age, self.alertness, self.energy, , self.lastHumanDetectAge
            self.log.info("\t{} next={} int={} threads={} dist={} temp={},{}".format(
                self.actionName[self._currentAction], 
                timerMsg,
                self._interruptId, 
                activeCount(),
                self.head.lastDistance, self.head.lastMinTemperature,self.head.lastMaxTemperature,
                ))

            if self.messageCallback is not None:   
                # Send message to programmer LCD
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
        '''Something caused an interrupt'''

        # Don't allow interrupt to be interrupted
        if self._interruptId is not None:
            return

        # Ignore human-detect (heat sensing didn't work!)
        if id=="human-detect":
            #print("Ignoring heat detect")
            self.head.unPauseSensors()  
            return

        # Ignore human-detect (heat sensing didn't work!)
        if id=="human-detect" and self.age-self.lastHumanDetectAge < 60:
            print("Bored of humans")  
            self.head.unPauseSensors()  
            return

        self.log.info("Interrupt {}".format(id))            

        # Set the interrupt so it will be handled on the next loop in _runRandom()
        self._interruptId = id
        self._interruptValue = value


    def _handleInterrupt(self):
        '''There is an interrupt that needs to be handled'''

        # Handle the interrupt if no other interrupt currently being handled
        #print("Handle interrupt", self._stopped)
        if not self._interruptBeingHandled and not self._stopped:
            self.log.info("Handle Interrupt {}".format(self._interruptId))
            self._interruptBeingHandled = True

            if self._interruptId=="short-distance":
                self.do_default()                           # do a scan and decide what to do

            elif self._interruptId=="left-antenna":
                self.do_rightNoCheck()                      # move off right
                self._interruptId = "escape-left-antenna"   # keep checking antenna
                self._setTimer(30, 'F')                     # move F after a delay if still stuck

            elif self._interruptId=="right-antenna":
                self.do_leftNoCheck()                       # move off left
                self._interruptId = "escape-right-antenna"  # keep checking antenna
                self._setTimer(30, 'F')                     # move F after a delay if still stuck

            elif self._interruptId=="human-detect":
                # Not used
                self.lastHumanDetectAge = self.age
                self.do_trackMovement()
                self._setTimer(self._randint(self.settings['RANDOMTIME']['T']), 'F')   

            elif self._interruptId=="long-distance":
                # Not used
                self._clearInterrupt()
                self.head.unPauseSensors()  


    def _clearInterrupt(self):
        '''Clear any interrupt'''
        self._interruptId = None
        self._interruptBeingHandled = False          

    def _randint(self, minmax):
        '''Generate random int based on minmax list'''
        return random.randint(minmax[0],minmax[1])


if __name__ == "__main__":
    print("Testing RandomAnimal")    


    # Create animal
    animal = RandomAnimal()

    #animal.log.setLevel(logging.DEBUG)

    # With 2 legs           
    animal.addPairOfLegs(Leg(Joint(0), Joint(1), 1), Leg(Joint(2), Joint(3), -1))

    # With 4 legs           
    animal.addPairOfLegs(Leg(Joint(4), Joint(5), 1), Leg(Joint(6), Joint(7), -1))

    # Load settings from json file
    animal.loadSettings()

    print("wakeSlowly(2)")
    animal.wakeSlowly(5) 

    # Run the animal in random mode
    print("Running animal")
    animal.start()
    while True:
        sleep(0.2)
    
