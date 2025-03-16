from openscad import *

def ngon(filletRadius=1, nSides=6, radius=10):
    """
    Create a n-gon shape by setting up vertices and hull them.
    """
    vertices = []
    for i in range(1, nSides+1):
        deg = i * 360 / nSides
        c = circle(r=filletRadius).right(radius).rotz(deg)
        vertices.append(c)
    return hull(union(vertices))