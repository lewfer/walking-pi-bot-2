"""
RotaryEncoder class

Rotary encoders have a knob that can register the direction of turn.
Some encoders also have a button, activated when you press the knob.

To initialise, pass in the pins of the encoder and button.
Use None for the button pin if you are not interested it it or you have no button.
Pass in a callback function, which should receive a parameter, direction which is 1 or -1 to indicate a directional turn, or 0 to indicate a button press.

See __main__ for example.

"""

from RPi import GPIO
from time import sleep
from gpiozero import Button
from threading import Thread

class RotaryEncoder():
    def __init__(self, clkPin, dtPin, buttonPin):
        # Turn pins
        self.clkPin = clkPin
        self.dtPin = dtPin

        # Set up turn pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(clkPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(dtPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Push-button on rotary encoder
        if buttonPin is not None:
            self.but = Button(buttonPin)
            self.but.when_pressed = self.buttonCallback

        counter = 0
        self.callback = None
        self.running = False            # flag to indicate if run() should continue

    def buttonCallback(self, button):
        """Called when the knob button is pressed"""
        if self.running:
            self.callback(0)

    def run(self, callback):
        self.callback = callback
        self.thread = Thread(target=self.do_run, name="Rot encoder")
        self.thread.start()        

    def do_run(self):
        """Read the turn pins, calling the callback with the direction of turns"""
        self.running = True
        clkLastState = GPIO.input(self.clkPin)
        while self.running:
            clkState = GPIO.input(self.clkPin)
            dtState = GPIO.input(self.dtPin)
            
            if clkState != clkLastState and clkLastState==1:
                #print(clkState, dtState)
                if dtState != clkState:
                    self.callback(1)
                else:
                    self.callback(-1)
            clkLastState = clkState
            sleep(0.01)
            

    def stop(self):
        """Stop checking the inputs"""
        self.running = False
        self.thread.join()
        self.callback = None



if __name__ == "__main__":
    print("Testing Rotary Encoder")    

    from threading import Thread

    # Set up callback to be notified when knob is turned or pushed
    def callback(action):
        # +1 or -1 for a direction, 0 for a button press
        print(action)

    re = RotaryEncoder(17,18, 4)

    # Call run() on a thread, so we can test the stop
    thread = Thread(target=re.run, kwargs={"callback":callback})
    thread.start()

    # Run for 10 secs    
    sleep(10)

    # Stop and wait for thread to finish
    re.stop()
    thread.join()