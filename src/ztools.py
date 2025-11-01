from openscad import *

import math, heapq
from collections.abc import Iterable

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

def bounding_box_volume(solid, mn = None, mx = None):
    '''
    Computes the volume of the bounding box for a solid.

    Optionally: supply mn and mx to avoid recomputing bounding box. See bounding_box() for more details.
    '''
    if not mn or not mx:
        mn, mx = bounding_box(solid)

    mag_x, mag_y, mag_z = magnitudes(solid, mn, mx)
    return mag_x * mag_y * mag_z

def center(solid, axis = [1, 1, 1], mn = None, mx = None):
    '''
    Center the solid on origin with bounding box.

    Optionally: Choose which axis you want to center on. Default = center on all 3 axis.
    Optionally: supply mn and mx to avoid recomputing bounding box. See bounding_box() for more details.

    Returns [solid at origin, move_vector used to move the solid to origin]
    '''
    if not mn or not mx:
        mn, mx = bounding_box(solid)

    move_vector = [-(sum(dims) / 2) if axis[axis_idx] == 1 else 0 for axis_idx, dims in enumerate(zip(mn, mx))]
    return [solid.translate(move_vector), move_vector]

def offset_3d(solid, delta = [1, 1, 1], auto_center=True, mn = None, mx = None):
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
    # Do this if auto_center=True.
    at_origin = solid
    if auto_center:
        at_origin, move_vector_used = center(solid, mn=mn, mx=mx)

    # delta is apply on "all sides".
    resized = at_origin.resize([(x_mag + 2 * dx), (y_mag + 2 * dy), (z_mag + 2 * dz)])

    # Restored to original position.
    res = resized
    if auto_center:
        res = resized.translate([-dim for dim in move_vector_used])
    return res

def __old__axis_aligned(solid, axis = [0, 0, 1], mn = None, mx = None):
    '''
    DEPRECATED.
    Generalized bounding box aligner. Defaults to positive z-axis.
    Works for negative axis for "below" alignment.
    Will downscale with fractions in axis, but that's not necessarily intended.
    '''
    if not mn or not mx:
        mn, mx = bounding_box(solid)

    if any([abs(a) > 1 for a in axis]):
        raise Exception("Each axis argument must be in the inclusive range of [-1, 1]")

    # Move the solid in the positive direction of the axis, such that the minimum bounds touch the axis zeroes.
    ops = (
        lambda s, minimums: s.right(-minimums),
        lambda s, minimums: s.back(-minimums),
        lambda s, minimums: s.up(-minimums),
    )

    # Move the solid in the negative direction of the axis, such that the maximum bounds touch the axis zeroes.
    neg_ops = (
        lambda s, maximums: s.left(maximums),
        lambda s, maximums: s.front(maximums),
        lambda s, maximums: s.down(maximums),
    )

    res = solid
    for op, neg_op, minimums, maximums, ax in zip(ops, neg_ops, mn, mx, axis):
        res = op(res, minimums * ax) if ax >= 0 else neg_op(res, maximums * -ax)
    return res


def axis_aligned(solid, axis = [0, 0, 1], mn = None, mx = None):
    '''
    Generalized bounding box aligner. Defaults to positive z-axis.
    Works for negative axis for "below" alignment.
    Will downscale with fractions in axis, but that's not necessarily intended.
    
    Returns: [aligned_solid, move_vec]
    '''
    
    if not mn or not mx:
        mn, mx = bounding_box(solid)

    if any([abs(a) > 1 for a in axis]):
        raise Exception("Each axis argument must be in the inclusive range of [-1, 1]")

    # translate vector for the solid in the positive direction of the axis, such that the minimum bounds touch the axis zeroes.
    ops = (
        lambda s, minimums: [-minimums, 0, 0],
        lambda s, minimums: [0, -minimums, 0] ,
        lambda s, minimums: [0, 0, -minimums],
    )

    # translate vector for the solid in the negative direction of the axis, such that the maximum bounds touch the axis zeroes.
    neg_ops = (
        lambda s, maximums: [-maximums, 0, 0],
        lambda s, maximums: [0, -maximums, 0],
        lambda s, maximums: [0, 0, -maximums],
    )

    component_vectors = []
    for op, neg_op, minimums, maximums, ax in zip(ops, neg_ops, mn, mx, axis):
        partial_vec = op(solid, minimums * ax) if ax >= 0 else neg_op(solid, maximums * -ax)
        component_vectors.append(partial_vec)
        
    # reduce the component vector to final vector.
    final_move_vec = [sum(*dims) for dims in zip(component_vectors)]
    
    return [solid.translate(final_move_vec), final_move_vec]

def z_aligned(solid, mn = None, mx = None):
    '''
    Raise the whole solid above zero-z.
    It takes the lowest z vertex, and raise it so it's at zero-z.

    If the solid is in the air, put it on the ground.

    Optionally: supply mn and mx to avoid recomputing bounding box. See bounding_box() for more details.

    (Technically mx is not needed, and won't be checked. But present to keep function signature consistent with other bbox based functions).

    Returns post-translate solid.

    TODO: Upgrade to return [moved_solid, move_vec].
    '''
    # if not mn:
    #     mn, _ = bounding_box(solid)

    # _, _, z = mn
    # return solid.up(-z)

    return axis_aligned(solid, axis = [0, 0, 1], mn=mn, mx=mx)[0]

def xy_aligned(solid, mn = None, mx = None):
    '''
    Convenient function to align the solid on positive x-axis and y-axis.
    TODO: Upgrade to return [moved_solid, move_vec].
    '''
    return axis_aligned(solid, axis = [1, 1, 0], mn=mn, mx=mx)[0]

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

def z_bisect(solid, top_mask=None, epsilon=0.001):
    '''
    Horizontal chop, given (optional) top mask.
    If top mask is unspecified, xy-plane is used as the cut line.
    Return [top, bottom] after cut.
    '''
    if not top_mask:
        # Just need the xy dimensions.
        mn, mx = bounding_box(solid)

        if any(not coord for coord in (mn, mx)):
            # defensive check if there's nothing to z_bisect because solid does not span across Z plane
            raise ValueError(f"arg solid does not span across Z axis. Therefore, nothing to z_bisect(). Bounding boxes found: {mn=}, {mx=}")

        # Clock wise points
        xy_points = [
            [p - epsilon for p in mn[:2]],   # lower left
            [mn[0] - epsilon, mx[1] + epsilon],
            [p + epsilon for p in mx[:2]],   # upper right
            [mx[0] + epsilon, mn[1] - epsilon]
        ]
        top_mask = polygon(xy_points).linear_extrude(mx[2])

    top = solid & top_mask

    # To combat z-fighting: scale up the top portion.
    bottom = solid - hull(top).scale([1 + epsilon, 1 + epsilon, 1 + epsilon])
    return [top, bottom]

def y_bisect(solid, epsilon=0.001):
    '''
    Convenience alias in cutting a solid "left and right" across the Y plane.
    For more fine-grain control: DIY with z_bisect().
    '''
    left, right = z_bisect(solid.roty(90), epsilon=epsilon)
    left, right = [item.roty(-90) for item in (left, right)]
    return [left, right]

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
        mn, _ = bounding_box(bottom_solid)

        # Create a hole punch to bottom_solid, use projection(hull(top_solid) thru the height of bottom_solid.
        hole_punch = projection(hull(top_solid)).linear_extrude(bottom_solid_height)

        # Since we are full_piercing: If there's "below ground" volume, translate the hole_punch accordingly.
        if mn[-1] < 0:
            hole_punch = hole_punch.down(-mn[-1])

        bottom_solid -= hole_punch

    return top_solid | (bottom_solid - hull(top_solid))

def rolling_hull(solid, path):
    '''
    Returned the object formed by the shadow left by rolling the solid along all the coordinates on the path.
    '''
    template = center(solid)[0]
    whole_path = []
    vertices = []
    for coord in path:
        vertices.append(template.translate(coord))
        if len(vertices) >= 2:
            whole_path.append(hull(vertices[-1], vertices[-2]))

    return [union(whole_path)] + vertices

def masked_map(mask, solid, func=lambda shape: shape.scale([0.5, 0.5, 1]), auto_center=True):
    '''
    Only apply a lambda over the masked volume.

    Parameters:
        mask: mask over the solid to perform the lambda.
        solid: input solid
        func: lambda to execute on masked shape.
        auto_center: auto center the masked off shape to origin before executing func. 
            Default is True. If on, the post_op shape is restored back to original position before returning.

    Use case: fillet only the masked volume, but leave the rest alone.
    Operating_vol = Solid & mask
    Untouched = solid - operating_vol

    For demo purposes, func is preassigned to scaling 50% on xy direction. Pass in an explicit lambda for your use case.

    Returns [Apply(operating_vol), operating_vol, untouched ]. This generic form supports cases where func may be splitting the solid into multiple solids.
    '''
    operating_vol = solid & mask
    untouched = solid - operating_vol

    if auto_center:
        # Move masked shape to center before executing.
        operating_vol, move_vec = center(operating_vol)
    
    post_op = func(operating_vol)

    if auto_center:
        # Undo the movement
        undo_vec = [-d for d in move_vec]

        if isinstance(post_op, Iterable):
            # TODO: Only supports single level collections for now.
            # XXX: to keep type consistency, make sure return value is a single solid.
            # Sorry, no lazy union flexibility.
            post_op = union([item.translate(undo_vec) for item in post_op])
        else:
            post_op = post_op.translate(undo_vec)

        operating_vol = operating_vol.translate(undo_vec)

    return [post_op, operating_vol, untouched]

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

def line_magnitude(point_left, point_right):
    x1, y1 = point_left
    x2, y2 = point_right
    return ((y2 - y1) ** 2 + (x2 - x1) ** 2) ** 0.5

def midpoint(point_left, point_right):
    x1, y1 = point_left
    x2, y2 = point_right

    return (x1 + x2) / 2, (y1 + y2) / 2

def arc(arc_point_left, arc_point_mid, arc_point_right):
    '''
    Returns a "cut off" circle, containing an arc bounded by the three points above.
    The three points, if drawn, should lie on the arc.
    The minor segment is produced using Intersecting Chord Theorem.

    Returns major and minor segment. If shown together, you see a full circle.

    TODO: Live in a different lib?
    '''

    mid = midpoint(arc_point_left, arc_point_right)
    a_mid = line_magnitude(arc_point_left, mid)
    b_mid = line_magnitude(mid, arc_point_right)
    minor = line_magnitude(arc_point_mid, mid)

    # Apply intersecting chord theorem
    major = a_mid * b_mid / minor
    diam = minor + major

    # print(f"{a_mid=} {a_mid=} {mid=} {c=} {d=} {diam=}")

    # Cut out the minor segment.
    # Major segment to the left, minor segment to the right.
    whole_circle = circle(d=diam)
    whole_circle = whole_circle.right(diam/2).left(major)

    minor_segment_mask = square([diam, diam]).front(diam/2)

    minor_segment = whole_circle & minor_segment_mask
    major_segment = whole_circle - minor_segment

    return [major_segment, minor_segment, diam, major, minor]

def sphere_arc(arc_point_left, arc_point_mid, arc_point_right):
    '''
    Sphere version of arc. Gives you have cutted spheres in major and minor sections.

    Used for: making a "pill" shape for DIY fillet on joints.
    '''
    major_segment, minor_segment, diam, major, minor = arc(arc_point_left, arc_point_mid, arc_point_right)

    # shift default centered sphere to align with major/minor segment placement of arcs.
    base = sphere(d=diam).right(diam/2).left(major)

    # Make sure masks are z-centered.
    major_mask, minor_mask = [center(shape.linear_extrude(diam), axis=[0, 0, 1])[0] for shape in (major_segment, minor_segment)]
    return [base & major_mask, base & minor_mask, diam, major, minor]


def rotate_point_horizontal(pt, angle_offset_deg):
    '''
    Utility for rotating a point (x, y, z) in respect to origin on the xy plane.
    '''
    x, y, z = pt
    nx = x * math.cos(math.radians(angle_offset_deg)) - y * math.sin(math.radians(angle_offset_deg))
    ny = x * math.sin(math.radians(angle_offset_deg)) + y * math.cos(math.radians(angle_offset_deg))
    nz = z
    return [nx, ny, nz]

def add_single_brim(convex_solid, scale_factor=1.2, height=0.2):
    '''
    Assume solid is already z-aligned.
    Adds a thin brim over the solid's footprint.

    Why: prusaslicer only supports outer and inner brim, but not brim over "intermediate" foot print that isn't the inner or outer most perimeter.

    This utility applies brim on a uni-convex solid (don't do this to a unioned object that is disjointed in space). This is due to the limitation of scaling. On disjointed objects...the brim would be dislocated from the actual contact point to the build plate.
    '''
    # Relocate to origin for scaling
    tmp, move_vec = center(convex_solid, axis=[1, 1, 0])
    brim = tmp.projection(True).scale([scale_factor, scale_factor, scale_factor])
    brim = brim.linear_extrude(height)

    # Restore movement
    brim = brim.translate([-p for p in move_vec])

    return [convex_solid | brim, brim]

def debug_find_face_by_normal_vector(solid, estimated_norm_vec, num_faces=1):
    '''
    Expected usage: user uses the measure tool after render, to find the 3x1 normal vector (printed in stdout status bar) of the face they want.
    Pass that 3x1 vector, and programming this returns the face closest to the given normal vector.
    It is possible to have multiple faces with the same normal vector (or matched by magnitude delta). Arg num_faces allows returning top matches up to num_faces.
    '''

    def transformation_matrix_to_normal_vector(trans_matrix):
        '''
        Discovered this by observation via debugging.
        f.matrix from faces() -> 3rd column = normal vector.
        '''
        return [row[2] for row in trans_matrix[:3]]

    def dist(x_mag, y_mag, z_mag):
        '''
        Get scalar of the magnitude between 2 vectors.
        '''
        return math.sqrt(x_mag ** 2 + y_mag ** 2 + z_mag ** 2)

    def iterate_faces():
        '''
        Helper function to preprocess the items we need for evaluating faces in ranked order closest to arg estimated_norm_vec.
        '''
        for idx, f in enumerate(solid.faces()):
            face_normal_vector = transformation_matrix_to_normal_vector(f.matrix)
            d = dist(*magnitudes(None, mn=face_normal_vector, mx=estimated_norm_vec))
            # (face, idx, magnitude dist between estimated_norm_vec and face's norm vec)
            yield (f, idx, d)

    best_matched_faces = heapq.nsmallest(num_faces, iterate_faces(), key=lambda tup: tup[2])

    # Reformat the output to list of 3 lists: [faces], [index], [dist].
    # It's a simple transpose. Need to deref the tuples to flatten before rewrap as lists. Both arg to zip, and zip's output (which default to tuple).
    return [[*dim] for dim in zip(*best_matched_faces)]


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

    for coords in debug_face_coordinates(solid):
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


    
def simple_fillet(uni_mask, solid):
    '''
    EXPERIMENTAL.
    Apply convex smooth curves to butting edges.
    Use case: You need to round out a peg to go into a hole smoothly.
    
    Caller can union back with solid (for lazy union efficiencies).
    '''
    # Apply the hull for the masked area.
    # XXX: If auto_center=True, make sure func=union(hull(shape)).
    # Otherwise: the undo-move vector would not be "centered" per hull component.
    masked_shape, operating_vol, solid_minus_mask = masked_map(uni_mask, solid, func=lambda shape: hull(shape), auto_center=False)
    
    return [masked_shape, solid_minus_mask]

def simple_chamfer(uni_mask, solid):
    '''
    EXPERIMENTAL.
    Apply concave smooth curves to butting edges (commonly known as "chamfer").
    Use case: you need to round out a hole for a peg to go in smoothly
        Take a negative of the solid with a hole.
        Generate that peg. Hull it.
        chamfer = solid - hulled_peg.
    '''
        
    # XXX: This implementation would chamfer in the shape of the mask as well.
    # The whole chamfer RELIES on this since it hulls the peg.
    peg = uni_mask - solid
    filleted_peg, _ = simple_fillet(uni_mask, peg)
    
    post_op = solid - filleted_peg
    
    # For signature completeness only.
    solid_minus_mask = solid - peg
    
    return [post_op, solid_minus_mask]


class LappedCuts:
    '''
    Utility class encapsulating lapped cuts (e.g., dovetail, puzzle pieces).
    General recommendation: Use circular lugs for efficient prints with minimum artifacts.
    '''
    def __init__(self):
        pass

    def y_lapped_cut(self, solid, lock_mask_list, base_offset, symmetry=False, epsilon=0.001, fit_tolerance=0.02):
        '''
        Generalized function for making dovetail-like cut.
        lock_mask can be classic dovetail, circular lug, etc.
        For lazy union purposes (avoid nested union CSG tree that crashes on stack overflow): lock masks is a list.
            
        Parameters:
            solid: input solid to be dovetail cut. 
            lock_mask_list: a list of locking masks, for the locking mechanism. Should be aligned for y-cut down the center. The male part is on the left side of the cut (-x side).
            base_offset: Positive offset extending base for the "female" part of the dovetail (negative not yet supported).
            symmetry: True if you want dovetail/lug locking on both sides. Must have non-zero base_offset.
            epsilon: Optional param to combat z-fighting.
            fit_tolerance: based on your printer, the tolerance gap between the lapped cuts.
        '''
        
        if symmetry and base_offset == 0:
            raise ValueError("Symmetry is only supported with non-zero base_offset.")

        # Finishing detail: Shape the dovetail to be flushed with the input solid.
        locks = [mask & solid for mask in lock_mask_list]
        
        # Only used if symmetry=True.
        reverse_locks = [lock_mask & solid.right(base_offset).roty(180) for lock_mask in locks]
        # Restore orientation.
        reverse_locks = [reverse_lock.roty(180).left(base_offset) for reverse_lock in reverse_locks]

        
        # Preprocessing to hollow out where dovetail would sit.
        # Scale up the locks for tolerance
        # hollow = difference(solid, [lock.scale([1 + fit_tolerance, 1 + fit_tolerance, 1 + fit_tolerance]) for lock in locks])
        # hollow = difference(solid, locks)

        # Debugging: This does not need z-fighting. It means mask & solid resulted in z-fighting. Scaling is not a sufficient solution.
        # Make the diff holes bigger, for print tolerances. BUT THIS GAPS THE MALE SIDE.
        # TODO: bisect FIRST and then hollow holes, such that female side gets offset_3d+ for tolerances.
        # TODO: Make a clone of reverse_locks, but source is mask not mask & solid.
        hollow = difference(solid, [offset_3d(lock, delta=[fit_tolerance, fit_tolerance, fit_tolerance]) for lock in lock_mask_list])
        
        if symmetry:
            # hollow = difference(hollow, [lock.scale([1 + fit_tolerance, 1 + fit_tolerance, 1 + fit_tolerance]) for lock in reverse_locks])
            hollow = difference(hollow, reverse_locks)

        # Slice the bottom. Only applicable for non-zero base offset.
        top, bottom = z_bisect(hollow, epsilon=epsilon)
            
        # Cut left and right.
        left, right = y_bisect(hollow, epsilon=epsilon)
    
        # show(hollow.color('purple'))
        # return hollow
    
        # Override right with the larger base_offset.
        b_right = None
        if base_offset != 0:
            _, b_right = y_bisect(bottom.right(base_offset), epsilon=epsilon)
            b_right = b_right.left(base_offset)
            
            # Include the bottom lock (dovetail/lug) if symmetry is on.
            if symmetry:
                b_right = union(b_right, reverse_locks)
        

        # Attach dovetail to and mask the base offsets.
        # Epsilon for z-fighting.
        # male = union(left, locks)

        # XXX: This lazy union may break symmetry case when difference() is done on them.
        male = [left] + locks
        female = right

        if b_right:
            # TODO: Hull seem to fix some z-fighting issues. But won't work if symmetry=True.
            # male -= b_right.scale([1 + epsilon, 1 + epsilon, 1 + epsilon])
            male = difference(male, b_right.scale([1 + epsilon, 1 + epsilon, 1 + epsilon]))
            #male -= hull(b_right.scale([1 + epsilon, 1 + epsilon, 1 + epsilon]))
            female = union(right, b_right)
        
        return [male, female]


    def lug(self, h, lug_radius, locking_offset=None):
        '''
        Circular lug
        '''
        if locking_offset is None:
            # default
            locking_offset = 0.70 * lug_radius

        lug = cylinder(r=lug_radius, h = h)
        
        # male part will be lhs, meaning we want the locking wedge on the right.
        lug = lug.right(locking_offset)
        return lug
    
    def dovetail(self, h, dovetail_big_width, dovetail_small_width, dovetail_height):
        '''
        Helper method to create dovetail base shape.
        '''
        # trapezoid
        pts = [
            [-dovetail_big_width/2, 0], 
            [dovetail_big_width/2, 0], 
            [dovetail_small_width/2, dovetail_height], 
            [-dovetail_small_width/2, dovetail_height], 
            [-dovetail_big_width/2, 0]
        ]
        trap = polygon(pts).rotz(90).linear_extrude(h)
        trap = center(trap, axis=[1, 1, 0])[0]
        return trap
    
    def y_lug_cut(self, solid, mn, mx, lug_radius, base_offset, symmetry=False, epsilon=0.001):
        '''
        Reference function for performing a single lug cut.
        '''
        if mn is None or mx is None:
            raise ValueError('Please explicitly pass in mn and mx from bounding_box(solid).')

        _, _, h = mx
        
        # TODO: Hardcode the lug offset for now.
        lock = lug(h, lug_radius, 0.70 * lug_radius)
        return y_lapped_cut(solid, lock, base_offset=base_offset, symmetry=symmetry, epsilon=epsilon)
        