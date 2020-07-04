
from .common import *
from .config import *


def get_trrs_holder():
    trrs_height = TRRS_H - (WALL_THICKNESS - TRRS_L + PLATE_GAP)
    x, y, t = TRRS_W / 2, -trrs_height, HOLDER_THICKNESS
    return [Polygon(
        points=fold_points_y([
            Point(x, y),
            Point(x, 0),
            Point(x + t, 0),
            Point(x + t, y-t),
        ])
    )]


def get_trrs_rect():
    x = TRRS_W / 2
    y = WALL_THICKNESS - TRRS_L + PLATE_GAP
    return Rect(
        p1=Point(-x, y),
        p2=Point(+x, y - TRRS_H),
    )