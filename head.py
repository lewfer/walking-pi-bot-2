"""
Control the head
"""

from joint import Joint
from distance_tf_mini import DistanceSensor
from thermal_amg88xx import ThermalSensor
from helpers import remap
from threading import Thread
from time import sleep

class Head:

    def __init__(self, interruptCallback):

        self.interruptCallback = interruptCallback

        self.joint = Joint(4)
        self.joint.midAngle = 90  
        self.joint.highAngle = 135   
        self.joint.lowAngle = 45

        # Distance sensor
        self.distanceSensor = DistanceSensor(14)
        self._distanceSensorThread = None
        self._pauseDistanceSensor = False
        self._runningDistanceSensor = False

        # Thermal sensor
        self.thermalSensor = ThermalSensor()
        self._pauseThermalSensor = False
        self._runningThermalSensor = False


    def trackMovement(self):
        matrix = self.thermalSensor.readMatrix()
        min,max,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()

        col = hotspot[1]
        
        self.thermalSensor.print(matrix, 0)
        print(colmeans)
        print(col)

        if col>=5:
            self.joint.moveRelativeToCurrent(-10, 0)
        elif col <=2:
            self.joint.moveRelativeToCurrent(10, 0)

    def detectMovement(self):
        matrix = self.thermalSensor.readMatrix()
        min,max,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()
        movement = self.thermalSensor.movement()
        print(movement)
        return movement


    def move(self, amount):
        """Move head from -100 (left) to +100 (right)"""
        newAngle = remap(amount,-100,100,self.joint.lowAngle,self.joint.highAngle)
        print(newAngle)
        self.joint.moveTo(newAngle, 0)

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

    def startDistanceSensor(self):
        self._distanceSensorThread = Thread(target=self.runDistanceSensor)
        self._distanceSensorThread.start() 

    def runDistanceSensor(self):
        self._runningDistanceSensor = True
        while self._runningDistanceSensor:
            if not self._pauseDistanceSensor:
                dist = self.distanceSensor.readCm()
                #print("Dist",dist)
                if dist < 10 and dist > 1: # sometimes readings of 1 come in error # !!dist
                    self._pauseDistanceSensor = True
                    self.interruptCallback("short-distance")
            sleep(0.1)    

    def startThermalSensor(self):
        self.thermalSensorThread = Thread(target=self.runThermalSensor)
        self.thermalSensorThread.start() 

    def runThermalSensor(self):
        self._runningThermalSensor = True
        while self._runningThermalSensor:
            if not self._pauseThermalSensor:
                matrix = self.thermalSensor.readMatrix()
                min,max,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()
                if max>26: #!!temp
                    self._pauseThermalSensor = True
                    self.interruptCallback("heat")
            sleep(0.1)                