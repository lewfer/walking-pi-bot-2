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

if __name__ == "__main__":
    print("Testing Thermal Sensor")       

    t = ThermalSensor()
    last = t.readMatrix()
    time.sleep(1)

    while True:
        matrix = t.readMatrix()
        #t.print(matrix,1)

        min,max,mean,rowmeans,colmeans,hotspot = t.summarise()
        #print(min,max,mean,rowmeans,colmeans,hotspot)

        #diff = t.delta()
        #print("diff")
        #t.print(diff)

        movement = t.movement()
        print(movement)

        last = matrix

        time.sleep(1)

