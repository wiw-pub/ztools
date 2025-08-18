from openscad import *

nimport('https://raw.githubusercontent.com/wiw-pub/ztools/refs/heads/main/src/ztools.py')

'''
2 examples illustrating usage of simple_fillet and simple_chamfer.
'''

fn = 100

def fillet_example():

    # T shape.
    wedge = union(square([20, 5]), square([5, 20]).right(7.5))
    wedge = wedge.linear_extrude(10)

    # masked areas for applying chamfer.
    masks = [
        rolling_hull(cube(2), [[7.5, 5, 0], [7.5, 5, 10]]),
        rolling_hull(cube(2), [[12.5, 5, 0], [12.5, 5, 10]]),
    ]

    post_op = [simple_fillet(m, wedge) for m in masks]
    
    # hulled area under masks, and original T shape minus masked areas.
    hulled, origs = zip(*post_op)
    
    return [*hulled, *origs]
    

def chamfer_example():
    
    # Cube with a hole.
    cube_with_hole = cube(20, center=True) - cylinder(d=5, h=40, center=True)

    # Apply 2.5 chamfer to the peg hole.
    # XXX: If square instead of circle, it would also chamfer in that shape.
    #mask = square([5, 5], center=True).linear_extrude(3).up(10 - 2.5).color('red')
    mask = circle(d=8, fn=6).linear_extrude(3).up(10 - 2.5).color('red')
    
    chamfered_solid, _ = simple_chamfer(mask, cube_with_hole)
    
    return chamfered_solid
    
show([union(fillet_example()).right(20), union(chamfer_example()).left(20)])