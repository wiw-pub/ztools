from openscad import *
import itertools

nimport('https://raw.githubusercontent.com/wiw-pub/ztools/refs/heads/main/src/ztools.py')

fn = 100

a = cube(50, center='00<')

lc = LappedCuts()

locking_lug = lc.lug(h=50, lug_radius=2).color('red')

multi_lugs = itertools.chain.from_iterable([[locking_lug.back(i * 5), locking_lug.front(i * 5)] for i in range(5)])

left_piece, right_piece = lc.y_lapped_cut(a, lock_mask_list=multi_lugs, base_offset=0)

show([left_piece.left(10), right_piece.right(10)])