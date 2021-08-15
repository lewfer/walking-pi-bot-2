# https://github.com/May-DFRobot/DFRobot/blob/master/TF-Luna%20LiDAR%EF%BC%888m%EF%BC%89Product%20Manual.pdf

# -*- coding: utf-8 -*
import pigpio
import time
from statistics import median

class DistanceSensor:

    def __init__(self, rxpin, log=None):
        self.RX = rxpin

        self.pi = pigpio.pi()
        self.pi.set_mode(self.RX, pigpio.INPUT)
        self.pi.bb_serial_read_open(self.RX, 115200) 

        self.minDistance = 5    # min distance sensor can read
        self.maxDistance = 700  # max distance sensor can read
        self.errorDistance = 1000  # distance to return if we get an error (a large value so robot does not take some avoiding action)

        self.log = log

    def __del__(self):
        print("del")
        pi = pigpio.pi()
        pi.bb_serial_read_close(self.RX)
        pi.stop()

    def readMedianCm(self, n):
        dists = []
        for i in range(n):
            dist = self.readCm()
            dists.append(dist)
        dist = median(dists)
        return dist

    def p(self, buffer):
        for b in buffer:
            print(hex(b)[2:]+".",end="")       
        print("") 

    def readCm(self):
        distance = -1
        tries = 0
        
            
        #print("ReadCm")
        while distance==-1:
            tries += 1
            #time.sleep(0.05)	#change the value if needed


            buffer = bytearray()
            count = 0
            tries2 = 0
            while count<9:
                tries2 += 1
                (count, recv) = self.pi.bb_serial_read(self.RX)
                if count>0:
                    #print("buffer",type(buffer), count)
                    #print("+",end="")
                    buffer += recv
                time.sleep(0.02)
                if tries2>20:
                    return self.errorDistance

            #self.p(buffer[:10])
            count = len(buffer)


            if tries>10:
                print("Trouble getting distances", tries)
                time.sleep(0.2)

            # Search for the header bytes
            orig_count = count
            while not (buffer[0] == 0x59 and buffer[1] == 0x59) and count>8: 
                buffer = buffer[1:]
                count -= 1

            #print("Ready:",end="")
            #self.p(buffer)
            #print("")

            #print("\tcount",orig_count,count, recv[0], recv[1], recv)

            if count > 8:
                #print("b")
                #for i in range(0, count-9):
                if buffer[0] == 0x59 and buffer[1] == 0x59: 
                    #print("c")

                    # From manual: checksum is the lower 8 bits of the cumulative sum of the numbers in the first 8 bytes
                    checksum = 0
                    for j in range(0, 8):
                        checksum = checksum + buffer[j]
                    checksum = checksum % 256 

                    if checksum == buffer[8]:
                        #print("d")
                        distance = buffer[2] + buffer[3] * 256
                        strength = buffer[4] + buffer[5] * 256
                        #print("\t",distance,strength)

                        #if distance>500:
                        #    print("\t",distance,strength)

                        # I noticed that high strength measurements were unreliable
                        #if strength>32767 or strength<100:
                        if strength>40000 or strength<20:
                            print("strength failed", strength, distance)
                            distance = -1

                        #if True: #distance <= 1200 and strength < 2000:
                            #print("e")
                            #print(distance, strength) 
                            #else:
                            # raise ValueError('distance error: %d' % distance)	
                            #i = i + 9
                    else:
                        #print("Checksum failed")
                        pass
                #buffer = bytearray()
            else:
                #print("lost bytes", end="")
                #self.p(buffer[:10])
                # keep buffer
                pass

            if tries>20:
                return self.errorDistance

        # Keep measurements within range
        return max(min(distance,self.maxDistance),self.minDistance)

if __name__ == '__main__':
    dist = DistanceSensor(14)
    i = 0
    while True:
        print(" dist",dist.readCm(), end="")
        if i%10==0:
            print("")
        #time.sleep(0.1)
        i += 1
