"""
leg.py

Implementation of Leg and LegPair classes.
A leg is made up of 2 joints.
A LegPair is made up of 2 legs.
Each leg can have a direction (left is 1, right is -1) which indicates if motor movements need to be mirrored.
Knee movements are up and down, hip movements are forward and backward.
"""

# Imports
# -------------------------------------------------------------------------------------------------
from threadhelper import *

# Constants
# -------------------------------------------------------------------------------------------------
HIPMOVEMENT = 30    # range of movement of knee from -HIPMOVEMENT (forward) to +HIPMOVEMENT (backward).  Reversed for right side.
KNEEMOVEMENT = 15   # range of movement of knee from -KNEEMOVEMENT (down) to +KNEEMOVEMENT (up). Reversed for right side.

# Indexes into joint settings list
LEG_MID = 1
LEG_FRONT = 2
LEG_BACK = 0
LEG_DOWN = 0
LEG_UP = 2

# Class
# -------------------------------------------------------------------------------------------------
class Leg():
    '''Leg represents a leg with 2 joints - a hip and a knee'''

    def __init__(self, hip, knee, direction):
        '''A leg is made up of a hip and knee joint
           Left and right leg movements must be mirrored, so set direction to 1 = left, -1 = right'''
        self.hip = hip
        self.knee = knee
        self.direction = direction  

    # For knee, 90 is neutral, + is lift up, - is put down
    # FOr hip, 90 is neutral, + is backwards, - is forwards
    def moveSimple(self, t):
        #print("moveSimple", self.direction)

        hipOffset = 20 * self.direction
        kneeOffset = 10 * self.direction
        self.knee.moveRelativeToMid(kneeOffset, t/5) # Lift knee
        self.hip.moveRelativeToMid(-hipOffset, t/5)  # Leg forward
        self.knee.moveRelativeToMid(-kneeOffset, t/5) # Down knee
        self.hip.moveRelativeToMid(hipOffset, t/5)  # Leg backward
        self.knee.moveRelativeToMid(0, t/5)  # Leg up to neutral position


    def reachForward(self, t):
        '''Make the leg do a reach forward movement, the first part of a walk'''
        # Up to 1/2 sec delay to introduce random movements for a more natural look
        #sleep(random.randint(0,5)/10.0) 

        self.knee.moveRelativeToMid(KNEEMOVEMENT, t/2)  

        # Move hip and knee together using threads, waiting for all threads to stop before continuing       
        hipOffset = -HIPMOVEMENT * self.direction
        kneeOffset = 2*KNEEMOVEMENT * self.direction
        t1 = Thread(target=self.knee.moveRelativeToMid, kwargs={'deltaAngle':kneeOffset, 'secs':t/2})
        t1.name = "reachForward t1"
        t2 = Thread(target=self.hip.moveRelativeToMid, kwargs={'deltaAngle':hipOffset, 'secs':t/2})
        t2.name = "reachForward t2"
        runThreadsTogether([t1,t2])

        # Put the knee down, ready for the back push
        #kneeDown = -KNEEMOVEMENT * self.direction
        #self.knee.moveRelativeToMid(kneeDown, t/2) 
        self.kneeFullDown(t/2)

    def reachBackward(self, t):
        '''Make the leg do a reach backward movement, the first part of a walk'''
        # Up to 1/2 sec delay to introduce random movements for a more natural look
        #sleep(random.randint(0,5)/10.0) 

        self.knee.moveRelativeToMid(KNEEMOVEMENT, t/2) 

        # Move hip and knee together using threads, waiting for all threads to stop before continuing  
        hipOffset = HIPMOVEMENT * self.direction
        kneeOffset = 2*KNEEMOVEMENT * self.direction
        t1 = Thread(target=self.knee.moveRelativeToMid, kwargs={'deltaAngle':kneeOffset, 'secs':t/2})
        t1.name = "reachBackward t1"
        t2 = Thread(target=self.hip.moveRelativeToMid, kwargs={'deltaAngle':hipOffset, 'secs':t/2})
        t2.name = "reachBackward t2"
        runThreadsTogether([t1,t2])

        # Put the knee down, ready for the forward push
        #kneeDown = -KNEEMOVEMENT * self.direction
        #self.knee.moveRelativeToMid(kneeDown, t/2)     
        self.kneeFullDown(t/2) 

    def reachHalfBackward(self, t):
        '''Make the leg do a half reach backward movement, the first part of a walk'''
        # Up to 1/2 sec delay to introduce random movements for a more natural look
        #sleep(random.randint(0,5)/10.0) 

        self.knee.moveRelativeToMid(KNEEMOVEMENT, t/2) 

        # Move hip and knee together using threads, waiting for all threads to stop before continuing  
        hipOffset = HIPMOVEMENT/4 * self.direction
        kneeOffset = 2*KNEEMOVEMENT * self.direction
        t1 = Thread(target=self.knee.moveRelativeToMid, kwargs={'deltaAngle':kneeOffset, 'secs':t/2})
        t1.name = "reachBackward t1"
        t2 = Thread(target=self.hip.moveRelativeToMid, kwargs={'deltaAngle':hipOffset, 'secs':t/2})
        t2.name = "reachBackward t2"
        runThreadsTogether([t1,t2])

        # Put the knee down, ready for the forward push
        #kneeDown = -KNEEMOVEMENT * self.direction
        #self.knee.moveRelativeToMid(kneeDown, t/2)   
        self.kneeFullDown(t/2)               

    def pushBackward(self, t):
        '''Make the leg do a push backward movement, the second part of a walk'''

        # Push the leg backwards
        hip = HIPMOVEMENT * self.direction
        self.hip.moveRelativeToMid(hip, t)  

    def pushForward(self, t):
        '''Make the leg do a push forward movement, the second of a walk'''

        # Push the leg forwards
        hip = -HIPMOVEMENT * self.direction
        self.hip.moveRelativeToMid(hip, t) 

    def mid(self, t=1):
        '''Put the leg into mid position'''
        
        # Move hip and knee together using threads, waiting for all threads to stop before continuing  
        hipOffset = 0
        kneeOffset = 0
        t1 = Thread(target=self.knee.moveRelativeToMid, kwargs={'deltaAngle':kneeOffset, 'secs':t})
        t1.name = "mid t1"
        t2 = Thread(target=self.hip.moveRelativeToMid, kwargs={'deltaAngle':hipOffset, 'secs':t}) 
        t2.name = "mid t2"
        runThreadsTogether([t1,t2])

    def unwind(self, t=1):
        '''Put the leg into a relaxed pose, lifting the knee up a bit'''
        
        # Move hip and knee together using threads, waiting for all threads to stop before continuing  
        hipOffset = 0                           # hip to neutral
        kneeOffset = 10 * self.direction        # knee up a bit
        t1 = Thread(target=self.knee.moveRelativeToMid, kwargs={'deltaAngle':kneeOffset, 'secs':t})
        t1.name = "unwind t1"
        t2 = Thread(target=self.hip.moveRelativeToMid, kwargs={'deltaAngle':hipOffset, 'secs':t}) 
        t2.name = "unwind t2"
        runThreadsTogether([t1,t2])

    def sit(self, t=1):
        '''Put the leg into a sitting post, with the knee down a bit'''
        
        # Move hip and knee together using threads, waiting for all threads to stop before continuing  
        hipOffset = 0                           # hip to neutral
        kneeOffset = +30 * self.direction       # knee down a bit
        t1 = Thread(target=self.knee.moveRelativeToMid, kwargs={'deltaAngle':kneeOffset, 'secs':t})
        t1.name = "sit t1"
        t2 = Thread(target=self.hip.moveRelativeToMid, kwargs={'deltaAngle':0, 'secs':t}) 
        t2.name = "sit t2"
        runThreadsTogether([t1,t2])

    def alert(self, t=1):
        '''Put the leg into an alert state, with the knee at the lowest position, raising the animal up'''
    
        # Move hip and knee together using threads, waiting for all threads to stop before continuing  
        hipOffset = 0
        kneeOffset = 0
        if self.direction==-1:
            t1 = Thread(target=self.knee.moveRelativeToHigh, kwargs={'deltaAngle':kneeOffset, 'secs':t})
        else:
            t1 = Thread(target=self.knee.moveRelativeToLow, kwargs={'deltaAngle':kneeOffset, 'secs':t})
        t1.name = "alert t1"
        t2 = Thread(target=self.hip.moveRelativeToMid, kwargs={'deltaAngle':hipOffset, 'secs':t}) 
        t2.name = "alert t2"
        runThreadsTogether([t1,t2])

    def kneeFullDown(self, t=1):
        '''Put this knee fully down'''
        kneeOffset = 0
        if self.direction==-1:
            t1 = Thread(target=self.knee.moveRelativeToHigh, kwargs={'deltaAngle':kneeOffset, 'secs':t})
        else:
            t1 = Thread(target=self.knee.moveRelativeToLow, kwargs={'deltaAngle':kneeOffset, 'secs':t})
        runThreadsTogether([t1])

    def kneeFullUp(self, t=1):
        '''Put the knee fully up'''
        kneeOffset = 0
        if self.direction==-1:
            t1 = Thread(target=self.knee.moveRelativeToLow, kwargs={'deltaAngle':kneeOffset, 'secs':t})
        else:
            t1 = Thread(target=self.knee.moveRelativeToHigh, kwargs={'deltaAngle':kneeOffset, 'secs':t})
        runThreadsTogether([t1])

    def kneeOffFloor(self, t=1):
        '''Put the knee up a little'''
        kneeOffset = 10 * self.direction        # knee up a bit
        t1 = Thread(target=self.knee.moveRelativeToMid, kwargs={'deltaAngle':kneeOffset, 'secs':t})
        runThreadsTogether([t1])


    def hipFullForward(self, t=1):
        '''Put the hip fully forward'''
        hipOffset = 0
        if self.direction==-1:
            t1 = Thread(target=self.hip.moveRelativeToHigh, kwargs={'deltaAngle':hipOffset, 'secs':t}) 
        else:
            t1 = Thread(target=self.hip.moveRelativeToLow, kwargs={'deltaAngle':hipOffset, 'secs':t}) 
        runThreadsTogether([t1])

    def hipFullBackward(self, t=1):
        '''Put the hip fully backward'''
        hipOffset = 0
        if self.direction==-1:
            t1 = Thread(target=self.hip.moveRelativeToLow, kwargs={'deltaAngle':hipOffset, 'secs':t}) 
        else:
            t1 = Thread(target=self.hip.moveRelativeToHigh, kwargs={'deltaAngle':hipOffset, 'secs':t}) 
        runThreadsTogether([t1])

    def hipMid(self, t=1):
        '''Put the hip into mid position'''
        t1 = Thread(target=self.hip.moveRelativeToMid, kwargs={'deltaAngle':0, 'secs':t}) 
        runThreadsTogether([t1])

    def kneeMid(self, t=1):
        '''Put the knee into mid position'''
        t1 = Thread(target=self.knee.moveRelativeToMid, kwargs={'deltaAngle':0, 'secs':t}) 
        runThreadsTogether([t1])


    def setHipPos(self, pos, t=0):
        if pos==LEG_FRONT:
            self.hipFullForward(t=t)
        elif pos==LEG_MID:
            self.hipMid(t=t)
        elif pos==LEG_BACK:       
            self.hipFullBackward(t=t)

    def nudgeHip(self, amount=0):
        if self.direction==-1:
            # Right hip forward is higher angle
            self.hip.nudge(amount)
        else:
            # Left hip forward is lower angle
            self.hip.nudge(-amount)

    def setKneePos(self, pos, t=0):
        if pos==LEG_UP:
            self.kneeFullUp(t=t)
        elif pos==LEG_MID:
            self.kneeMid(t=t)
        elif pos==LEG_DOWN:       
            self.kneeFullDown(t=t)

    def nudgeKnee(self, amount=0):
        if self.direction==-1:
            # Right knee up is lower angle
            self.knee.nudge(-amount)
        else:
            # Left knee up is higher angle
            self.knee.nudge(amount)

    def setAngles(self, angles, t):
        '''Make the leg point at the given angle'''
        #print("reachForward", hipOffset)

        # Move hip and knee together using threads, waiting for all threads to stop before continuing  
        t1 = Thread(target=self.knee.moveTo, kwargs={'newAngle':angles[1], 'secs':t/2})
        t1.name = "setAngles t1"
        t2 = Thread(target=self.hip.moveTo, kwargs={'newAngle':angles[0], 'secs':t/2})
        t2.name = "setAngles t2"
        runThreadsTogether([t1,t2])

    def stop(self):
        self.knee.stop()
        self.hip.stop()


# Class
# -------------------------------------------------------------------------------------------------
class LegPair():
    '''A pair of legs, one left and one right'''

    def __init__(self, left, right):
        self.left = left
        self.right = right


# Test
if __name__ == "__main__":
    print("Testing Leg")    

    from joint import *

    # Create a pair of legs
    p = LegPair(Leg(Joint(0), Joint(1), 1), Leg(Joint(2), Joint(3), -1))

    def testLeg(leg):
        # Limit movement
        leg.hip.highAngle = 130
        leg.hip.lowAngle = 50
        leg.knee.highAngle = 130
        leg.knee.lowAngle = 50
    
        print("Left reachForward()")
        leg.reachForward(2)
        print("Left pushBackward()")
        leg.pushBackward(2)

        print("reachBackward()")
        leg.reachBackward(2)
        print("pushForward()")
        leg.pushForward(2)

        print("relax()")
        leg.relax()

        print("sit()")
        leg.sit()

        print("alert()")
        leg.alert()

        print("kneeFullDown()")
        leg.kneeFullDown()
        print("kneeFullUp()")
        leg.kneeFullUp()
        print("hipFullForward()")
        leg.hipFullForward()
        print("hipFullBackward()")
        leg.hipFullBackward()

        leg.hip.moveDirectToMid()
        leg.knee.moveDirectToMid()

    
    print("Test left leg")
    testLeg(p.left)

    print("Test right leg")
    testLeg(p.right)
    
