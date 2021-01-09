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
from statistics import median

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
        self.lastDistance = None

        # Thermal sensor
        self.thermalSensor = ThermalSensor()
        self._pauseThermalSensor = False
        self._runningThermalSensor = False
        self.lastMaxTemperature = None

        # Settings - can be overridden
        self.joint.midAngle = 90  
        self.joint.highAngle = 135   
        self.joint.lowAngle = 45        
        self.trackDelta = 10        # change in angle each iteration when tracking movement
        self.shortDistance = 10     # distance in cm to obstacle below which triggers a short-distance interrupt
        self.longDistance = 200     # distance in cm to obstacle above which triggers a long-distance interrupt
        self.humanDetectMin = 26    # temerature in C which triggers human-detect interrupt
        self.humanDetectMax = 30    # temerature in C which triggers human-detect interrupt

    # Detection and movement
    # ---------------------------------------------------------------------------------------------
    
    def trackHotspot(self):
        """Adjust position of the head in order to centre any hot spot detected.
        Returns hottest column, or None if no hotspot detected"""

        # Read the thermal sensor
        matrix = self.thermalSensor.readMatrix()
        min,max,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()

        # Get the column which is the hottest
        col = hotspot[1]

        if max>=self.humanDetectMin and max<=self.humanDetectMax:
            # React depending on if hot spot is to the left or right
            if col>=5:
                self.joint.moveRelativeToCurrent(-self.trackDelta, 0)
            elif col <=2:
                self.joint.moveRelativeToCurrent(self.trackDelta, 0)
            return col
        else:
            return None

    def trackMovement(self):
        """Adjust position of the head in order to centre any movement detected.
        Returns total movement and most changed column"""

        # Read the thermal sensor
        matrix = self.thermalSensor.readMatrix()
        min,max,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()
        values = self.thermalSensor.movement()

        # Sensor not ready
        if values is None:
            return None

        # Unpack movement
        movement,_,_,hotspot = values

        # Get the column which has most movement
        col = hotspot[1]

        # React depending on if hot spot is to the left or right
        if movement > 80/2: #!!
            print("Insufficient movement")
            offset = 1 # offset from centre to detect
            if col>=4+offset:
                matrix = self.thermalSensor.readMatrix() # read again to nullify movement
                self.joint.moveRelativeToCurrent(-self.trackDelta, 0)
            elif col <=3-offset:
                matrix = self.thermalSensor.readMatrix() # read again to nullify movement
                self.joint.moveRelativeToCurrent(self.trackDelta, 0)

        return movement,col


    def detectMovement(self):
        """Take a reading from the thermal sensor.  Checks against previous reading to see if there was movement.
           Returns the amount of movement (sum of absolute changes in temeperature of across the matrix)"""

        matrix = self.thermalSensor.readMatrix()
        min,max,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()
        movement,_,_,_ = self.thermalSensor.movement()
        #print(movement)
        return movement


    def move(self, position, t=0):
        """Move head to a position from -100 (left) to +100 (right)"""
        newAngle = remap(position,-100,100,self.joint.highAngle,self.joint.lowAngle)
        #print(newAngle)
        self.joint.moveTo(newAngle, t)

    def scan(self):
        """Scan left to right, reading distances (21 positions).  Returns the distances as a list, and the index of the min and max distance."""
        distances = []
        self.move(-100, t=2)
        dist = self.distanceSensor.readCm() # throw away first reading as it seems to be dodgy
        for pos in range(-100,101,10):
            self.move(pos, t=0)
            if pos%10==0:
                #dist1 = self.distanceSensor.readCm()
                #dist2 = self.distanceSensor.readCm()
                #dist3 = self.distanceSensor.readCm()
                #dist = median([dist1,dist2,dist3])
                dist = self.distanceSensor.readCm()
                #print([dist1,dist2,dist3],dist)
                distances.append(dist)
        self.move(0, t=2)
        return distances, distances.index(min(distances)), distances.index(max(distances))

    def scanLeft(self):
        """Scan left side, reading distances (10 positions).  Returns the distances as a list, and the index of the min and max distance."""
        distances = []
        self.move(0, t=2)
        dist = self.distanceSensor.readCm() # throw away first reading as it seems to be dodgy
        for pos in range(0,-101,-10):
            self.move(pos, t=0)
            if pos%10==0:
                dist = self.distanceSensor.readCm()
                distances.append(dist)
        distances.reverse() # so distances are left to right
        return distances, distances.index(min(distances)), distances.index(max(distances))

    def scanRight(self):
        """Scan right side, reading distances (10 positions).  Returns the distances as a list, and the index of the min and max distance."""
        distances = []
        self.move(0, t=2)
        dist = self.distanceSensor.readCm() # throw away first reading as it seems to be dodgy
        for pos in range(0,101,10):
            self.move(pos, t=0)
            if pos%10==0:
                dist = self.distanceSensor.readCm()
                distances.append(dist)
        return distances, distances.index(min(distances)), distances.index(max(distances))


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
                self.lastDistance = dist
                #print("Dist",dist)
                if dist < self.shortDistance and dist > 1: # sometimes readings of 1 come in error # 
                    self._pauseDistanceSensor = True
                    self.interruptCallback("short-distance", dist)
                #elif dist > self.longDistance:
                #    self._pauseDistanceSensor = True
                #    self.interruptCallback("long-distance", dist)                    
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
                self.lastMaxTemperature = max
                if max>=self.humanDetectMin and max<=self.humanDetectMax:
                    self._pauseThermalSensor = True
                    self.interruptCallback("human-detect", max)
            sleep(0.1)                




if __name__ == "__main__":
    print("Testing Head")                

    # ---------------------------------------------------------------------------------------------
    
        
    def interrupt(id, value):
        print("Interrupt",id,value)
        head.unPauseSensors()

    head = Head(interrupt)

    #head.startSensors()

    #head.trackHotspot()

    while True:
        col = head.trackMovement()
        print(col)

    # Scan left to right and read 21 distances
    #dists = head.scan()
    #print(dists)

    #head.move(-100, t=2)
    #sleep(1)
    #dist = head.distanceSensor.readCm()
    #print(dist)
   # head.move(-0, t=2)