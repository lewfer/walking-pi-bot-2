"""
animal.py

Implementation of Animal class.
An Animal is a robot with a number of pairs of legs.
Each leg will have one and only one thread running movements at a time.  This prevents multiple threads trying to move a single servo at the same time, which causes erratic movements. 
"""

# Imports
# -------------------------------------------------------------------------------------------------
from threadhelper import *
from joint import *
from leg import *
from time import sleep
import curses
import random
import json
import logging
import sys

# Constants
# -------------------------------------------------------------------------------------------------
SETTINGSFILENAME = 'creature_settings.json'

    

# Class
# -------------------------------------------------------------------------------------------------
class Animal():
    '''Animal has a number of pairs of legs'''

    def __init__(self):
        self.legPairs = []                                              # start with no legs
        self.stopped = False                                            # flag to indicate if we want the animal to stop what it is doing
        self._legs = {}                                                  # dictionary to quickly find legs
        self._threads = {}                                               # dictionary to quickly find threads
        self.threadCount = 0

        # Set up logger to log to screen
        self.log = logging.getLogger('logger')
        self.log.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        h = logging.StreamHandler(sys.stdout)
        #h.setLevel(logging.INFO)
        h.setFormatter(formatter)  
        self.log.addHandler(h)      
        self.log.info("Created Animal")

    def setStepsPerDegree(self, spd): 
        '''Steps servo takes per angular degree.  Smaller means faster, but less smooth.  Recommended range 0.5 to 10.'''

        # Now set the steps per degree for each joint
        for pair in range(len(self.legPairs)):
            self.legPairs[pair].left.hip.stepsPerDegree = spd
            self.legPairs[pair].left.knee.stepsPerDegree = spd
            self.legPairs[pair].right.hip.stepsPerDegree = spd
            self.legPairs[pair].right.knee.stepsPerDegree = spd

    def factoryReset(self):
        self.settings = {"leg_ranges": []}
        # knee order: down, mid, up
        # hip order: back, mid, forward
        for i in range(len(self.legPairs)):
            self.settings["leg_ranges"].append({"left": {"hip": [130,90,50],"knee": [50,90,130]},"right": {"hip": [50,90,130],"knee": [130,90,50]}})
        self.storeSettings()
            
    def loadSettings(self):
        '''Load the settings file, which contains the calibrated settings for each joint'''

        try:
            # Try to load the settings file
            with open(SETTINGSFILENAME) as f:
                print("Settings", SETTINGSFILENAME, "found")
                self.settings = json.load(f)
        except FileNotFoundError:
            # If no settings file use defaults 
            print("Settings file", SETTINGSFILENAME, "not found.  Using defaults")
            self.factoryReset()
        print(self.settings)

        # Now set the default angles for each joint.  We need to mirror the angles left and right legs 
        for pair in range(len(self.legPairs)):

            self.legPairs[pair].left.hip.lowAngle = self.settings["leg_ranges"][pair]["left"]["hip"][LEG_FRONT]
            self.legPairs[pair].left.knee.lowAngle = self.settings["leg_ranges"][pair]["left"]["knee"][LEG_DOWN]
            self.legPairs[pair].right.hip.lowAngle = self.settings["leg_ranges"][pair]["right"]["hip"][LEG_BACK]
            self.legPairs[pair].right.knee.lowAngle = self.settings["leg_ranges"][pair]["right"]["knee"][LEG_UP]

            self.legPairs[pair].left.hip.midAngle = self.settings["leg_ranges"][pair]["left"]["hip"][LEG_MID]
            self.legPairs[pair].left.knee.midAngle = self.settings["leg_ranges"][pair]["left"]["knee"][LEG_MID]
            self.legPairs[pair].right.hip.midAngle = self.settings["leg_ranges"][pair]["right"]["hip"][LEG_MID]
            self.legPairs[pair].right.knee.midAngle = self.settings["leg_ranges"][pair]["right"]["knee"][LEG_MID]

            self.legPairs[pair].left.hip.highAngle = self.settings["leg_ranges"][pair]["left"]["hip"][LEG_BACK]
            self.legPairs[pair].left.knee.highAngle = self.settings["leg_ranges"][pair]["left"]["knee"][LEG_UP]
            self.legPairs[pair].right.hip.highAngle = self.settings["leg_ranges"][pair]["right"]["hip"][LEG_FRONT]
            self.legPairs[pair].right.knee.highAngle = self.settings["leg_ranges"][pair]["right"]["knee"][LEG_DOWN]

            #print(self.legPairs[pair].left.hip)
            #print(self.legPairs[pair].left.knee)
            #print(self.legPairs[pair].right.hip)
            #print(self.legPairs[pair].right.knee)


    """
    def setSettings(self):
        '''Set the current setting of each joint as the default'''

        for pair in range(len(self.legPairs)):
            self.legPairs[pair].left.hip.updateDefault()
            self.legPairs[pair].left.knee.updateDefault()
            self.legPairs[pair].right.hip.updateDefault()
            self.legPairs[pair].right.knee.updateDefault()"""

    def storeSettings(self):
        '''Store the default settings to the settings file'''
        # Save the settings dictionary to file
        with open(SETTINGSFILENAME, 'w') as f:
            json.dump(self.settings, f)

        # Reload so settings are applied
        self.loadSettings()


    def runOnThread(self, legId, func, params):
        """Run the function func on the leg identified by legId with the given params.  Wait for any existing thread to finish first"""

        # Get the thread associated with the leg
        thread = self._threads[legId]

        # Wait for existing thread to finish
        if thread is not None:
            self.log.debug("\tWait for thread {} before create new {} for {}".format(thread.name, legId, func))
            thread.join()
        else:
            self.log.debug("\tNo existing thread for {}".format(legId))

        # Start the new thread
        funcEval = eval('self._legs[legId].'+func)
        threadName = legId + ":" + func + ":" + str(self.threadCount)
        self.threadCount += 1
        thread = Thread(target=funcEval, name=threadName, kwargs=params)
        thread.start()
        #oldname = thread.name
        #thread.name = legId + ":" + func
        self.log.debug("\tStarted new thread{}".format(thread.name))

        # Store the thread against the leg
        self._threads[legId] = thread

    def joinThreads(self, legIds):
        """Wait for all threads to finish for the specified legs"""
        for legId in legIds:
            thread = self._threads[legId]
            if thread is not None:
                thread.join()

    def stopThreads(self):
        self.log.debug("Stopping threads:", self._threads)
        # Stop all threads for all legs
        for i, k in enumerate(self._threads):
            thread = self._threads[k]
            if thread is not None:
                self.log.debug("Joining {}".format(thread.name))
                thread.join()        
                self._threads[k] = None
        
        #self.log.debug("Stopped threads: {}".format(activeCount()))


    def addPairOfLegs(self, left, right):
        '''Add legs from front to back'''
        index = len(self.legPairs)
        self.legPairs.append(LegPair(left, right))

        # Add to legs dictionary
        self._legs['L'+str(index)] = self.legPairs[index].left
        self._legs['R'+str(index)] = self.legPairs[index].right

        # Add to legs threads
        self._threads['L'+str(index)] = None
        self._threads['R'+str(index)] = None

    def wakeSlowly(self, t=5):
        '''Move all legs slowly to their mid position.  The slow wake prevents a surge in current draw that could shut down the Pi.'''
       
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'mid', {'t':t})
            self.runOnThread(right, 'mid', {'t':t})
        self.joinThreads(threads)

    def unwind(self, t=1):
        '''Put the animal into a relaxing state (crouched down)'''
        
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'unwind', {'t':t})
            self.runOnThread(right, 'unwind', {'t':t})
        self.joinThreads(threads)


    def alert(self, t=1):
        '''Put the animal into an alert state (standing upright)'''
        
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'alert', {'t':t})
            self.runOnThread(right, 'alert', {'t':t})
        self.joinThreads(threads) 


    def sit(self, t=1):
        '''Put the animal into an sitting state'''
        
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'sit', {'t':t})
            self.runOnThread(right, 'sit', {'t':t})    
        self.joinThreads(threads)         
   

    def high(self, t=1):
        '''Put the animal into an high state (all servos at highest setting)'''
        
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'high', {'t':t})
            self.runOnThread(right, 'high', {'t':t})              
        self.joinThreads(threads)                     
       

    def low(self, t=1):
        '''Put the animal into an low state (all servos at lowest setting)'''
        
        self.stopped = False

        # Set up a thread for each leg movement and move all legs simultaneously
        threads = []
        for pair in range(len(self.legPairs)):
            left = 'L'+str(pair)
            right = 'R'+str(pair)
            threads += [left,right]
            self.runOnThread(left, 'low', {'t':t})
            self.runOnThread(right, 'low', {'t':t})            
        self.joinThreads(threads)    
          

    """
    def setAngles(self):
        '''Point forwards'''
        
        self.stopped = False

        # Set up a thread for each limb movement
        threads = []
        for pair in range(len(self.legPairs)):
            settings = self.settings["leg_ranges"][pair]
            print(settings["left"]["hip"])
            angles = (settings["left"]["hip"][2], settings["left"]["knee"][1])
            threads.append(Thread(target=self.legPairs[pair].left.setAngles, kwargs={"angles":angles, "t":1}))
            angles = (settings["right"]["hip"][2], settings["right"]["knee"][1])
            threads.append(Thread(target=self.legPairs[pair].right.setAngles, kwargs={"angles":angles, "t":1}))

        # Move all legs into position simulaneously
        runThreadsTogether(threads) 
    """


    def stop(self):
        '''Stop the current action'''
        self.stopped = True

        # Stop all servos
        for pair in range(len(self.legPairs)):
            self.legPairs[pair].left.stop()
            self.legPairs[pair].right.stop()

        # Stop all threads
        self.stopThreads()

if __name__ == "__main__":
    print("Testing Animal")    

    # Create animal
    animal = Animal()

    # With 2 legs           
    animal.addPairOfLegs(Leg(Joint(0), Joint(1), 1), Leg(Joint(2), Joint(3), -1))

    # Load settings from json file
    animal.loadSettings()

    print("wakeSlowly(2)")
    animal.wakeSlowly(5) 
    sleep(2)

    
    print("animal.unwind()")
    animal.unwind()
    sleep(2)

    print("alert()")
    animal.alert()
    sleep(2)

    print("sit()")
    animal.sit()
    sleep(2)
    
