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

        # x_offset shifts the honeycomb hexagon corner-to-corner, but need to reduce by the hexagon's wing obtuse triangle height.
        # wing obtuse triangle height = radius * cos(60)
        wing_obtuse_triangle_height = self.outer_radius * math.cos(math.radians(60))
        x_offset, y_offset = (self.outer_radius * 2 - wing_obtuse_triangle_height), self.perpendicular_angle() * self.outer_radius
        b = a.translate([x_offset, y_offset, 0])
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

        # reposition to quadrant 1.
        shell = shell.translate([self.outer_radius, self.outer_radius * self.perpendicular_angle(), 0])
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

        for xx, yy in itertools.product(range(x_bound), range(y_bound)):
            shell, x_off, y_off = self.pair()
            sheet.append(shell.translate([x_off * xx, y_off * yy, 0]))
            
        return mask & union(sheet) if not only_raw else union(sheet)

    
    def face_shell(self, solid, enable_border=True):
        '''
        Apply honeycomb perforated mesh on every face of the solid.

        Prerequisites:
            Requires skin() feature to be ENABLED in Edit > Preferences > Features.
            Requires nimport('https://raw.githubusercontent.com/willywong/ztools/refs/heads/main/src/ztools.py')
        
        TODO: create a honeycomb_example.py to showcase its usage.
        '''
        # Identity matrix.
        IDENT = cube(1).origin.copy()

        thickness = self.thickness

        shell_faces = []
        borders = []
        for i, f in enumerate(solid.faces()):
            # Track the move vector from origin.
            # This is important to "restore" orientation after manipulation at the origin.
            orientation = f.matrix

            # Faces inward for origin manipulation (negative Z; below ground).
            # Since we want the final mesh to extrude "inward".
            # This face_3d will be used as a mask on the honeycomb sheet to get the correct face.
            face_3d = f.linear_extrude(-thickness)

            # IMPORTANT: Handle to restore back to original position at the end.
            face_3d.orig = IDENT

            # Move to origin. This will be centered by default (thank you skin()).
            flat_face_3d = face_3d.align(IDENT, orientation)

            # Get the dimensions to apply honeycomb
            # magnitudes() from ztools.
            # center() from ztools.
            x_mag, y_mag, z_mag = zt.magnitudes(flat_face_3d)
            replacement_face_3d = zt.center(self.fill_sheet(x_mag, y_mag).linear_extrude(thickness))[0]

            # Make sure the honeycomb sheet is "below ground" to have final shape extrude inward.
            replacement_face_3d = replacement_face_3d.down(thickness/2)

            # Intersect the volume to "fit" the rectangular honeycomb sheet to the face dimensions.
            # Necessary for non-rectangular faces.
            replacement_face_3d &= flat_face_3d


            # If border is enabled: prep the border to be unioned later.
            if enable_border:                
                # NOTE: Because the face will be flat on xy-plane with no Z difference, we only need to shrink in xy directions.
                inner = zt.offset_3d(flat_face_3d, delta=[-thickness, -thickness, 0])

                border = flat_face_3d - inner
        
                # For debugging: add the border to collection.
                borders.append(border)
        
                # Apply the border.
                replacement_face_3d |= border


            # Restored to original orientation
            modified_face_3d = replacement_face_3d.align(IDENT, flat_face_3d.orig)

            shell_faces.append(modified_face_3d)

        # union all
        shell = functools.reduce(lambda x, y: x | y, shell_faces)
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
