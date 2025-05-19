from openscad import *

import os

def load_openscad_thirdparty_lib():
    LIB_PATH = rf'C:\Users\{os.getlogin()}\Documents\OpenSCAD\libraries'

    if LIB_PATH not in sys.path:
        sys.path.append(LIB_PATH)

load_openscad_thirdparty_lib()

nimport('https://raw.githubusercontent.com/wiw-pub/ztools/refs/heads/main/src/honeycomb.py')
nimport('https://raw.githubusercontent.com/wiw-pub/ztools/refs/heads/main/src/ztools.py')


'''
Demoing honeycomb.py, a work-in-progress lib using pythonscad to apply honeycomb mesh.

Rendered examples at https://imgur.com/a/UamhF6Y
'''

# Honeycomb utility object. Radius of a single honeycomb and thickness of honeycomb cells are instance properties.
# User can instantiate multiple honeycomb objects for different settings.
hcomb = Honeycomb(outer_radius=6, thickness=1)


# Feature 1: 2d rectangular sheet of honeycombs.

# Note, this does not look right until you render with F6.
rectangle_2d_honeycomb = hcomb.fill_sheet(50, 50)

# 3d sheet of honeycombs.
rectangle_3d_honeycomb = rectangle_2d_honeycomb.linear_extrude(6)


# Feature 2: Given a solid, honeycomb pattern its faces.
box = z_aligned(cube([50, 50, 50], center=True))
box_shell = hcomb.face_shell(box, extrude_thickness=2, enable_border=True)[0]


# Limitations: Does not work well for cylindrical solids, where the faces are joined at angles.
# TBD whether there is a generalized solution to this.
sph = sphere(r=60, fn=10)
sph_shell = hcomb.face_shell(sph, extrude_thickness=1, enable_border=True)[0]

corner_box = cube([50, 50, 50]) - cube([40, 40, 40])
corner_box_shell = hcomb.face_shell(corner_box, extrude_thickness=1, enable_border=True)[0]

# Feature 3: wrap a sheet over a cylinder.
# There IS another way for cylindrical solids using wrap().
radius = 30
circumference = 2 * radius * math.pi
vertical_sheet = hcomb.fill_sheet(circumference, 50).linear_extrude(2).rotx(90)
wrapped_cylinder = vertical_sheet.wrap(r=radius)

to_show = [rectangle_3d_honeycomb, box_shell, sph_shell, corner_box_shell, wrapped_cylinder]
show([item.right(idx * 120) for idx, item in enumerate(to_show)])