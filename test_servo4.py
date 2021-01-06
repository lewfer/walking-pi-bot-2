from gpiozero import Servo
from time import sleep
from threading import Thread

servo1 = Servo(19, frame_width=0.02, min_pulse_width = 0.0006, max_pulse_width = 0.0023)
servo2 = Servo(20, frame_width=0.02, min_pulse_width = 0.0006, max_pulse_width = 0.0023)
servo3 = Servo(21, frame_width=0.02, min_pulse_width = 0.0006, max_pulse_width = 0.0023)
servo4 = Servo(26, frame_width=0.02, min_pulse_width = 0.0006, max_pulse_width = 0.0023)

running = True

def t1():
    while running:
        servo1.value = -1
        sleep(1)
        servo1.value = 0
        sleep(1)
        servo1.value = 1
        sleep(1)

def t2():
    while running:
        servo2.value = -1
        sleep(1)
        servo2.value = 0
        sleep(1)
        servo2.value = 1
        sleep(1)

def t3():
    while running:
        servo3.value = -1
        sleep(1)
        servo3.value = 0
        sleep(1)
        servo3.value = 1
        sleep(1)

def t4():
    while running:
        servo4.value = -1
        sleep(1)
        servo4.value = 0
        sleep(1)
        servo4.value = 1
        sleep(1)


# Create a new thread and link it to function t1
thread1 = Thread(target=t1)
thread2 = Thread(target=t2)
thread3 = Thread(target=t3)
thread4 = Thread(target=t4)

# Start the thread - it will call t1()
thread1.start()
thread2.start()
thread3.start()
thread4.start()

input("Press enter to stop")

running = False
thread1.join()
thread2.join()
thread3.join()
thread4.join()




