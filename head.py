"""
head.py

Control the head
The head can move left and right.
It also has a distance sensor and thermal sensor.
"""

from joint import Joint
from distance_tf_mini import DistanceSensor
from thermal_amg88xx import ThermalSensor
from helpers import remap
from threading import Thread
from time import sleep

class Head:

    def __init__(self, interruptCallback):
        """The interruptCallack must be provided so the caller can receive interrupts from the sensors"""

        self.interruptCallback = interruptCallback

        self.joint = Joint(4)

        # Distance sensor
        self.distanceSensor = DistanceSensor(14)
        self._distanceSensorThread = None
        self._pauseDistanceSensor = False
        self._runningDistanceSensor = False

        # Thermal sensor
        self.thermalSensor = ThermalSensor()
        self._pauseThermalSensor = False
        self._runningThermalSensor = False

        # Settings - can be overridden
        self.joint.midAngle = 90  
        self.joint.highAngle = 135   
        self.joint.lowAngle = 45        
        self.trackDelta = 10        # change in angle each iteration when tracking movement
        self.shortDistance = 10     # distance in cm to obstacle that triggers a short-distance interrupt
        self.heatDetect = 26        # temerature in C which triggers heat-detect interrupt


    def trackHotspot(self):
        """Adjust position of the head in order to centre any hot spot detected"""

        # Read the thermal sensor
        matrix = self.thermalSensor.readMatrix()
        min,max,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()

        # Get the column which is the hotest
        col = hotspot[1]


        # React depending on if hot spot is to the left or right
        if col>=5:
            self.joint.moveRelativeToCurrent(-self.trackDelta, 0)
        elif col <=2:
            self.joint.moveRelativeToCurrent(self.trackDelta, 0)

    def detectMovement(self):
        """Take a reading from the thermal sensor.  Checks against previous reading to see if there was movement.
           Returns the amount of movement (sum of absolute changes in temeperature of across the matrix)"""

        matrix = self.thermalSensor.readMatrix()
        min,max,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()
        movement = self.thermalSensor.movement()
        #print(movement)
        return movement


    def move(self, position):
        """Move head to a position from -100 (left) to +100 (right)"""
        newAngle = remap(position,-100,100,self.joint.lowAngle,self.joint.highAngle)
        #print(newAngle)
        self.joint.moveTo(newAngle, 0)


    # Sensor management
    # ---------------------------------------------------------------------------------------------
    
    def startSensors(self):
        self._pauseDistanceSensor = False
        self._pauseThermalSensor = False
        self.startDistanceSensor()
        self.startThermalSensor()

    def pauseSensors(self):
        self._pauseDistanceSensor = True
        self._pauseThermalSensor = True

    def unPauseSensors(self):
        self._pauseDistanceSensor = False
        self._pauseThermalSensor = False

    def stopSensors(self):
        self._runningDistanceSensor = False
        if self._distanceSensorThread is not None:
            self._distanceSensorThread.join()
            self._distanceSensorThread = None

        self._runningThermalSensor = False
        if self.thermalSensorThread is not None:
            self.thermalSensorThread.join()
            self.thermalSensorThread = None


    # Distance sensor
    # ---------------------------------------------------------------------------------------------
    
    def startDistanceSensor(self):
        """Start distance sensor running on a thread"""
        self._distanceSensorThread = Thread(target=self.runDistanceSensor)
        self._distanceSensorThread.start() 

    def runDistanceSensor(self):
        """Thread which constantly reads from the distance sensor and raises interrupts for significant events"""
        self._runningDistanceSensor = True
        while self._runningDistanceSensor:
            if not self._pauseDistanceSensor:
                dist = self.distanceSensor.readCm()
                #print("Dist",dist)
                if dist < self.shortDistance and dist > 1: # sometimes readings of 1 come in error # 
                    self._pauseDistanceSensor = True
                    self.interruptCallback("short-distance")
            sleep(0.1)    


    # Thermal sensor
    # ---------------------------------------------------------------------------------------------

    def startThermalSensor(self):
        """Start thermal sensor running on a thread"""
        self.thermalSensorThread = Thread(target=self.runThermalSensor)
        self.thermalSensorThread.start() 

    def runThermalSensor(self):
        """Thread which constantly reads from the thermal sensor and raises interrupts for significant events"""
        self._runningThermalSensor = True
        while self._runningThermalSensor:
            if not self._pauseThermalSensor:
                matrix = self.thermalSensor.readMatrix()
                min,max,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()
                if max>self.heatDetect: #!!temp
                    self._pauseThermalSensor = True
                    self.interruptCallback("heat-detect")
            sleep(0.1)                