import RPi_I2C_driver
from time import sleep
from gpiozero import Button
from crawler import *
from rotary_encoder import RotaryEncoder

class Programmer():
    """Button and LCD programmer"""

    def __init__(self, menu):
        print("Init Programmer")
        self.b1 = Button(22) 
        self.b2 = Button(23) 
        self.b3 = Button(24) 
        self.b4 = Button(25) 
        self.breturn = Button(27)

        self.b1.when_pressed = self.callback
        self.b2.when_pressed = self.callback
        self.b3.when_pressed = self.callback
        self.b4.when_pressed = self.callback
        self.breturn.when_pressed = self.callback

        self.lcd = None

        self.selected = None

        self.menu = menu

        self.knob = RotaryEncoder(17,18, 4)


    def setLcd(self, line1, line2):
        try:
            if self.lcd is None:
                print("Creating LCD", self.lcd)
                self.lcd = RPi_I2C_driver.lcd(0x3f)
                print(self.lcd)
            self.lcd.lcd_clear()
            self.lcd.lcd_display_string(line1, 1)
            self.lcd.lcd_display_string(line2, 2)
        except Exception as e:
            print("Trapped exception when creating LCD", e)
            self.lcd = None


    def callback(self, button):

        #print("Pressed button on", button.pin)
        but = str(button.pin)
        if but == "GPIO22":
            self.selected = 1
        elif but == "GPIO23":
            self.selected = 2
        elif but == "GPIO24":
            self.selected = 3
        elif but == "GPIO25":
            self.selected = 4
        elif but == "GPIO27":
            self.selected = 0 # return

    def showOptions(self, options, msg1=None, msg2=None):
        # Add arrow for menu options only
        opt1 = options[1]
        if not opt1.endswith('.'): 
            opt1 = "<"+opt1 
        else: 
            opt1 = opt1[:-1]

        opt2 = options[2]
        if not opt2.endswith('.'): 
            opt2 = opt2+">"  
        else: 
            opt2 = opt2[:-1]   

        opt3 = options[3]
        if not opt3.endswith('.'): 
            opt3 = "<"+opt3 
        else: 
            opt3 = opt3[:-1]

        opt4 = options[4]
        if not opt4.endswith('.'): 
            opt4 = opt4+">"    
        else: 
            opt4 = opt4[:-1] 

        # Generate and show line 1
        gap1 = 16 - (len(opt1) + len(opt2))
        line1 = '{}{}{}'.format(opt1, ' '*gap1, opt2)
        #self.lcd.lcd_display_string(line1, 1)

        # Insert message if given
        if msg1 is not None:
            msgLen = len(msg1)
            #print(msgLen, 8-msgLen/2, 8+msgLen-msgLen/2)
            line1 = line1[:8-int(msgLen/2)] + msg1 + line1[8+msgLen-int(msgLen/2):]

        # Generate and show line 2
        gap2 = 16 - (len(opt3) + len(opt4))
        line2 = '{}{}{}'.format(opt3, ' '*gap2, opt4)
        #self.lcd.lcd_display_string(line2, 2) 
        
        # Insert message if given
        if msg2 is not None:
            msgLen = len(msg2)
            #print(msgLen, 8-msgLen/2, 8+msgLen-msgLen/2)
            line2 = line2[:8-int(msgLen/2)] + msg2 + line2[8+msgLen-int(msgLen/2):]

        self.setLcd(line1, line2)

    def showMessage(self, line1, line2):
        self.setLcd("{: <16}".format(line1), "{: <16}".format(line2))

    def runMenu(self, menuName):
        print("runMenu", menuName)

        # If we have a list, get and show list of options
        options = self.menu[menuName]
        #print(type(options))
        if isinstance(options, list):
            print(options)
            self.showOptions(options)
        else:
            # Not a list, so must be a command.  Run it.
            print("Exectuting", options)
            exec("self."+options)
            return

        # Loop, waiting for the callback to set self.selected
        self.selected = None
        while True:
            if self.selected == None:
                sleep(0.1)
                continue

            # Get option name
            optionName = self.getSelectedOption(options)
            #optionName = options[self.selected]
            #self.selected = None
            if optionName=="return" or optionName=="quit":
                break
            elif optionName.endswith("."):
                continue # anything ending in . is ignored
            
            # Recurse to next level menu
            nextMenuName = menuName+"/"+optionName
            print(nextMenuName)
            self.runMenu(nextMenuName)

            # Show options
            print(options)
            self.showOptions(options)

    def getSelectedOption(self, options):      
        # Get option selected
        if self.selected == None:
            sleep(0.1)
            return None
        optionName = options[self.selected]
        self.selected = None
        return optionName

    def yesNo(self, msg):
        options = [".",".",".","Yes","No"]
        self.showOptions(options, msg)
        while True: 
            optionName = self.getSelectedOption(options)
            if optionName=="Yes":
                return True
            elif optionName=="No":
                return False        

if __name__ == "__main__":
    print("Testing Programmer")    

    # Items ending in . don't show arrows
    menu = {
                "main" : ["quit", "menu", "start", ".", "stop"],

                "main/stop" : "stop()",
                "main/start" : "start()",

                "main/menu":["return","one", "two", "three", "four"],

                "main/menu/one":["return","A", "B", "C", "D"],
                "main/menu/one/A": "test('A')",
                "main/menu/one/B": "test('B')",
                "main/menu/one/C": "test('C')",
                "main/menu/one/D": "test('D')",

                "main/menu/two":["return","A", "B", "C", "D."], # D not selectable
                "main/menu/two/A": "test('A')",
                "main/menu/two/B": "test('B')",
                "main/menu/two/C": "test('C')",
                "main/menu/two/D": "test('D')", 

                "main/menu/three":["return","A", "B", "C", "D"],
                "main/menu/three/A": "test2('A')",
                "main/menu/three/B": "test2('B')",
                "main/menu/three/C": "test2('C')",
                "main/menu/three/D": "test2('D')",

                "main/menu/four":["return","A", "B", "C", "D"],
                "main/menu/four/A": "test('A')",
                "main/menu/four/B": "test('B')",
                "main/menu/four/C": "test('C')",
                "main/menu/four/D": "test('D')",
            }

    class MyProgrammer(Programmer):
        def __init__(self, menu):
            Programmer.__init__(self, menu)

            self.counter = 0

        def reCallback(self,action):
            print(action)
            #print(" ")
            self.counter += action
            self.showMessage("Counter:" + str(self.counter), "Pressed" if action==0 else "")

        def test(self, action):
            print("Running test", action)

        def test2(self, action):
            """Shows creating custom action with messages and extended menu"""
            print("Running test2", action)
            counter = 0
            options = ["return",".",".",".","cancel"]
            while True:
                self.showOptions(options, "Count", str(counter))
                optionName = self.getSelectedOption(options)
                if optionName=="cancel":
                    break                   
                counter += 1

        def stop(self):
            print("Running stop")
            self.knob.stop()

        def start(self):
            print("Running start")
            self.knob.run(self.reCallback)



    programmer = MyProgrammer(menu)
    programmer.runMenu("main")

