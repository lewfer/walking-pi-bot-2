import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BCM)
GPIO.setup(19, GPIO.OUT)
GPIO.output(19, True)

pwm=GPIO.PWM(19, 50)
pwm.start(0)


for i in range(50,100):

    pwm.ChangeDutyCycle(i/10) # left -90 deg position
    sleep(0.1)



GPIO.output(19, False)
pwm.stop()
GPIO.cleanup()