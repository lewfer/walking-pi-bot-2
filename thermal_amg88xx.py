import busio
import board
import adafruit_amg88xx
import time



class ThermalSensor:

    def __init__(self):
        self.lastReading = None
        self.previousReading = None
        self.rotate = True
        self.flipHorizontal = False
        self.flipVertical = False

        i2c = busio.I2C(board.SCL, board.SDA)
        self.amg = adafruit_amg88xx.AMG88XX(i2c)


    def readMatrix(self):
        if self.lastReading is not None:
            self.previousReading = self.lastReading.copy()
        self.lastReading = self.amg.pixels
        if self.rotate:
            self. _rotate90()
        if self.flipHorizontal:
            self._flipHorizontal()
        if self.flipVertical:
            self._flipVertical()
        return self.lastReading

    def _rotate90(self):
        self.lastReading = [list(r) for r in zip(*self.lastReading[::-1])]

    def _flipHorizontal(self):
        """Flip matrix left-right"""
        for i in range(8):
            self.lastReading[i].reverse()

    def _flipVertical(self):
        self.lastReading = self.lastReading[::-1]

    def summarise(self):
        """
        Summarise the last reading.  Returns a tuple:
            min temperature in matrix
            max temperature in matrix
            mean temperature across matrix
            mean temperature for each row (as a list of 8 means)
            mean temperature for each col (as a list of 8 means)
        """
        max = -999
        min = 999
        mean = 0
        rowMeans = [0]*8
        colMeans = [0]*8
        for r,row in enumerate(self.lastReading):
            for c,temp in enumerate(row):
                if temp > max:
                    max = temp
                if temp < min:
                    min = temp
                mean += temp
                rowMeans[r] += temp/8
                colMeans[c] += temp/8
        mean = mean / 64
        hotrow = 0
        for r,temp in enumerate(rowMeans):
            if temp>rowMeans[hotrow]:
                hotrow = r
        hotcol = 0
        for c,temp in enumerate(colMeans):
            if temp>colMeans[hotcol]:
                hotcol = c
        return (min,max,mean,rowMeans,colMeans, (hotrow, hotcol))

    def delta(self):
        """Compute delta between last and previous readings"""
        if self.lastReading is None or self.previousReading is None:
            return None
        diffs = self._delta(self.lastReading, self.previousReading)
        return diffs

    def movement(self):        
        """Detect movement.  Returns the sum of abs changes in temperature across the matrix"""
        if self.lastReading is None or self.previousReading is None:
            return None

        sumAbs, rowSumAbs, colSumAbs = self._movement(self.lastReading, self.previousReading)

        hotrow = 0
        for r,delta in enumerate(rowSumAbs):
            if delta>rowSumAbs[hotrow]:
                hotrow = r
        hotcol = 0
        for c,delta in enumerate(colSumAbs):
            if delta>colSumAbs[hotcol]:
                hotcol = c

        return sumAbs, rowSumAbs, colSumAbs, (hotrow,hotcol)


    def minMaxMeanTemperature(self, matrix):
        max = -999
        min = 999
        mean = 0
        for row in matrix:
            for temp in row:
                if temp > max:
                    max = temp
                if temp < min:
                    min = temp
                mean += temp
        mean = mean / 64
        return (min,max,mean)

    def _delta(self, matrix1, matrix2):
        """Compute changes in temperature from 1 to 2"""
        #print("matrix1")
        #self.print(matrix1)
        #print("matrix2")
        #self.print(matrix2)
        diffs = [[0]*8,[0]*8,[0]*8,[0]*8,[0]*8,[0]*8,[0]*8,[0]*8]
        for i in range(8):
            for j in range(8):
                diffs[i][j] = matrix2[i][j] - matrix1[i][j]
        return diffs

    def print(self, matrix, dp=0):
        fmt = '{0:.' + str(dp) + 'f}'
        for row in matrix:
            #print([fmt.format(temp) for temp in row])
            print([round(temp,0) for temp in row])

    def _movement(self, matrix1, matrix2):
        diff = self._delta(matrix1, matrix2)
        sumAbs = 0
        rowSumAbs = [0]*8
        colSumAbs = [0]*8        
        for r,row in enumerate(diff):
            for c,temp in enumerate(row):
                sumAbs += abs(temp)
                rowSumAbs[r] += abs(temp)
                colSumAbs[c] += abs(temp)           
        return sumAbs, rowSumAbs, colSumAbs

    def printCols(self,cols, indent=""):
        print(indent, end="")
        for c in cols: print("{:>5.2f} ".format(c), end="")
        print("")
        print(indent, end="")
        print("      "*cols.index(max(cols)), " ^")

    def printMatrix(self):
        self.print(self.lastReading)


if __name__ == "__main__":
    print("Testing Thermal Sensor")       

    import os
    from colorama import Fore, Back, Style
    from collections import OrderedDict 

    def printColour(matrix, ranges, dp=0):
        fmt = '{0:.' + str(dp) + 'f}'
        for row in matrix:
            #print([fmt.format(temp) for temp in row])
            for temp in row:
                colour = ranges[list(ranges.keys())[-1]] # highest colour as default
                for k in ranges.keys():
                    if int(temp)<k:
                        colour = ranges[k]
                        break

                #print(Fore.RED+str(round(temp,0))+" ", end="")
                #print(ranges[int(temp)], end="")
                """if temp>17:
                    print(Fore.RED, end="")
                else:
                    print(Fore.GREEN, end="")"""
                print(colour+str(fmt.format(temp))+" ", end="")
                print(Style.RESET_ALL, end="")
            print("")
        print("")

    t = ThermalSensor()
    last = t.readMatrix()
    time.sleep(1)

    print("Mode: 1) Summary, 2) Column Movements, 3) Matrix")
    mode = input()[0]

    while True:
        matrix = t.readMatrix()
        #t.print(matrix,1)
        os.system('clear')

        if mode=="1":
            minval,maxval,meanval,rowmeans,colmeans,hotspot = t.summarise()
            print(minval,maxval,meanval,rowmeans,colmeans,hotspot)

        #diff = t.delta()
        #print("diff")
        #t.print(diff)

        if mode=="2":
            sumAbs, rowSumAbs, colSumAbs, hotspot = t.movement()
            t.printCols(colSumAbs)
            if (colSumAbs[hotspot[1]]>10):
                print("Movement detected")

        if mode=="3":
            ranges = OrderedDict() 
            ranges[16] = Style.DIM+Fore.BLACK+Back.BLACK
            ranges[17] = Style.DIM+Fore.CYAN+Back.BLACK
            ranges[18] = Style.DIM+Fore.BLUE+Back.BLACK
            ranges[19] = Style.DIM+Fore.GREEN+Back.BLACK
            ranges[20] = Style.DIM+Fore.YELLOW+Back.BLACK
            ranges[21] = Style.DIM+Fore.MAGENTA+Back.BLACK
            ranges[22] = Style.DIM+Fore.RED+Back.BLACK
            ranges[23] = Style.NORMAL+Fore.BLACK+Back.CYAN
            ranges[24] = Style.NORMAL+Fore.BLACK+Back.BLUE
            ranges[25] = Style.NORMAL+Fore.BLACK+Back.GREEN
            ranges[26] = Style.NORMAL+Fore.BLACK+Back.YELLOW
            ranges[27] = Style.NORMAL+Fore.BLACK+Back.MAGENTA
            ranges[28] = Style.NORMAL+Fore.BLACK+Back.RED
            ranges[29] = Style.NORMAL+Fore.BLACK+Back.WHITE
            ranges[30] = Style.BRIGHT+Fore.BLACK+Back.WHITE
                    
            printColour(matrix, ranges)


        last = matrix

        time.sleep(1)

