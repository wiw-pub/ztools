from openscad import *
import math, itertools

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

    def fill_cylindrical_shell(self, radius, height, shell_thickness):
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
