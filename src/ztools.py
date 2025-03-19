from openscad import *

'''
WIP: generalized set of operators for higher-level abstraction for pythonscad.
'''

def bounding_box(solid):
    '''
    Returns bounding box as a 2-element list of (x, y, z) coordinates.
    mn is the "minimum" coordinate, and mx is the "maximum" coordinate.
    '''
    vertices, _ = solid.mesh()
    mn = [min(transpose) for transpose in zip(*vertices)]
    mx = [max(transpose) for transpose in zip(*vertices)]
    return [mn, mx]

def bounding_box_cube(solid, mn = None, mx = None):
    '''
    Bounding box as a cube.
    Optionally: supply mn and mx to avoid recomputing bounding box. See bounding_box() for more details.
    '''
    if not mn or not mx:
        mn, mx = bounding_box(solid)

    lengths = [abs(b - a) for a, b in zip(mn, mx)]
    center_vector = [(b + a) / 2 for a, b in zip(mn, mx)]
    return cube(lengths, center=True).translate(center_vector)

def center(solid, mn = None, mx = None):
    '''
    Center the solid on origin with bounding box.

    Optionally: supply mn and mx to avoid recomputing bounding box. See bounding_box() for more details.

    Returns [solid at origin, move_vector used to move the solid to origin]
    '''
    if not mn or not mx:
        mn, mx = bounding_box(solid)

    move_vector = [-(sum(dims) / 2) for dims in zip(mn, mx)]
    return [solid.translate(move_vector), move_vector]

def offset_3d(solid, delta = [1, 1, 1], mn = None, mx = None):
    '''
    Apply offset() to 3d shape.
    delta is a 3-element array, matching x, y, and z growth dimensions.
    Positive delta grows. Negative delta shrinks.
    Delta acts like a "radius". E.g., Delta of [1, 0, 0] grows 2 in total in x dimension.
    Returns the resized shape.
    '''
    if not mn or not mx:
        mn, mx = bounding_box(solid)

    x_mag, y_mag, z_mag = magnitudes(solid, mn, mx)
    dx, dy, dz = delta

    # Because resize is performed in respect to origin, we need to move the solid to origin first, transform, and restore back to its original position.
    at_origin, move_vector_used = center(solid, mn, mx)

    # delta is apply on "all sides".
    resized = at_origin.resize([(x_mag + 2 * dx), (y_mag + 2 * dy), (z_mag + 2 * dz)])

    # Restored to original position.
    return resized.translate([-dim for dim in move_vector_used])

def axis_aligned(solid, axis = [0, 0, 1], mn = None, mx = None):
    '''
    Generalized bounding box aligner. Defaults to positive z-axis
    (This is a work in progress; only intends to work for POSITIVE axis alignment for now).
    '''
    if not mn or not mx:
        mn, _ = bounding_box(solid)
    
    ops = (
        lambda s, minimums: s.right(-minimums),
        lambda s, minimums: s.back(-minimums),
        lambda s, minimums: s.up(-minimums),
    )
    
    res = solid
    for op, minimums, ax in zip(ops, mn, axis):
        res = op(res, minimums * ax)
    return res

def z_aligned(solid, mn = None, mx = None):
    '''
    Raise the whole solid above zero-z.
    It takes the lowest z vertex, and raise it so it's at zero-z.

    If the solid is in the air, put it on the ground.

    Optionally: supply mn and mx to avoid recomputing bounding box. See bounding_box() for more details.

    (Technically mx is not needed, and won't be checked. But present to keep function signature consistent with other bbox based functions).

    Returns post-translate solid.
    '''
    # if not mn:
    #     mn, _ = bounding_box(solid)

    # _, _, z = mn
    # return solid.up(-z)

    return axis_aligned(solid, axis = [0, 0, 1], mn=mn, mx=mx)

def xy_aligned(solid, mn = None, mx = None):
    return axis_aligned(solid, axis = [1, 1, 0], mn=mn, mx=mx)

def magnitudes(solid, mn = None, mx = None):
    '''
    Returns x, y, z magnitudes based on bounding box.

    Optionally: supply mn and mx to avoid recomputing bounding box. See bounding_box() for more details.

    Return values are 0 or positive numbers only (by definition).
    '''
    if not mn or not mx:
        mn, mx = bounding_box(solid)
    
    return [abs(big - small) for small, big in zip(mn, mx)]

def z_height(solid, mn = None, mx = None):
    '''
    Returns z-height in magnitude of the bounding box. 

    Optionally: supply mn and mx to avoid recomputing bounding box. See bounding_box() for more details.
    0 or positive numbers only (by definition).
    '''
    return magnitudes(solid, mn, mx)[-1]

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
    mask_cube = bounding_box_cube(donut)
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

    return [ (post_op | untouched), operating_vol, post_op, untouched ]

def to_matrix(vec):
    x, y, z = vec
    return [
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1]
    ]

def to_translation_vector(matrix):
    return [matrix[0][-1], matrix[1][-1], matrix[2][-1]]

def debug_face_indicators(solid, indicator = sphere(0.5), indicator_color = 'yellow'):
    '''
    A generator of solids transposed to vertices indicating a face.
    Relies on mesh() underneath.

    Designed for debugging uses to deep dive on mesh(). 

    User can show() each of the element returned by the generator.
    
    Since a solid can have MANY vertices: use itertools.islice() to efficency loop thru faces without pre-storing all the vertices x indicators.

    Note: Each generator yield is a list of indicator shapes, in which displayed together shows the vertices of a face.
    '''
    # Vertex is your (x, y, z) coordinate.
    # Faces is a list of arrays, where each array are index pointers to a specific vertex.
    # A face would comprise of at least 3 vertices.

    for coords in face_coordinates(solid):
        dots = []
        for xyz in coords:
            dots.append(indicator.translate(xyz).color(indicator_color))
        yield dots

def debug_face_coordinates(solid):
    '''
    mesh() returns face in the form of index pointers to vertices.
    This is a convenience function to return a generator of list of xyz coordinates to avoid the extra level of dereferencing.
    For usability reasons only.
    '''
    # Vertex is your (x, y, z) coordinate.
    # Faces is a list of arrays, where each array are index pointers to a specific vertex.
    # A face would comprise of at least 3 vertices.
    vertices, faces = solid.mesh()

    for vertex_indices in faces:
        coords = []
        for vertex_idx in vertex_indices:
            coords.append(vertices[vertex_idx])
        yield coords