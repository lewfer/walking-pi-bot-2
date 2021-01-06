import RPi.GPIO as GPIO
from time import sleep

# ======================================================================================================
# Servo class
# ======================================================================================================

class Servo():

    def __init__(self, pin, frequency=50, minPulseWidth=0.6, maxPulseWidth=2.3):
        '''Initialise the Servo on the given pin. Default frequency to 50Hz and pulse widths given in milliseconds'''
        self.pin = pin
        self.frequency = frequency
        self.minPulseWidth = minPulseWidth
        self.maxPulseWidth = maxPulseWidth
        GPIO.setmode(GPIO.BCM)                   # use BCM numbering
        GPIO.setup(self.pin, GPIO.OUT)           # set the pin to output mode
        self.pwm=GPIO.PWM(self.pin, frequency)   # set up pin for PWM mode
        self.pwm.start(0)                        # no angle set

    def stop(self):
        '''Stop the servo'''
        self.pwm.stop()

    def angle(self, angle):
        '''Set the servo to the given angle'''
        #duty = angle / 18 + 2                    # calculate the duty cycle for the angle we want

        pulseWidth = 100*self.minPulseWidth + (100*angle * ((self.maxPulseWidth - self.minPulseWidth) / 180))
        duty = pulseWidth  / (1000/self.frequency)
        print(duty)
        
        self.pwm.ChangeDutyCycle(duty)           # change the PWM duty cycle
        #sleep(1)        

