from ctypes import *


class Lidar():
    def __init__(self):
        self.lidar = cdll.LoadLibrary("./lidar/lidar.so") 
        self.lidar.lidarInit(0)

    def readCm(self):
        return self.lidar.lidarReadDistance()
