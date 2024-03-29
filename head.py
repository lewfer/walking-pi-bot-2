"""
head.py

Control the head.
The head can move left and right.
It also has a distance sensor and thermal sensor.
The distance and thermal sensor can continuously monitor and send interrupts back to the caller (the "body").
The head can perform a scan, looking left to right for obstacles and also for thermal movement.
If it detects thermal movement it can track that movement (i.e. the head will follow the movement).
"""

from joint import Joint
from distance_tf_mini import DistanceSensor
from thermal_amg88xx import ThermalSensor
from gpiozero import MotionSensor
from helpers import remap
from threading import Thread
from time import sleep
import random

class Head:

    def __init__(self, interruptCallback, log):
        """The interruptCallack function must be provided so the caller can receive interrupts from the sensors"""

        # Remember the callback function so we can call it when an interrupt condition is met
        self.interruptCallback = interruptCallback

        ## Set up the joint on the given Servo Bonnet pin
        self.joint = Joint(15)

        # Set up the distance sensor on the given RPi pin
        self.distanceSensor = DistanceSensor(14, log)
        self._distanceSensorThread = None       # thread on which to run continuous monitoring
        self._runningDistanceSensor = False     # flag to indicate if continuous monitoring is running
        self._pauseDistanceSensor = False       # flag to indicate if continuous monitoring is paused
        self.lastDistance = None                # last distance measured

        # Set up the thermal sensor (uses I2C to the RPi)
        # The thermal sensor reads a 8x8 matrix (64 readings)
        try:
            self.thermalSensor = ThermalSensor()
        except Exception as e:
            self.thermalSensor = None
            log.info("ERROR: Failed to start thermal sensor: " + str(e))
        self.thermalSensorThread = None         # thread on which to run continuous monitoring
        self._runningThermalSensor = False      # flag to indicate if continuous monitoring is running
        self._pauseThermalSensor = False        # flag to indicate if continuous monitoring is paused
        self.lastMaxTemperature = None          # last max temperature read from the 8x8 matrix
        self.lastMinTemperature = None          # last min temperature read from the 8x8 matrix

        # Set up the PIR, which is on the tail
        self.tail = MotionSensor(13)

        # Settings - can be overridden by the body
        self.joint.midAngle = 90                # midpoint angle for servo (facing forwards)
        self.joint.highAngle = 160              # high angle for servo (rightmost angle)
        self.joint.lowAngle = 20                # lowest angle for servo (leftmost angle)
        self.trackDelta = 10                    # change in angle each iteration when tracking movement
        self.shortDistance = 30                 # distance in cm to obstacle below which triggers a short-distance interrupt
        self.longDistance = 1000                # distance in cm to obstacle above which triggers a long-distance interrupt
        self.humanDetectMinTemperature = 26     # temperature in C which triggers human-detect interrupt
        self.humanDetectMaxTemperature = 30     # temperature in C which triggers human-detect interrupt
        self.colMovementThreshold = 6           # total temperature change in a matrix column above which we say we saw movement
        self.movementWaitSeconds = 0.5          # how long to wait between thermal readings to detect movement

        self.log = log


    # Detection and head movement
    # ---------------------------------------------------------------------------------------------
    
    def trackHotspot(self):
        """Adjust position of the head towards hot spot detected.
        Returns hottest column, or None if no hotspot detected"""

        if self.thermalSensor is None:
            return None

        # Read the thermal sensor
        matrix = self.thermalSensor.readMatrix()
        min,max,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()

        # Get the column which is the hottest
        col = hotspot[1]

        # Move the head accordingly
        if max>=self.humanDetectMinTemperature and max<=self.humanDetectMinTemperature:
            # React depending on if hot spot is to the left or right
            if col>=5:
                self.joint.moveRelativeToCurrent(-self.trackDelta, 0)
            elif col <=2:
                self.joint.moveRelativeToCurrent(self.trackDelta, 0)
            return col
        else:
            # No reading taken
            return None

    def trackMovement(self):
        """Adjust position of the head towards any movement detected.
        Returns True if movement detected, False otherwise"""

        if self.thermalSensor is None:
            return False

        # Read the thermal sensor
        matrix = self.thermalSensor.readMatrix()
        values = self.thermalSensor.movement()

        # If sensor not ready return
        if values is None:
            return False

        # Unpack movement values
        _,_,colmovements,hotspot = values
        
        # Get the column which has most movement
        hotcol = hotspot[1]

        detectedSignificantMovement = colmovements[hotcol]>self.colMovementThreshold
        self._printCols(colmovements, indent="Track (" + str(detectedSignificantMovement) + ")")

        # If movement detected move head by amount depending on which col saw the movement
        offset = 1    # offset from centre to detect (centre detection won't cause movement)
        if hotcol>=4+offset:
        #if hotcol>3:
            # Movement detected to the right
            #matrix = self.thermalSensor.readMatrix() # read again to nullify movement
            angle = (hotcol-3)*self.trackDelta
            #angle = self.trackDelta
            self.joint.moveRelativeToCurrent(-angle, 0.1)

        elif hotcol <=3-offset:
        #elif hotcol <4:
            # Movement detected to the left
            #matrix = self.thermalSensor.readMatrix() # read again to nullify movement
            angle = (hotcol+1)*self.trackDelta
            #angle = self.trackDelta
            self.joint.moveRelativeToCurrent(angle, 0.1)
            
        # React depending on if hot spot (i.e. most movement) is to the left or right
        if (detectedSignificantMovement):
            return True
        else:
            # No movement
            #print("No movement")
            #print("~", end="")
            return False


    def detectMovement(self):
        """Take a reading from the thermal sensor.  Checks against previous reading to see if there was movement.
           Returns True if we detected movement"""

        if self.thermalSensor is None:
            return False

        matrix = self.thermalSensor.readMatrix()
        #min,max,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()
        values = self.thermalSensor.movement()

        # If sensor not ready return
        if values is None:
            return False

        # Unpack movement values
        movement,_,colmovements,hotspot = values

        # Get the column which has most movement
        hotcol = hotspot[1]

        # See if we had significant movement
        if (colmovements[hotcol]>self.colMovementThreshold):
            self.log.info("\tMovement:")
            self._printCols(colmovements, indent="")
            return True
        else:
            self.log.info("\tNo movement:")
            self._printCols(colmovements, indent="")
            return False

    def move(self, position, t=0):
        """Move head to a position from -100 (left) to +100 (right)"""
        newAngle = remap(position,-100,100,self.joint.highAngle,self.joint.lowAngle)
        self.joint.moveTo(newAngle, t)

    def look(self):
        """Look around, moving head left to right"""
        numMovements = random.randint(3,8)
        base = -100
        self.tail.wait_for_no_motion(timeout=self.movementWaitSeconds)
        for i in range(numMovements):
            self.move(random.randint(base, base+100), t=1)
            sleep(1) # try sleeping to avoid thermal camera detecting movement immediately
            # Check for thermal movement
            if self.thermalSensor is not None:
                self.thermalSensor.readMatrix()  # read
                #sleep(self.movementWaitSeconds)     # wait a bit   
                rearMovement = self.tail.wait_for_motion(timeout=self.movementWaitSeconds)
                movement = self.detectMovement() # read again and look for deltas
            else:
                movement = False       
            if movement or rearMovement:
                return movement, rearMovement
            base = -100 if base==0 else 0
        
        # Nothing seen front or back
        return False, False           


    def scan(self):
        """Scan left to right, reading distances and checking for movement.  """

        self.log.debug("\tHead scan")

        # Move head to the left
        self.move(-100, t=2)
        dist = self.distanceSensor.readCm() # throw away first reading as it seems to be dodgy

        # Scan left to right, reading distances
        minPos = -100
        minDist = 9999
        maxPos = -100
        maxDist = -9999        
        minLeftDist = 9999
        minRightDist = 9999    
        maxLeftDist = -9999
        maxRightDist = -9999
        distances = []
        for pos in range(-100,101):
            if pos%20==0:
                self.move(pos, t=0.5)
                dist = self.distanceSensor.readMedianCm(3)
                distances.append(dist)

                if dist<minDist:
                    minPos = pos
                    minDist = dist
                if dist>maxDist:
                    maxPos = pos
                    maxDist = dist
                if pos<0 and dist<minLeftDist:
                    minLeftDist = dist
                if pos>0 and dist<minRightDist:
                    minRightDist = dist       
                if pos<0 and dist>maxLeftDist:
                    maxLeftDist = dist
                if pos>0 and dist>maxRightDist:
                    maxRightDist = dist    

        self.log.info("\tDistances:" + str(distances))

        # Move back to centre
        self.move(0, t=2)

        # Check for thermal movement
        if self.thermalSensor is not None:
            self.thermalSensor.readMatrix()  # read
            #sleep(self.movementWaitSeconds)     # wait a bit   
            rearMovement = self.tail.wait_for_motion(timeout=self.movementWaitSeconds)
            movement = self.detectMovement() # read again and look for deltas
        else:
            movement = False

        # Return all the results
        return minPos, minDist, maxPos, maxDist, minLeftDist, minRightDist, maxLeftDist, maxRightDist, movement, rearMovement

    def scanLeft(self):
        """Scan left side, reading distances at a number of positions.  Returns the index and value of the min and max distance."""
        
        # Move head to the centre
        self.move(0, t=2)
        dist = self.distanceSensor.readCm() # throw away first reading as it seems to be dodgy

        # Scan to left, reading distances
        minPos = -100
        minDist = 9999
        maxPos = -100
        maxDist = -9999       
        for pos in range(0,-101, -1):
            if pos%20==0:
                self.move(pos, t=0.5)
                dist = self.distanceSensor.readMedianCm(3)

                if dist<minDist:
                    minPos = pos
                    minDist = dist
                if dist>maxDist:
                    maxPos = pos
                    maxDist = dist

        # Return results
        return minPos, minDist, maxPos, maxDist

    def scanRight(self):
        """Scan right side, reading distances at a number of positions.  Returns the index and value of the min and max distance."""

        # Move head to the centre
        self.move(0, t=2)
        dist = self.distanceSensor.readCm() # throw away first reading as it seems to be dodgy

        # Scan to right, reading distances
        minPos = -100
        minDist = 9999
        maxPos = -100
        maxDist = -9999   
        for pos in range(0,101):
            if pos%20==0:
                self.move(pos, t=0.5)
                dist = self.distanceSensor.readMedianCm(3)

                if dist<minDist:
                    minPos = pos
                    minDist = dist
                if dist>maxDist:
                    maxPos = pos
                    maxDist = dist      

        # Return results
        return minPos, minDist, maxPos, maxDist

    # Shake head
    def shake(self):
        amount = 30
        mult = -1
        for count in range(12):
            self.move(amount, t=0.75)
            amount *= mult

        

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
                dist = self.distanceSensor.readMedianCm(3)
                self.lastDistance = dist
                #print("Dist",dist)
                if dist < self.shortDistance and dist > 1: # sometimes readings of 1 come in error # 
                    self._pauseDistanceSensor = True
                    self.interruptCallback("short-distance", dist)
                elif dist > self.longDistance:
                    self._pauseDistanceSensor = True
                    self.interruptCallback("long-distance", dist)                    
            sleep(0.1)    


    # Thermal sensor
    # ---------------------------------------------------------------------------------------------

    def startThermalSensor(self):
        """Start thermal sensor running on a thread"""
        if self.thermalSensor is None:
            return None

        self.thermalSensorThread = Thread(target=self.runThermalSensor)
        self.thermalSensorThread.start() 

    def runThermalSensor(self):
        """Thread which constantly reads from the thermal sensor and raises interrupts for significant events"""

        if self.thermalSensor is None:
            return None

        self._runningThermalSensor = True
        while self._runningThermalSensor:
            if not self._pauseThermalSensor:
                matrix = self.thermalSensor.readMatrix()
                mintemp,maxtemp,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()
                self.lastMaxTemperature = maxtemp
                self.lastMinTemperature = mintemp
                if mintemp<self.humanDetectMinTemperature and  maxtemp>=self.humanDetectMinTemperature and maxtemp<=self.humanDetectMax:
                    # Note: check mintemp is < minhuman checks that ambient temp is less than human temp.  If not, can't detect humans
                    self._pauseThermalSensor = True
                    self.interruptCallback("human-detect", maxtemp)
            sleep(0.1)                

    # Helper
    # ---------------------------------------------------------------------------------------------

    def _printCols(self,cols, indent=""):
        if self.log is not None:
            s = "\t"+indent
            for c in cols: s += "{:>5.2f} ".format(c)  
            self.log.info(s)
            if max(cols)>self.colMovementThreshold:
                s = "\t"+" "*len(indent) + "      "*cols.index(max(cols)) + "  ^"
            else:
                s = "\t"+" "*len(indent) + "      "*cols.index(max(cols)) + "  '"

            self.log.info(s)


if __name__ == "__main__":
    print("Testing Head")                

    # ---------------------------------------------------------------------------------------------
    
    from helpers import createLogger

    log = createLogger()
        
    # Set up interrupt function to receive interrupts
    def interrupt(id, value):
        print("Interrupt",id,value)
        head.unPauseSensors()

    # Create the head
    head = Head(interrupt, log)

    print("Mode: 1) Track hotspot, 2) Track movements, 3) Detect movement, 4) Scan, 5) Scan left, 6) Scan right, 7) Monitor 8) Shake")
    mode = int(input()[0])

    if mode==1:
        # Track hot spot
        head.trackHotspot()

    elif mode==2:
        # Track head movements
        while True:
            col = head.trackMovement()
            #print(col)
            sleep(0.2)
    
    elif mode==3:
        # Detect movements
        while True:
            head.detectMovement()

    elif mode==4:
        # Scan left to right and read distances
        minPos, minDist, maxPos, maxDist, minLeftDist, minRightDist, maxLeftDist, maxRightDist, movement, rearMovement = head.scan()
        print("minPos={} minDist={} maxPos={} maxDist={} minLeftDist={} minRightDist={} maxLeftDist={} maxRightDist={} movement={} rearMovement={}".format(minPos, minDist, maxPos, maxDist, minLeftDist, minRightDist, maxLeftDist, maxRightDist, movement, rearMovement))

    elif mode==5:
        # Scan left and read distances
        minPos, minDist, maxPos, maxDist = head.scanLeft()
        print("minPos={} minDist={} maxPos={} maxDist={} ".format(minPos, minDist, maxPos, maxDist))

    elif mode==6:
        # Scan right and read distances
        minPos, minDist, maxPos, maxDist = head.scanRight()
        print("minPos={} minDist={} maxPos={} maxDist={} ".format(minPos, minDist, maxPos, maxDist))

    elif mode==7:
        print("Sensing for 20 seconds")
        head.startSensors()
        for i in range(100):
            sleep(0.2)
        head.stopSensors()

    elif mode==8:
        head.shake()

    #head.move(-100, t=2)
    #sleep(1)
    #dist = head.distanceSensor.readCm()
    #print(dist)
   # head.move(-0, t=2)
