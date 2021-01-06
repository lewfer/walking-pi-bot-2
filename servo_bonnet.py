from time import sleep

# Import the PCA9685 module.
import Adafruit_PCA9685

# Initialise the PCA9685 using the default address (0x40).
pwm = Adafruit_PCA9685.PCA9685()

# Alternatively specify a different address and/or bus:
#pwm = Adafruit_PCA9685.PCA9685(address=0x41, busnum=2)

# Uncomment to enable debug output.
#import logging
#logging.basicConfig(level=logging.DEBUG)



# ======================================================================================================
# ServoBonnet class
# ======================================================================================================

class Servo():

    def __init__(self, pin, frequency=50, minPulseWidth=0.6, maxPulseWidth=2.3):
        '''Initialise the Servo on the given pin. Default frequency to 50Hz and pulse widths given in milliseconds'''
        self.pin = pin
        self.minPulseWidth = minPulseWidth
        self.maxPulseWidth = maxPulseWidth 
        self.frequency = frequency   
        pwm.set_pwm_freq(frequency)

    def stop(self):
        pass
    
    def angle(self, angle):
        '''Set the servo to the given angle'''
        #print(angle)

        # Calculate the desired pulse width to achieve the angle
        pulseWidth = self.minPulseWidth + (angle * ((self.maxPulseWidth - self.minPulseWidth) / 180))
        
        # Calculate the number of "ticks", with 4096 ticks per second
        servoBonnetTicks = pulseWidth*1000/(1000*1000/4096/self.frequency)
        #print(servoBonnetTicks)

        # Send the pulse to the servo
        pwm.set_pwm(self.pin, 0, int(servoBonnetTicks))

