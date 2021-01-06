# -*- coding: utf-8 -*
import pigpio
import time

class DistanceSensor:

    def __init__(self, rxpin):
        self.RX = rxpin

        self.pi = pigpio.pi()
        self.pi.set_mode(self.RX, pigpio.INPUT)
        self.pi.bb_serial_read_open(self.RX, 115200) 

    def __del__(self):
        print("del")
        pi = pigpio.pi()
        pi.bb_serial_read_close(self.RX)
        pi.stop()

    def readCm(self):
        distance = -1
        count = 10
        
        while distance==-1 and count>0:
            time.sleep(0.05)	#change the value if needed
            (count, recv) = self.pi.bb_serial_read(self.RX)
            
            if count > 8:
                #print("b")
                for i in range(0, count-9):
                    if recv[i] == 89 and recv[i+1] == 89: # 0x59 is 89
                        #print("c")
                        checksum = 0
                        for j in range(0, 8):
                            checksum = checksum + recv[i+j]
                        checksum = checksum % 256
                        if checksum == recv[i+8]:
                            #print("d")
                            distance = recv[i+2] + recv[i+3] * 256
                            strength = recv[i+4] + recv[i+5] * 256
                            #if True: #distance <= 1200 and strength < 2000:
                                #print("e")
                                #print(distance, strength) 
                                #else:
                                # raise ValueError('distance error: %d' % distance)	
                                #i = i + 9
            count += 1

        return distance

if __name__ == '__main__':
    dist = DistanceSensor(14)
    while True:
        print(dist.readCm())
