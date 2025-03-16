from openscad import *

'''
WIP: generalized set of operators for higher-level abstraction for pythonscad.
'''

def bounding_box(solid):
    '''
    Returns bounding box as a 2-element list of (x, y, z) coordinates.
    '''
    vertices, _ = solid.mesh()
    mn = [min(transpose) for transpose in zip(*vertices)]
    mx = [max(transpose) for transpose in zip(*vertices)]
    return [mn, mx]

def bounding_box_mask(solid):
    '''
    Bounding box as a cube.
    '''
    mn, mx = bounding_box(solid)
    lengths = [abs(b - a) for a, b in zip(mn, mx)]
    center_vector = [(b + a) / 2 for a, b in zip(mn, mx)]
    return cube(lengths, center=True).translate(center_vector)

def center(solid):
    '''
    Center the solid on origin with bounding box.
    Returns [solid at origin, move_vector used to move the solid to origin]
    '''
    mn, mx = bounding_box(solid)
    move_vector = [-(sum(dims) / 2) for dims in zip(mn, mx)]
    return [solid.translate(move_vector), move_vector]

def z_above_ground(solid):
    '''
    Raise the whole solid above zero-z.
    It takes the lowest z vertex, and raise it so it's at zero-z.
    Returns post-translate solid.
    '''
    mn, _ = bounding_box(solid)
    _, _, z = mn
    
    if z < 0:
        return solid.up(-z)
    return solid

def z_height(solid):
    '''
    Returns z-height in magnitude of the bounding box. 
    0 or positive numbers only (by definition).
    '''
    mn, mx = bounding_box(solid)
    return abs(mx[-1] - mn[-1])

def z_bisect(solid, top_mask=None):
    '''
    Horizontal chop, given (optional) top mask.
    If top mask is unspecified, xy-plane is used as the cut line.
    Return [top, bottom] after cut.
    '''
    if not top_mask:
        # Just need the xy dimensions.
        mn, mx = bounding_box(solid)
        
        # Clock wise points
        xy_points = [
            mn[:2],   # lower left
            [mn[0], mx[1]],
            mx[:2],   # upper right
            [mx[0], mn[1]]
        ]
        top_mask = polygon(xy_points).linear_extrude(mx[2])

    top = solid & top_mask
    bottom = solid - top
    return [top, bottom]

def z_donut_hole(donut):
    '''
    You have a donut. You want the donut hole.
    '''
    mask_cube = bounding_box_mask(donut)
    outer = hull(donut)
    
    # intersect the hull(donut) to cut out all the extra crap from bounding box cube.
    res = (mask_cube - donut) & outer
    return res


def z_hammer_hull_union(top_solid, bottom_solid, full_pierce=False):
    '''
    Top solid "presses" into the bottom solid, and unioned.
    Simple put: top_solid | (bottom_solid - hull(top_solid))
    Example: donut + box = preserve the Donut's hole.

    Optional: full_pierce = True means the "hole punching" to bottom_solid would be a projection(hull(top_solid)) in the Z direction.
    '''
    if full_pierce:
        bottom_solid_height = z_height(bottom_solid)
        print(bottom_solid_height)
        mn, _ = bounding_box(bottom_solid)
    
        # Create a hole punch to bottom_solid, use projection(hull(top_solid) thru the height of bottom_solid.
        hole_punch = projection(hull(top_solid)).linear_extrude(bottom_solid_height)
        
        # Since we are full_piercing: If there's "below ground" volume, translate the hole_punch accordingly.
        if mn[-1] < 0:
            hole_punch = hole_punch.down(-mn[-1])

        bottom_solid -= hole_punch

    return top_solid | (bottom_solid - hull(top_solid))

def masked_map(mask, solid, func=lambda shape: shape.scale([0.5, 0.5, 1])):
    '''
    Only apply a lambda over the masked volume.

    Use case: fillet only the masked volume, but leave the rest alone.
    Operating_vol = Solid & mask
    Untouched = solid - operating_vol

    For demo purposes, func is preassigned to scaling 50% on xy direction. Pass in an explicit lambda for your use case.

    Returns [ (Apply(operating_vol) | untouched), Apply(operating_vol), untouched ]. The non-first element are for debugging purposes.
    '''
    operating_vol = solid & mask
    untouched = solid - operating_vol
    post_op = func(operating_vol)

    return [ (post_op | untouched), post_op, untouched ]

def debug_face_indicators(solid, indicator = sphere(0.5), indicator_color = 'blue'):
    '''
    A generator of solids transposed to vertices indicating a face.
    Relies on mesh() underneath.

    Designed for debugging uses to deep dive on mesh(). 

    User can show() each of the element returned by the generator.
    
    Since a solid can have MANY vertices: use itertools.islice() to efficency loop thru faces without pre-storing all the vertices x indicators.
    '''
    # Vertex is your (x, y, z) coordinate.
    # Faces is a list of arrays, where each array are index pointers to a specific vertex.
    # A face would comprise of at least 3 vertices.
    vertices, faces = solid.mesh()

    for vertex_indices in faces:
        lst_indicators = []
        for vertex_idx in vertex_indices:
            dot = indicator.translate(vertices[vertex_idx]).color(indicator_color)
            lst_indicators.append(dot)
        yield lst_indicators