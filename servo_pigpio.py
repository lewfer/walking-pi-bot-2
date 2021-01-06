# Servo controlled using Pigpio method
# Not tested

import pigpio

class Servo:

    # Singleton Pigpio object
    pi = None

    def __init__(self, pin):
        self.pin = pin
        if not Servo.pi:
            print("CREATING")
            Joint.pi = pigpio.pi()

    def angle(self,angle):
        # Convert angle from 0 to 90 to pulse width of 1000 to 2000
        # Note that this gives around 90 degrees of movement, which is safe for these motors
        #v = angle * 1000 / 180 + 1000 # gives range of 90 degrees
        v = a * 2000 / 180 + 500  # gives full range of 180 degrees
        Joint.pi.set_servo_pulsewidth(self.pin, v)        