import math
import numpy as np

class PentaGon:
    def __init__(self, radius=10, h=0, k=0, theta=0):
        self.radius = radius
        self.angle = (math.pi*2)/5

        self.trans_matrix = np.array(
            [
                [math.cos(theta), -math.sin(theta), h],
                [math.sin(theta),  math.cos(theta), k],
                [0,                0,               1]
            ])

    def generate_points(self):
        points = []

        angle = self.angle
        for i in range(5):
            angle = self.angle*i

            x = self.radius*math.cos(angle)
            y = self.radius*math.sin(angle)

            p = np.array([x, y, 1])
            p = self.trans_matrix @ p
            
            points.append((float(p[0]), float(p[1])))
        

        return points


p = PentaGon(theta=math.pi/6)
points = p.generate_points()

for point in points:
    print(point)