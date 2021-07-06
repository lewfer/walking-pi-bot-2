#from gpiozero import Servo
from servo_bonnet import *
from time import sleep
from threading import Thread

servo1 = Servo(14)


running = True

def t1():
    while running:
        servo1.angle(120)
        sleep(1)
        servo1.angle(90)
        sleep(1)
        servo1.angle(60)
        sleep(1)



# Create a new thread and link it to function t1
thread1 = Thread(target=t1)


# Start the thread - it will call t1()
thread1.start()


input("Press enter to stop")

running = False
thread1.join()





