# https://github.com/May-DFRobot/DFRobot/blob/master/TF-Luna%20LiDAR%EF%BC%888m%EF%BC%89Product%20Manual.pdf

# -*- coding: utf-8 -*
import pigpio
import time
from statistics import median

class DistanceSensor:

    def __init__(self, rxpin):
        self.RX = rxpin

        self.pi = pigpio.pi()
        self.pi.set_mode(self.RX, pigpio.INPUT)
        self.pi.bb_serial_read_open(self.RX, 115200) 

        self.minDistance = 5    # min distance sensor can read
        self.maxDistance = 700  # max distance sensor can read

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

    def readCm(self):
        distance = -1
        tries = 0
        
        while distance==-1:
            tries += 1
            time.sleep(0.05)	#change the value if needed
            (count, recv) = self.pi.bb_serial_read(self.RX)

            if tries>10:
                print("Trouble getting distances")

            if count < 8:
                continue

            if tries>10:
                print("+", count,end="")

            # Search for the header bytes
            orig_count = count
            while not (recv[0] == 0x59 and recv[1] == 0x59) and count>8: 
                recv = recv[1:]
                count -= 1

            if count<8:
                print(recv)

            #print("\tcount",orig_count,count, recv[0], recv[1], recv)

            if count > 8:
                #print("b")
                #for i in range(0, count-9):
                if recv[0] == 0x59 and recv[1] == 0x59: 
                    #print("c")

                    # From manual: checksum is the lower 8 bits of the cumulative sum of the numbers in the first 8 bytes
                    checksum = 0
                    for j in range(0, 8):
                        checksum = checksum + recv[j]
                    checksum = checksum % 256 

                    if checksum == recv[8]:
                        #print("d")
                        distance = recv[2] + recv[3] * 256
                        strength = recv[4] + recv[5] * 256
                        #print("\t",distance,strength)

                        # I noticed that high strength measurements were unreliable
                        if strength>32767 or strength<100:
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


        return max(min(distance,self.maxDistance),self.minDistance)

if __name__ == '__main__':
    dist = DistanceSensor(14)
    while True:
        print("dist",dist.readCm())
        #time.sleep(0.1)
