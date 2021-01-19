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
        self.lastDistance = None

        # Thermal sensor
        self.thermalSensor = ThermalSensor()
        self._pauseThermalSensor = False
        self._runningThermalSensor = False
        self.lastMaxTemperature = None
        self.lastMinTemperature = None

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
        #_,_,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()
        values = self.thermalSensor.movement()

        # If sensor not ready return
        if values is None:
            return False

        # Unpack movement values
        movement,_,colmovements,hotspot = values
        #print("Movement {: 5.2f} Thermal columns ".format(movement), end="")
        self.thermalSensor.printCols(colmovements, indent="\t")
        #for c in colmovements: print("{: 5.2f} ".format(c), end="")
        #print("")
        #print("                               ", "      "*colmovements.index(max(colmovements)), "^")

        # Get the column which has most movement
        hotcol = hotspot[1]

        # React depending on if hot spot (i.e. most movement) is to the left or right
        if (colmovements[hotcol]>10): #!!
        #if movement > 80/3: #!!
            print("Detected movement")
            #print(movement,col)
            offset = 1 # offset from centre to detect
            if hotcol>=4+offset:
                # Movement detected to the right, so move head
                matrix = self.thermalSensor.readMatrix() # read again to nullify movement
                self.joint.moveRelativeToCurrent(-self.trackDelta, 0)
            elif hotcol <=3-offset:
                # Movement detected to the left, so move head
                matrix = self.thermalSensor.readMatrix() # read again to nullify movement
                self.joint.moveRelativeToCurrent(self.trackDelta, 0)

            return True

        return False


    def detectMovement(self):
        """Take a reading from the thermal sensor.  Checks against previous reading to see if there was movement.
           Returns the amount of movement (sum of absolute changes in temeperature of across the matrix)"""

        matrix = self.thermalSensor.readMatrix()
        #min,max,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()
        movement = self.thermalSensor.movement()

        # If sensor not ready return
        if movement is None:
            return False

        movement,_,colmovements,hotspot = movement

        # Get the column which has most movement
        hotcol = hotspot[1]

        if (colmovements[hotcol]>10): #!!
        #if movement>80: #!!param
            #print("movement {}".format(movement))
            print("\tMovement:")
            self.thermalSensor.printCols(colmovements, indent="\t")
            return True
        else:
            print("\tNo movement:")
            #print("no movement {}".format(movement))
            self.thermalSensor.printCols(colmovements, indent="\t")
            return False

    def move(self, position, t=0):
        """Move head to a position from -100 (left) to +100 (right)"""
        newAngle = remap(position,-100,100,self.joint.highAngle,self.joint.lowAngle)
        #print(newAngle)
        self.joint.moveTo(newAngle, t)

    def scan(self):
        """Scan left to right, reading distances.  """
        distances = []
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
                if pos<=0 and dist<minLeftDist:
                    minLeftDist = dist
                if pos>0 and dist<minRightDist:
                    minRightDist = dist       
                if pos<=0 and dist>maxLeftDist:
                    maxLeftDist = dist
                if pos>0 and dist>maxRightDist:
                    maxRightDist = dist    

        print("\t", distances)

        # Move back to centre
        self.move(0, t=2)

        # Check for thermal movement
        self.thermalSensor.readMatrix()  # read
        sleep(1)                         #!!  wait
        movement = self.detectMovement() # read again and look for deltas

        return minPos, minDist, maxPos, maxDist, minLeftDist, minRightDist, maxLeftDist, maxRightDist, movement


        #return distances, distances.index(min(distances)), distances.index(max(distances)), movement

    def scanLeft(self):
        """Scan left side, reading distances (10 positions).  Returns the distances as a list, and the index of the min and max distance."""
        distances = []
        self.move(0, t=2)
        dist = self.distanceSensor.readCm() # throw away first reading as it seems to be dodgy

        minPos = -100
        minDist = 9999
        maxPos = -100
        maxDist = -9999       

        for pos in range(0,-101,-10):
            if pos%10==0:
                self.move(pos, t=0.5)
                dist = self.distanceSensor.readMedianCm(3)
                distances.append(dist)

                if dist<minDist:
                    minPos = pos
                    minDist = dist
                if dist>maxDist:
                    maxPos = pos
                    maxDist = dist

        return minPos, minDist, maxPos, maxDist

        #distances.reverse() # so distances are left to right
        #return distances, distances.index(min(distances)), distances.index(max(distances))

    def scanRight(self):
        """Scan right side, reading distances (10 positions).  Returns the distances as a list, and the index of the min and max distance."""
        distances = []
        self.move(0, t=2)
        dist = self.distanceSensor.readCm() # throw away first reading as it seems to be dodgy

        minPos = -100
        minDist = 9999
        maxPos = -100
        maxDist = -9999   

        for pos in range(0,101,10):
            if pos%10==0:
                self.move(pos, t=0.5)
                dist = self.distanceSensor.readMedianCm(3)
                distances.append(dist)

                if dist<minDist:
                    minPos = pos
                    minDist = dist
                if dist>maxDist:
                    maxPos = pos
                    maxDist = dist      

        return minPos, minDist, maxPos, maxDist

        #return distances, distances.index(min(distances)), distances.index(max(distances))


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
                mintemp,maxtemp,mean,rowmeans,colmeans,hotspot = self.thermalSensor.summarise()
                self.lastMaxTemperature = maxtemp
                self.lastMinTemperature = mintemp
                if mintemp<self.humanDetectMin and  maxtemp>=self.humanDetectMin and maxtemp<=self.humanDetectMax:
                    # Note: check mintemp is < minhuman checks that ambient temp is less than human temp.  If not, can't detect humans
                    self._pauseThermalSensor = True
                    self.interruptCallback("human-detect", maxtemp)
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

    """
    while True:
        col = head.trackMovement()
        #print(col)
        sleep(0.2)
    """

    # Scan left to right and read 21 distances
    #distances, mindist, maxdist, movement = head.scan()
    minPos, minDist, maxPos, maxDist, minLeftDist, minRightDist, maxLeftDist, maxRightDist, movement = head.scan()
    #print("distances={} mindist={}(idx={}) maxdist={}(idx={}) movement={}".format(distances, distances[mindist], mindist, distances[maxdist], maxdist, movement))
    print("minPos={} minDist={} maxPos={} maxDist={} minLeftDist={} minRightDist={} maxLeftDist={} maxRightDist={} movement={}".format(minPos, minDist, maxPos, maxDist, minLeftDist, minRightDist, maxLeftDist, maxRightDist, movement))

    #head.move(-100, t=2)
    #sleep(1)
    #dist = head.distanceSensor.readCm()
    #print(dist)
   # head.move(-0, t=2)