from openscad import *
import math

def bezier_curve(angle=90, heightLength=10, baseLength=10, fn=30):
    angle_rad = math.radians(angle)

    heightsIncrements = heightLength / fn
    baseIncrements = baseLength / fn

    # These are points along the height (y axis)
    a = [[r * heightsIncrements * math.cos(angle_rad), r * heightsIncrements * math.sin(angle_rad)] for r in range(1, fn + 2)]

    # These are points along the base (x axis).
    b = [[x * baseIncrements, 0] for x in range(fn, -1, -1)]


    poly = [polygon([[0, 0], a[i], b[i]]) for i in range(min(len(a), len(b)))]
    return union(poly)

#show(bezier_curve())