from openscad import *
import math, itertools, copy, functools

# Prerequisites: Requires skin() feature to be ENABLED in Edit > Preferences > Features.

# Users: 
#   Ensure your sys.path has access to ztools.py and this file.
#   At your top level pythonscad script, use nimport() on both ztools.py and honeycomb.py.
#   README.md has more info in the github repo that contains this file.
import ztools as zt

class Honeycomb:
    '''
    Lib for patterning a surface as hexagonal honeycomb.

    Main usage: Apply a fill on a 2d sheet via fill_sheet().
    '''
    def __init__(self, outer_radius=6, thickness=2):
        # Hexagon outer radius
        self.outer_radius = outer_radius

        # Thickness of the hexagonal cell border.
        self.thickness = thickness

    def perpendicular_angle(self):
        '''
        Private utility method for finding perpendicular angle.
        '''
        return math.cos(math.radians(30))

    def pair(self, hole=False):
        '''
        Stitch two honeycombs together. It's not perfectly congruent but practically close enough.
        '''
        a = self.single(hole)


        # Old implementation: hex side is aligned on x-axis
        '''
        # x_offset shifts the honeycomb hexagon corner-to-corner, but need to reduce by the hexagon's wing obtuse triangle height.
        # wing obtuse triangle height = radius * cos(60)
        wing_obtuse_triangle_height = (self.outer_radius) * math.cos(math.radians(60))
        x_offset, y_offset = (self.outer_radius * 2 - self.thickness - wing_obtuse_triangle_height), self.perpendicular_angle() * (self.outer_radius - self.thickness/2)
        b = a.translate([x_offset, y_offset, 0])
        res = a | b
        '''
        
        # center to corner
        inner_corner_radius = -self.thickness + self.outer_radius
        
        # center to side
        inner_side_radius = inner_corner_radius * math.cos(math.radians(180/6))
        
        outer_side_radius = self.outer_radius * math.cos(math.radians(180/6))
        
        # Double the center-to-side radius will get you edge-to-edge stack.
        # Subtract the thickness for overlap. But wait: thickness is based on corner radius. Take a sin.
        dist_r = (outer_side_radius * 2) - (2 * self.thickness * math.sin(math.radians(180/6)))
        x_offset, y_offset = dist_r * math.cos(math.radians(2 * 180/6)), dist_r * math.sin(math.radians(2 * 180/6))
        b = a.translate([x_offset, y_offset, 0]).color('red')
        res = a | b

        # Also return offset distances.
        return res, 2 * x_offset, 2 * y_offset

    def single(self, hole=False):
        """
        Singular honeycomb.
        """
        c = circle(r=self.outer_radius, fn=6)
        inner = c.offset(r=-self.thickness, fn=6)
        shell = c - inner if not hole else inner

        # New implementation: hex is "standing" on a corner on x-axis.
        shell = shell.rotz(360/6/2)
        shell = projection(zt.axis_aligned(shell.linear_extrude(1), [1, 1, 0])[0])

        # Old implementation: hex side is aligned on x-axis.
        # reposition to quadrant 1.
        #shell = shell.translate([self.outer_radius, self.outer_radius * self.perpendicular_angle(), 0])
        return shell

    def fill_sheet(self, x, y, only_raw=False):
        """
        Fill a 2d sheet of x wide, y height with honeycombs.

        By default, the size is trimmed to the bounding sheet of dimensions x and y.
        """

        mask = square([x, y])

        # Upper bound generate combs.
        # X bounds: ceil(x / self.outer_radius)
        # Y bounds = ceil(y / (math.cos(math.radians(30))/outer_radius))

        d = 2 * self.outer_radius
        sheet = []
        x_bound = math.ceil(x / d)
        y_bound = math.ceil(y / (self.perpendicular_angle() * d))

        shell, x_off, y_off = self.pair()
        for xx, yy in itertools.product(range(x_bound), range(y_bound)):
            sheet.append(shell.translate([x_off * xx, y_off * yy, 0]))
            
        return mask & union(sheet) if not only_raw else union(sheet)

    
    def face_shell(self, solid, extrude_thickness, enable_border=True):
        '''
        Apply honeycomb perforated mesh on every face of the solid.

        Prerequisites:
            Requires skin() feature to be ENABLED in Edit > Preferences > Features.
            Requires nimport('https://raw.githubusercontent.com/willywong/ztools/refs/heads/main/src/ztools.py')
        
        TODO: create a honeycomb_example.py to showcase its usage.
        '''

        shell_faces = []
        borders = []
        for i, f in enumerate(solid.faces()):
            # Track the move vector from origin.
            # This is important to "restore" orientation after manipulation at the origin.
            orientation = f.matrix

            # Note: do not do negative extrude_thickness. Render does not perform well.
            # We want the final mesh to extrude "inward".
            # To have faces extrude inward (negative Z; below ground), shift .down() after transform the face to origin for manipulation.
            face_3d = f.linear_extrude(extrude_thickness)

            # Move to origin. This will be centered by default (thank you skin()).
            #flat_face_3d = face_3d.align(IDENT, orientation).down(extrude_thickness)
            flat_face_3d = face_3d.divmatrix(orientation).down(extrude_thickness)

            # Get the dimensions to apply honeycomb
            # magnitudes() from ztools.
            # center() from ztools.
            x_mag, y_mag, _ = zt.magnitudes(flat_face_3d)

            # Hack: For some triangles, the x_mag, y_mag gets cut off. 2x it as a quick hack to ensure honeycomb sheet can encompass the whole face.
            replacement_face_3d = zt.center(self.fill_sheet(x_mag * 2, y_mag * 2).linear_extrude(extrude_thickness))[0]

            # Make sure the honeycomb sheet is "below ground" to have final shape extrude inward.
            replacement_face_3d = replacement_face_3d.down(extrude_thickness/2)

            # Intersect the volume to "fit" the rectangular honeycomb sheet to the face dimensions.
            # Necessary for non-rectangular faces.
            replacement_face_3d &= flat_face_3d


            def old_border_impl(replacement_face_3d, flat_face_3d):
                # NOTE: Because the face will be flat on xy-plane with no Z difference, we only need to shrink in xy directions.
                # Learning from /u/gadget3D: larger "cut" mask fixes z-fighting. Make delta-z positive, not zero.
                inner = zt.offset_3d(flat_face_3d, delta=[-extrude_thickness, -extrude_thickness, extrude_thickness])

                border = flat_face_3d - inner
        
                # For debugging: add the border to collection.
                borders.append(border)
        
                # Apply the border.
                return replacement_face_3d | border
            
            def new_border_impl(replacement_face_3d, flat_face_3d):
                '''
                From /u/gadget3D's suggestion to fix z-fighting??
                '''
                # The over extrusion on the cut fixes z-fighting problems.
                border_cut = flat_face_3d.projection().offset(-extrude_thickness).linear_extrude(extrude_thickness*3).down(1.5*extrude_thickness)
                border_frame = flat_face_3d - border_cut
                return replacement_face_3d | border_frame

            # If border is enabled: prep the border to be unioned later.
            if enable_border:                
                replacement_face_3d = old_border_impl(replacement_face_3d, flat_face_3d)
                #replacement_face_3d = new_border_impl(replacement_face_3d, flat_face_3d)


            # Restored to original orientation
            # Do multmatrix (instead of align()), so it ignores the .down() I performed after inverse align() with f.matrix (divmatrix).
            modified_face_3d = replacement_face_3d.multmatrix(orientation)
            shell_faces.append(modified_face_3d)

        # union all
        shell = union(shell_faces)
        return [shell] + shell_faces + borders

    def deprecated_fill_cylindrical_shell(self, radius, height, shell_thickness):
        """
        A cylindrical shell of hexes.
        Classic openscad way.
        Superceded by PythonScad's wrap() function.
        """

        # Place a hexagon "standing up" at a dist from origin. Take a difference from self.pair() and extrude into 3d.
        # Produce a ring of these hexagons.
        # Produce another ring with staggered offset.
        # Repeat.
        # Do a cylinder difference.

        def perfect_holes():
            """
            Holes and some junk. If you intersect them during usage, it should be fine.
            """
            #s = self.fill_sheet(self.outer_radius * 2, self.outer_radius, only_raw=True)
            s, _, _ = self.pair(hole=True)
#            mask = square([self.outer_radius * 4, self.outer_radius * 3]).front(self.outer_radius).rotz(30)
#            holes = (mask - s) & hull(s)            
#            return holes
            return s
        

        def ring_holes():
            _, x_offset, y_offset = self.pair()

            holes_3d = perfect_holes().linear_extrude(shell_thickness * 2)
            holes_3d_centers = holes_3d.left(x_offset/2 + self.thickness)

            # Offset the radius distance, but make sure the extrude points 'inward'.
            pre_ring = holes_3d_centers.rotx(90).rotz(90).right(radius - shell_thickness)

            # Need some math to calculate the angle to rotz, since it is based off of radius (cord distance calculation).
            # Just do triangle math. tan() would do.
            
            ang_radian = math.atan2(x_offset, radius)
            ang_deg = math.degrees(ang_radian)
            
            floor_limit = int(360 // ang_deg)
            ring = []
            for i in range(floor_limit):
                ring.append(pre_ring.rotz(i * ang_deg))

            return union(ring)


        def column_holes():
            _, x_offset, y_offset = self.pair()
            height_limit = math.ceil(height/y_offset)
            column = []
            for j in range(height_limit):
                column.append(ring_holes().up(j * y_offset))

            return union(column)

        return column_holes()