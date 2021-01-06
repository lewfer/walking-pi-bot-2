from gpiozero import AngularServo
from time import sleep

servo = AngularServo(19, min_angle=-42, max_angle=44)
while True:
    servo.min()
    sleep(1)
    servo.mid()
    sleep(1)
    servo.max()
    sleep(1)
    servo.angle = 40
    sleep(1)
    servo.angle = 20
    sleep(1)
    servo.angle = 0
    sleep(1)
    servo.angle = -20
    sleep(1)
    servo.angle = -40