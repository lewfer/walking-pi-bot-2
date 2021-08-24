"""
joint.py

Implementation of Joint class.  This is where the servo control happens.
Each joint has one servo.
The joint remembers its position, so you can move relative to the current position.
Joints are not aware of whether they are hip/knee or left/right.  They just move to the requested angle.
Joints have a mid angle, which is the neutral position.
The mid angle can be changed to account for the physical robot design.
Joints also have a high and low angle, which are the limits that the joint servo should be allowed to turn to.
"""

# Imports
# -------------------------------------------------------------------------------------------------
# We have a few options for driving servos.  Choose one
#from servo_gpio import Servo
#from servo_pigpio import Servo
from servo_bonnet import Servo

from easing import *

from time import sleep

# Select the easing function
def ease(t):
    return easeInOutQuad(t)

# Class
# -------------------------------------------------------------------------------------------------
class Joint():
    '''Joint represents a single joint of a leg, controlled by a single servo motor'''

    pi = None

    def __init__(self, pin):
        # Public attributes
        self.midAngle = 90                          # mid angle of servo
        self.highAngle = 180                        # highest allowable angle
        self.lowAngle = 0                           # lowest allowable angle
        self.stepsPerDegree = 1                     # number of steps to take per angular degree, bigger means smoother
        
        # Private attributes
        self._pin = pin
        self._servo = Servo(pin)
        self._angle = 90                            # current angle of servo

    def __str__(self):
        return "_pin: {} _angle: {}  lowAngle: {} midAngle: {} highAngle {} stepsPerDegree {}".format(self._pin,self._angle,self.lowAngle,self.midAngle,self.highAngle,self.stepsPerDegree)

    def _limitedAngle(self, angle):
        '''Returns the limited value of angle, to limit to the allowable range'''
        if angle > self.highAngle:
            angle = self.highAngle
        elif angle < self.lowAngle:
            angle = self.lowAngle
        return angle

    def moveTo(self, newAngle, secs):
        '''Move to angle with easing over a time period.  Version that keeps the time between the steps fixed but varies the angular movement'''
        newAngle = self._limitedAngle(newAngle)

        #print(self.stepsPerDegree)
        waitBetweenSteps = 0
        delta = newAngle-self._angle                                                     # compute change in angle
        if abs(delta)>0 : waitBetweenSteps = float(secs)/abs(delta)/self.stepsPerDegree # compute time delay between each step
        a = self._angle                                                                  # start at the previous angle

        #print(newAngle, delta, waitBetweenSteps)

        # Move one step at a time
        tt = 0.0
        for i in range (int(abs(delta)*self.stepsPerDegree)): 
            #print(self._pin,end="")
            a = self._angle + delta * ease((i/self.stepsPerDegree)/abs(delta))           # compute angle needed to move to the next step
            #print("\t",a)
            self._servo.angle(a)                                                         # move to that angle
            #print("Move to ", a) ###
            sleep(waitBetweenSteps)
            tt += waitBetweenSteps

        #print(secs, tt)
        self._servo.angle(newAngle)                                                      # move to final angle

        # Remember the new angle
        self._angle = newAngle         

    def moveToT(self, newAngle, secs):
        '''Move to angle with easing over a time period.  Version that keeps the angular movement fixed and varies the time between the steps'''
        newAngle = self._limitedAngle(newAngle)
        
        waitBetweenSteps = 0
        delta = newAngle-self._angle                                                     # compute change in angle

        #print(newAngle, delta, waitBetweenSteps)
        #print("from ", self._angle, "to", newAngle)

        # Move one step at a time
        tt = 0.0
        for i in range (int(abs(delta)*self.stepsPerDegree)): 
            #print(self._pin,end="")
            t = secs * ease((i/self.stepsPerDegree)/abs(delta))
            waitBetweenSteps = t - tt 
            #print(i, self._angle+i/self.stepsPerDegree, t, waitBetweenSteps)
            #print("\t",a)
            self._servo.angle(self._angle + i/self.stepsPerDegree * (-1 if delta < 0 else 1))                                                         # move to that angle
            #print("Move to ", a) ###
            sleep(waitBetweenSteps)
            tt += waitBetweenSteps

        #print(secs, tt)
        self._servo.angle(newAngle)                                                      # move to final angle

        # Remember the new angle
        self._angle = newAngle         

    def moveRelativeToCurrent(self, deltaAngle, secs):
        '''Move relative to mid angle.  delta can be positive or negative'''
        newAngle = self._limitedAngle(self._angle+deltaAngle)
        self.moveTo(newAngle, secs)
        
    def moveRelativeToMid(self, deltaAngle, secs):
        '''Move relative to mid angle.  delta can be positive or negative'''
        newAngle = self._limitedAngle(self.midAngle+deltaAngle)
        #print(newAngle)
        self.moveTo(newAngle, secs)

    def moveRelativeToLow(self, deltaAngle, secs):
        '''Move relative to low angle.  delta can be positive'''
        newAngle = self._limitedAngle(self.lowAngle+deltaAngle)
        #print(self.lowAngle,newAngle)
        self.moveTo(newAngle, secs)

    def moveRelativeToHigh(self, deltaAngle, secs):
        '''Move relative to low angle.  delta can be negative'''
        newAngle = self._limitedAngle(self.highAngle+deltaAngle)
        #print(self.highAngle,newAngle)
        self.moveTo(newAngle, secs)

    def moveDirectTo(self, newAngle):
        '''Move direct to the angle, without easing'''
        newAngle = self._limitedAngle(newAngle)
        self._servo.angle(newAngle)                                                      # move to final angle
        #print(newAngle)
        self._angle = newAngle                                                           # remember the new angle

    def moveDirectToMid(self):
        '''Move direct to the mid angle, without easing'''
        #print("moveDirectToMid", self.midAngle)
        self.moveDirectTo(self.midAngle)

    def nudge(self, amount=0):
        '''Used for calibration.  Angle limited to 0-180'''
        newAngle = min(180,max(0,self._angle + amount))
        #print("Nudge", self._pin, amount, self._angle, newAngle)
        self._angle = newAngle
        #print(self._angle)
        self._servo.angle(self._angle)                                                      # move to final angle

    def stop(self):
        '''Stop the servo'''
        self._servo.stop()

# Tests
if __name__ == "__main__":
    print("Testing Joint")    
    j = Joint(1)

    print("Test moveTo()")
    print("Move direct to 90")
    j.moveDirectTo(90)
    print("Move to 180 in 2 seconds")
    j.moveTo(180,2)    
    print("Move to 0 in 2 seconds")
    j.moveTo(00,2)
    print("Move to 90 in 2 secs")
    j.moveTo(90,2)

    """
    print("Test moveToT()")
    print("Move direct to 90")
    j.moveDirectTo(90)
    print("Move to 180 in 2 seconds")
    j.moveToT(180,2)
    print("Move to 0 in 2 seconds")
    j.moveToT(0,2)
    print("Move to 90 in 2 seconds")
    j.moveToT(90,2)
    
    print("Test moveRelativeToCurrent()")
    print("Move 20 degrees up")
    j.moveRelativeToCurrent(20, 1)
    print("Move 20 degrees up")
    j.moveRelativeToCurrent(20, 1)
    j.moveDirectTo(90)
    print("Move 20 degrees down")
    j.moveRelativeToCurrent(-20, 1)
    print("Move 20 degrees down")
    j.moveRelativeToCurrent(-20, 1)
    j.moveDirectTo(90)

    print("Test moveRelativeToMid()")
    print("Move 20 degrees to mid")
    j.moveRelativeToMid(20, 1)
    print("Move 40 degrees to mid")
    j.moveRelativeToMid(40, 1)
    j.moveDirectTo(90)
    print("Move -20 degrees to mid")
    j.moveRelativeToMid(-20, 1)
    print("Move -40 degrees to mid")
    j.moveRelativeToMid(-40, 1)            
    j.moveDirectTo(90)
    """