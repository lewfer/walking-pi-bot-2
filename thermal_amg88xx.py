import time
import busio
import board
import adafruit_amg88xx
i2c = busio.I2C(board.SCL, board.SDA)
amg = adafruit_amg88xx.AMG88XX(i2c)



class ThermalSensor:

    def __init__(self):
        pass

    def readMatrix(self):
        return amg.pixels

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
                mean+= temp
        mean = mean / 64
        return (min,max,mean)

    def delta(self, matrix1, matrix2):
        """Compute changes in temperature from 1 to 2"""
        diffs = [[0]*8]*8
        for i,row in enumerate(matrix):
            for j,temp in enumerate(row):
                diffs[i][j] = matrix2[i][j] - matrix1[i][j]
        return diffs

    def print(self, matrix):
        for row in matrix:
            print(['{0:.1f}'.format(temp) for temp in row])

    def movement(self, matrix1, matrix2):
        diff = self.delta(matrix1, matrix2)
        sumAbs = 0
        for row in diff:
            for temp in row:
                sumAbs += abs(temp)
        return sumAbs

if __name__ == "__main__":
    print("Testing Thermal Sensor")       

    t = ThermalSensor()
    last = t.readMatrix()

    while True:
        matrix = t.readMatrix()
        t.print(matrix)

        min,max,mean = t.minMaxMeanTemperature(matrix)
        print(min,max,mean)

        diff = t.delta(last, matrix)
        t.print(diff)

        movement = t.movement(last, matrix)
        print(movement)

        last = matrix

        time.sleep(1)

