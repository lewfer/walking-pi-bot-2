"""
robot.py

Code for a crawling robot.

Combines the functionality of Turtle and Programmer to provide a crawling robot with the ability to control it using a programmer.
The robot will start its default behaviour (call to start()) but can be stopped and programmed.
"""

# Imports
# -------------------------------------------------------------------------------------------------
from turtle import *
from programmer import *

class Robot(Programmer):

    def __init__(self, menu):
        Programmer.__init__(self, menu)   

        # Create an animal with 2 legs
        self.animal = Turtle()

        # Adjust parameter between 0.5 (fast) and 6 (slow) to change speed of movement
        self.animal.setStepsPerDegree(self.animal.settings['STEPSPERDEGREE'])

        self.animal.messageCallback = self.messageCallback


    def messageCallback(self, line1, line2):
        """Receives messages from the animal"""
        self.showMessage(line1, line2)


    # Calibration
    # ---------------------------------------------------------------------------------------------

    def calibrateLeftHip(self):
        print("Calibrate left hip mid position")
        legPair = 0
        self.calibrateJointMid(self.animal.legPairs[legPair].left.hip, self.animal.settings["leg_ranges"][legPair]["left"]["hip"], "L hip")

    def calibrateLeftKnee(self):
        print("Calibrate left knee position")
        legPair = 0
        self.calibrateJointMid(self.animal.legPairs[legPair].left.knee, self.animal.settings["leg_ranges"][legPair]["left"]["knee"], "L knee")

    def calibrateRightHip(self):
        print("Calibrate right hip position")
        legPair = 0
        self.calibrateJointMid(self.animal.legPairs[legPair].right.hip, self.animal.settings["leg_ranges"][legPair]["right"]["hip"], "R hip")

    def calibrateRightKnee(self):
        print("Calibrate right knee position")        
        legPair = 0
        self.calibrateJointMid(self.animal.legPairs[legPair].right.knee, self.animal.settings["leg_ranges"][legPair]["right"]["knee"], "R knee")

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
        left = self.animal.legPairs[legPair].left
        right = self.animal.legPairs[legPair].right
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
                self.animal.settings["leg_ranges"][legPair]["left"]["hip"][pos] = int(left.hip._angle)
                self.animal.settings["leg_ranges"][legPair]["right"]["hip"][pos] = int(right.hip._angle)
                self.animal.storeAndReapplySettings()     
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
        left = self.animal.legPairs[legPair].left
        right = self.animal.legPairs[legPair].right
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
                self.animal.settings["leg_ranges"][legPair]["left"]["knee"][pos] = int(left.knee._angle)
                self.animal.settings["leg_ranges"][legPair]["right"]["knee"][pos] = int(right.knee._angle)
                self.animal.storeAndReapplySettings()     
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
                self.animal.storeAndReapplySettings()     
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
        self.animal.legPairs[0].left.knee.moveDirectTo(90)
        self.animal.legPairs[0].left.hip.moveDirectTo(90)
        self.animal.legPairs[0].right.knee.moveDirectTo(90)
        self.animal.legPairs[0].right.hip.moveDirectTo(90)

    def factoryReset(self):
        if self.yesNo("Factory Reset?"):
            self.animal.factoryReset()
            self.showMessage("Settings reset","")
            sleep(2)     


    # Testing
    # ---------------------------------------------------------------------------------------------

    def testDistanceSensor(self):
        options = ["return",".",".",".","."]
        self.showOptions(options)
        self.showMessage("DistanceSensor", None)
        while True:
            self.showMessage(None, str(self.animal.head.distanceSensor.readCm()))
            optionName = self.getSelectedOption(options)
            if optionName=="return":
                break   

    def testAntennae(self):
        options = ["return",".",".",".","."]
        self.showOptions(options)
        self.showMessage("Antennae", None)
        while True:
            msg = "{} - {}".format(self.animal.leftAntenna.is_pressed, self.animal.rightAntenna.is_pressed)
            self.showMessage(None, msg)
            optionName = self.getSelectedOption(options)
            if optionName=="return":
                break           

    def testThermalSensor(self):
        options = ["return",".",".",".","."]
        self.showOptions(options)
        self.showMessage("ThermalSensor", None)
        while True:
            matrix = self.animal.head.thermalSensor.readMatrix()
            min,max,mean,rowmeans,colmeans,hotspot = self.animal.head.thermalSensor.summarise()
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
            self.animal.head.move(position)
            sleep(2)
            position += 100
            if position==200: position=-100

            optionName = self.getSelectedOption(options)
            if optionName=="return":
                break           

    def tesTrackHotspot(self):
        """Follow heat with head"""
        options = ["return",".",".",".","."]
        self.showOptions(options)
        self.showMessage("Head follow heat", None)
        position = -100
        while True:
            self.showMessage(None, str(position))
            self.animal.head.trackHotspot()

            optionName = self.getSelectedOption(options)
            if optionName=="return":
                break          

        

    def test(self, action):
        """Test an action"""

        # Show test action menu
        options = ["return",".",".",".","done"]
        self.showOptions(options)

        # Start the action off
        exec("self.animal."+self.animal.actionFunction[action])

        # Wait for return or done to be pressed
        while True:
            self.showOptions(options, self.animal.actionFunction[action])
            optionName = self.getSelectedOption(options)
            if optionName=="return" or optionName=="done":
                break
            sleep(0.2)

        # Wait for action to complete before returning
        self.animal.do_wait()


# Main program
# -------------------------------------------------------------------------------------------------

# Items ending in . don't show arrows
menu = {
            "main" : ["stop", "menu", ".", ".", "start"],

            "main/stop" : "animal.stop()",
            "main/start" : "animal.start()",

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
            "main/menu/test/head/heat": "testHotspot()",


            "main/menu/freset" : "factoryReset()"
        }

robot = Robot(menu)
#robot.start()
robot.runMenu("main")


