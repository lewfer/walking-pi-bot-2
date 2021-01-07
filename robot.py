"""
robot.py

Code for a crawling robot.

Combines the functionality of Crawler and Programmer to provide a crawling robot with the ability to control it using a programmer.
The robot will start its default behaviour (call to start()) but can be stopped and programmed.
"""

# Imports
# -------------------------------------------------------------------------------------------------
from crawler import *
from head import Head
from programmer import *
from time import sleep
from gpiozero import Button
from random import randint

class Robot(Programmer):

    def __init__(self, menu):
        Programmer.__init__(self, menu)   

        # Create an animal with 2 legs
        self.crawler = Crawler()

        self.head = Head(self.interrupt)

        # Antennae
        self.leftAntenna = Button(6)
        self.rightAntenna = Button(12)
        self.antennaeThread = None
        self.leftAntenna.when_pressed = self.leftAntennaPressed
        self.rightAntenna.when_pressed = self.rightAntennaPressed

        # Adjust parameter between 0.5 (fast) and 6 (slow) to change speed of movement
        self.crawler.setStepsPerDegree(self.crawler.settings['STEPSPERDEGREE'])

        # Manage current and next action
        self.currentAction = None       # current action being run (one-letter code)
        self.actionThread = None        # thread on which current action is running
        self.timerDelay = 0             # delay before next action runs
        self.timerAction = None         # action to run next (one-letter code)
        self.timerAgeStart = 0          # age of robot when timer was started
        self.interruptId = None         # the current interrupt, if any
        self.interruptBeingHandled = None   # if we are currently executing the interrupt handling action

        # Random action generator
        self.randomThread = None        # thread on which random action generator runs
        self.runningRandom = False      # flag to indicate that random thread is running

        # Robot health
        # Can use these to determine behaviour, e.g. slowing down as energy drops
        self.alertness = 120
        self.energy = 1000
        self.age = 0

        # List of one-letter action codes and the associated actions
        self.actionFunction = {
            'F':'self.forward()', 
            'B':'self.backward()',
            'L':'self.left()',
            'R':'self.right()',
            'W':'self.wait()',
            'U':'self.unwind()',
            'P':'self.point()',
            'E':'self.eat()',
            'S':'self.sit()',
            '^':'self.high()',
            'v':'self.low()',
            'A':'self.alert()',
            'I':'self.endInterrupt()',
            'M':'self.detectMovement()',
            'T':'self.trackMovement()'
            }

    # Handlers for actions 
    # ---------------------------------------------------------------------------------------------

    def endInterrupt(self):
        self.interruptId = None
        self.interruptBeingHandled = False
        self.forward()

    def forward(self):
        self.handleAction(self.crawler.forwardTurtle, "F")
        self.head.unPauseSensors()   # turn sensors back on for moving forwards

    def backward(self):
        self.handleAction(self.crawler.backwardTurtle, "B")

    def left(self):
        self.handleAction(self.crawler.leftTurtle, "L")

    def right(self):
        self.handleAction(self.crawler.rightTurtle, "R")

    def wait(self):
        self.handleAction(None, "W")

    def unwind(self):
        self.handleAction(self.crawler.unwind, "U")

    def point(self):
        self.handleAction(self.crawler.point, "P")

    def eat(self):
        self.handleAction(self.crawler.eat, "E")

    def sit(self):
        self.handleAction(self.crawler.sit, "S")

    def high(self):
        self.handleAction(self.crawler.high, "^")

    def low(self):
        self.handleAction(self.crawler.low, "v")

    def alert(self):
        self.handleAction(self.crawler.alert, "A")

    def detectMovement(self):
        self.handleAction(self.detectMovementDo, "M")

    def trackMovement(self):
        self.handleAction(self.trackMovementDo, "T")

    def handleAction(self, func, msg):  
        """Stop any current action and start a new one"""
        self.crawler.stop()
        if self.actionThread: self.actionThread.join()
        print(msg)
        if func is not None:
            self.actionThread = Thread(target=func)
            self.actionThread.start()   
        self.currentAction = msg


    def detectMovementDo(self):
        # Put in alert state
        self.crawler.alert()

        tracking = False

        while True:
            if tracking:
                self.head.trackMovement()
            else:
                # Detect movement
                movement = self.head.detectMovement()
                if movement>80: #!!param
                    print("Movement",movement,"so start tracking")
                    self.setTimer(10, self.timerAction) # delay the next action
                    tracking = True

            # If request was made to end , break out of loop
            if self.crawler.stopped:
                #self.log.info("Stopped detect movement")
                break         

            sleep(0.2)           
         




    # Action management
    # ---------------------------------------------------------------------------------------------

    def setTimer(self, delay, action):
        """Cancel any existing timer and replace with this one.  Timers are used to """
        #if self.timer is not None:
        #    self.timer.cancel()
        self.timerAgeStart = self.age
        #self.timer = Timer(delay, self.actionFunction[action])
        #self.timer.start()
        self.timerDelay = delay
        self.timerAction = action

    def executeTimer(self):
        #!!surely need to stop previous action?
        exec(self.actionFunction[self.timerAction])
        self.timerAction = None
        self.timerDelay = 0
        self.timerAgeStart = 0

    def start(self):
        """Start the robot"""
        self.forward()
        self.head.startSensors()
        self.startRandom()

    def stop(self):
        """Stop the robot"""
        self.showMessage("Stopping","")
        self.handleAction(None, "W")
        self.head.stopSensors()
        self.runningRandom = False

    def startRandom(self):
        """Start a random behaviour interrupt generator"""
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
                actions = ['F','S','B','L','R','U','P','E','A']
                weights = [ 40, 10, 1,  3,  3,  2,  2,  1,  1] # !! weights parameters
                #weights = [20,0,0,0,0] # !! weights
                choice = random.choices(actions, weights)[0]
                print("random",choice, "-", end="")

                # Start the choice, and set a timer to start moving forward again after a random period
                #self.handleInterrupt("random", 0)
                if choice in ['L','R']:
                    # These actions can run for a short period
                    exec(self.actionFunction[choice])
                    self.setTimer(random.randint(2, 15), 'F') #!! rest min/max parameters
                elif choice in ['S','P','E','A']:
                    # These actions can run for a medium period
                    exec(self.actionFunction[choice])
                    self.setTimer(random.randint(2, 30), 'F') #!! rest min/max parameters
                elif choice=='U' and self.alertness < 100:
                    # These actions can run for a long period
                    self.unwind()
                    self.setTimer(random.randint(3, 50), 'F') #!! rest min/max parameters

            sleep(1)

            # Adjust alertness
            if self.currentAction=='U':
                self.alertness += 5
            else:
                self.alertness -= 1

            # djust age
            self.age += 1

            self._printStatus()

    def _printStatus(self):
        """Print out the status for debugging"""
        print("{} alertness={} energy={} timernext={}_in_{}s threadcount={}".format(self.currentAction, self.alertness, self.energy, self.timerAction, self.timerDelay, activeCount()))
        if self.interruptId is None:
            self.showMessage(self.actionFunction[self.currentAction],self.actionFunction[self.timerAction] if self.timerAction is not None else "")
        else:
            self.showMessage("Interrupt",self.interruptId)


    # Interrupt handling
    # ---------------------------------------------------------------------------------------------
    def interrupt(self, id):

        # Don't allow interrupt to be interrupted
        if self.interruptId is not None:
            return

        print("Interrupt",id)            

        self.interruptId = id

    def handleInterrupt(self):
        # Handle the interrupt
        if not self.interruptBeingHandled:
            print("Handle Interrupt")
            self.interruptBeingHandled = True
            if self.interruptId=="short-distance":
                self.backward()
                self.setTimer(10, 'I') # !!turn time

            elif self.interruptId=="left-antenna":
                self.right()
                self.setTimer(10, 'I') # !!turn time

            elif self.interruptId=="right-antenna":
                self.left()
                self.setTimer(10, 'I') # !!turn time

            elif self.interruptId=="heat":
                self.detectMovement()
                self.setTimer(10, 'I') # !!turn time 


    # Sensors
    # ---------------------------------------------------------------------------------------------

    def leftAntennaPressed(self):
        self.interrupt("left-antenna")

    def rightAntennaPressed(self):
            self.interrupt("right-antenna")



    """
    def waitForStop(self):  
        self.showMessage("Stopping","")
        self.crawler.stop()
        if self.actionThread: self.actionThread.join()"""

    # Calibration
    # ---------------------------------------------------------------------------------------------

    def calibrateLeftHip(self):
        print("Calibrate left hip mid position")
        legPair = 0
        self.calibrateJointMid(self.crawler.legPairs[legPair].left.hip, self.crawler.settings["leg_ranges"][legPair]["left"]["hip"], "L hip")

    def calibrateLeftKnee(self):
        print("Calibrate left knee position")
        legPair = 0
        self.calibrateJointMid(self.crawler.legPairs[legPair].left.knee, self.crawler.settings["leg_ranges"][legPair]["left"]["knee"], "L knee")

    def calibrateRightHip(self):
        print("Calibrate right hip position")
        legPair = 0
        self.calibrateJointMid(self.crawler.legPairs[legPair].right.hip, self.crawler.settings["leg_ranges"][legPair]["right"]["hip"], "R hip")

    def calibrateRightKnee(self):
        print("Calibrate right knee position")        
        legPair = 0
        self.calibrateJointMid(self.crawler.legPairs[legPair].right.knee, self.crawler.settings["leg_ranges"][legPair]["right"]["knee"], "R knee")

    def calibrateHipsFront(self):
        print("Calibrate hips front position")
        legPair = 0
        self.calibrateHips(LEG_FRONT, legPair, "Hips front")

    def calibrateHipsBack(self):
        print("Calibrate hips back position")
        legPair = 0
        self.calibrateHips(LEG_BACK, legPair, "Hips back")   

    def calibrateKneesUp(self):
        print("Calibrate knees up position")
        legPair = 0
        self.calibrateKnees(LEG_UP, legPair, "Knees up")   

    def calibrateKneesDown(self):
        print("Calibrate knees down position")
        legPair = 0
        self.calibrateKnees(LEG_DOWN, legPair, "Knees down") 

    def calibrateHips(self, pos, legPair, name):
        """Calibrate hips to front or back"""

        options = ["return","save",".","to mid","reset"]
        self.showOptions(options)

        # Move joints to current position being calibrated
        left = self.crawler.legPairs[legPair].left
        right = self.crawler.legPairs[legPair].right
        left.setHipPos(pos)
        right.setHipPos(pos)

        # Start reading the knob
        self.knob.run(self.calibrateKnobAdjustments)
        self.rotaryAction = 0

        # Remember where we started (in case user wants to reset)
        originalLeftAngle = left.hip._angle
        originalRightAngle = right.hip._angle

        # Start calibrating
        counter = 0
        while True: 
            # Add angle and show options
            if counter%8==0:
                msg = "Adj " + name
            else:
                msg = "{:>6} {:3}".format(left.hip._angle, right.hip._angle)
            self.lcd.lcd_display_string_pos(msg, 1, 6)

            # Get option selected
            optionName = self.getSelectedOption(options)     
            #print(optionName)

            # Nudge joint
            if self.rotaryAction!=0:
                print(self.rotaryAction)
                left.nudgeHip(self.rotaryAction)
                right.nudgeHip(self.rotaryAction)
            elif optionName=="save":
                self.crawler.settings["leg_ranges"][legPair]["left"]["hip"][pos] = int(left.hip._angle)
                self.crawler.settings["leg_ranges"][legPair]["right"]["hip"][pos] = int(right.hip._angle)
                self.crawler.storeSettings()     
                self.showMessage("Saved",name)
                sleep(2)                
                break
            elif optionName=="to mid":
                print("to mid")
                left.setHipPos(LEG_MID)
                right.setHipPos(LEG_MID)     
            elif optionName=="reset":
                left.setHipPos(pos)
                right.setHipPos(pos)       
            elif optionName=="return":
                break         
            self.rotaryAction = 0
            counter+=1
            sleep(0.5)
            
        self.knob.stop()        

    def calibrateKnees(self, pos, legPair, name):
        """Calibrate hips to up or down"""

        options = ["return","save",".","to mid","reset"]
        self.showOptions(options)

        # Move joints to current position being calibrated
        left = self.crawler.legPairs[legPair].left
        right = self.crawler.legPairs[legPair].right
        left.setKneePos(pos)
        right.setKneePos(pos)

        # Start reading the knob
        self.knob.run(self.calibrateKnobAdjustments)
        self.rotaryAction = 0

        # Remember where we started (in case user wants to reset)
        originalLeftAngle = left.knee._angle
        originalRightAngle = right.knee._angle

        # Start calibrating
        counter = 0
        while True: 
            # Add angle and show options
            if counter%8==0:
                msg = "Adj " + name
            else:
                msg = "{:>6} {:3}".format(left.knee._angle, right.knee._angle)
            self.lcd.lcd_display_string_pos(msg, 1, 6)

            # Get option selected
            optionName = self.getSelectedOption(options)     
            #print(optionName)

            # Nudge joint
            if self.rotaryAction!=0:
                print(self.rotaryAction)
                left.nudgeKnee(self.rotaryAction)
                right.nudgeKnee(self.rotaryAction)
            elif optionName=="save":
                self.crawler.settings["leg_ranges"][legPair]["left"]["knee"][pos] = int(left.knee._angle)
                self.crawler.settings["leg_ranges"][legPair]["right"]["knee"][pos] = int(right.knee._angle)
                self.crawler.storeSettings()     
                self.showMessage("Saved",name)
                sleep(2)                
                break
            elif optionName=="to mid":
                print("to mid")
                left.setKneePos(LEG_MID)
                right.setKneePos(LEG_MID)     
            elif optionName=="reset":
                left.setKneePos(pos)
                right.setKneePos(pos)       
            elif optionName=="return":
                break         
            self.rotaryAction = 0
            counter+=1
            sleep(0.5)
            
        self.knob.stop()        


    def calibrateJointMid(self, joint, setting, name):
        '''Calibrate a single joint's mid position'''

        # Set up options
        options = ["return","save",".","to 90","reset"]
        self.showOptions(options)

        # Move joint to mid position
        joint.moveDirectToMid()

        # Start reading the knob
        self.knob.run(self.calibrateKnobAdjustments)
        self.rotaryAction = 0

        # Remember where we started (in case user wants to reset)
        originalAngle = joint._angle

        # Start calibrating
        counter = 0
        while True: 
            # Add angle and show options
            if counter%8==0:
                msg = "Adj " + name
            else:
                msg = "{:>10}".format(joint._angle)
            self.lcd.lcd_display_string_pos(msg, 1, 6)

            # Get option selected
            optionName = self.getSelectedOption(options)     
            #print(optionName)

            # Nudge joint
            if self.rotaryAction!=0:
                print(self.rotaryAction)
                joint.nudge(self.rotaryAction)
            elif optionName=="save":
                setting[LEG_MID] = int(joint._angle)
                self.crawler.storeSettings()     
                self.showMessage("Saved",name)
                sleep(2)                
                break
            elif optionName=="to 90":
                joint.moveDirectTo(90)        
            elif optionName=="reset":
                joint.moveDirectTo(originalAngle) 
            elif optionName=="return":
                break         
            self.rotaryAction = 0
            counter+=1
            sleep(0.5)
            
        self.knob.stop()

    def calibrateKnobAdjustments(self, action):
        # Callback for knob turns to be registered
        #print("action", action)
        self.rotaryAction += action

    def set90Degrees(self):
        '''Set all motors to 90 degrees'''
        self.showMessage("Setting to 90","degrees")
        sleep(1)
        self.crawler.legPairs[0].left.knee.moveDirectTo(90)
        self.crawler.legPairs[0].left.hip.moveDirectTo(90)
        self.crawler.legPairs[0].right.knee.moveDirectTo(90)
        self.crawler.legPairs[0].right.hip.moveDirectTo(90)

    def factoryReset(self):
        if self.yesNo("Factory Reset?"):
            self.crawler.factoryReset()
            self.showMessage("Settings reset","")
            sleep(2)     


    # Testing
    # ---------------------------------------------------------------------------------------------

    def testDistanceSensor(self):
        options = ["return",".",".",".","."]
        self.showOptions(options)
        self.showMessage("DistanceSensor", None)
        while True:
            self.showMessage(None, str(self.head.distanceSensor.readCm()))
            optionName = self.getSelectedOption(options)
            if optionName=="return":
                break   

    def testAntennae(self):
        options = ["return",".",".",".","."]
        self.showOptions(options)
        self.showMessage("Antennae", None)
        while True:
            msg = "{} - {}".format(self.leftAntenna.is_pressed, self.rightAntenna.is_pressed)
            self.showMessage(None, msg)
            optionName = self.getSelectedOption(options)
            if optionName=="return":
                break           

    def testThermalSensor(self):
        options = ["return",".",".",".","."]
        self.showOptions(options)
        self.showMessage("ThermalSensor", None)
        while True:
            matrix = self.head.thermalSensor.readMatrix()
            min,max,mean,rowmeans,colmeans,hotspot = self.head.thermalSensor.summarise()
            print(round(min,1),round(max,1),round(mean,1),hotspot)
            msg = "{:.0f} {:.0f} {:.0f} {}".format(min,max,mean,hotspot[1])
            self.showMessage(None, msg)
            optionName = self.getSelectedOption(options)
            if optionName=="return":
                break               

    def testHeadMovements(self):
        """Move between left, mid, right"""
        options = ["return",".",".",".","."]
        self.showOptions(options)
        self.showMessage("Head move", None)
        position = -100
        while True:
            # Move head
            #position = randint(-100,100)
            self.showMessage(None, str(position))
            self.head.move(position)
            sleep(2)
            position += 100
            if position==200: position=-100

            optionName = self.getSelectedOption(options)
            if optionName=="return":
                break           

    def testTrackMovements(self):
        """Follow heat with head"""
        options = ["return",".",".",".","."]
        self.showOptions(options)
        self.showMessage("Head follow heat", None)
        position = -100
        while True:
            self.showMessage(None, str(position))
            self.head.trackMovement()

            optionName = self.getSelectedOption(options)
            if optionName=="return":
                break          

        

    def test(self, action):
        """Test an action"""

        # Show test action menu
        options = ["return",".",".",".","done"]
        self.showOptions(options)

        # Start the action off
        exec(self.actionFunction[action])

        # Wait for return or done to be pressed
        while True:
            self.showOptions(options, self.actionFunction[action])
            optionName = self.getSelectedOption(options)
            if optionName=="return" or optionName=="done":
                break
            sleep(0.2)

        # Wait for action to complete before returning
        self.wait()


# Main program
# -------------------------------------------------------------------------------------------------

# Items ending in . don't show arrows
menu = {
            "main" : ["stop", "menu", ".", ".", "start"],

            "main/stop" : "stop()",
            "main/start" : "start()",

            "main/menu":["return", "calibrate", "90d", "test", "freset"],
            
            "main/menu/calibrate": ["return", "defs", "hips", "knees", "."],

            "main/menu/calibrate/defs": ["return", "Lknee", "Rknee", "Lhip", "Rhip"],
            "main/menu/calibrate/defs/Lknee": "calibrateLeftKnee()",
            "main/menu/calibrate/defs/Lhip": "calibrateLeftHip()",
            "main/menu/calibrate/defs/Rknee": "calibrateRightKnee()",
            "main/menu/calibrate/defs/Rhip": "calibrateRightHip()",

            "main/menu/calibrate/hips": ["return", "front", ".", "back", "."],
            "main/menu/calibrate/knees": ["return", "up", ".", "down", "."],

            "main/menu/calibrate/hips/front": "calibrateHipsFront()",
            "main/menu/calibrate/hips/back": "calibrateHipsBack()",
            "main/menu/calibrate/knees/up": "calibrateKneesUp()",
            "main/menu/calibrate/knees/down": "calibrateKneesDown()",

            "main/menu/90d": "set90Degrees()",

            "main/menu/test": ["return", "moves1", "moves2", "sensors", "head"],
            "main/menu/test/moves1": ["return", "forward", "backward", "left", "right"],
            "main/menu/test/moves2": ["return", "unwind", "point", "eat", "sit"],
            "main/menu/test/sensors": ["return", "dist", "antennae", "thermal", "."],
            "main/menu/test/head": ["return","move","heat",".","."],


            "main/menu/test/moves1/forward": "test('F')",
            "main/menu/test/moves1/backward": "test('B')",
            "main/menu/test/moves1/left": "test('L')",
            "main/menu/test/moves1/right": "test('R')",
            
            "main/menu/test/moves2/unwind": "test('U')",
            "main/menu/test/moves2/point": "test('P')",
            "main/menu/test/moves2/eat": "test('E')",
            "main/menu/test/moves2/sit": "test('S')",

            "main/menu/test/sensors/dist": "testDistanceSensor()",
            "main/menu/test/sensors/thermal": "testThermalSensor()",
            "main/menu/test/sensors/antennae": "testAntennae()",

            "main/menu/test/head/move": "testHeadMovements()",
            "main/menu/test/head/heat": "testTrackMovements()",


            "main/menu/freset" : "factoryReset()"
        }

robot = Robot(menu)
#robot.start()
robot.runMenu("main")


