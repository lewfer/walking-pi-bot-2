import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BCM)

voicePin = 16
GPIO.setup(voicePin, GPIO.OUT)
#pwm = GPIO.PWM(voicePin, 1000)
GPIO.output(voicePin, GPIO.HIGH)

#pwm.start(100)
sleep(10)
#pwm.ChangeDutyCycle(100)
GPIO.output(voicePin, GPIO.LOW)

GPIO.cleanup()