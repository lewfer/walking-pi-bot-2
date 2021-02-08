from gpiozero import MotionSensor

pir = MotionSensor(13)

print("Ready...")
while True:
    intruder = pir.wait_for_motion(timeout=2)
    if intruder:
        print("Intruder!!")
        pir.wait_for_no_motion()
        print("Ready...")
