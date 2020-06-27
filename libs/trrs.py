
from .common import *
from .config import *


def get_trrs_holder():
    trrs_height = TRRS_H - (WALL_THICKNESS - TRRS_L + PLATE_GAP)
    x, y, t = TRRS_W / 2, trrs_height, HOLDER_THICKNESS
    return [Polygon(
        points=fold_points_y([
            Point(x, 0),
            Point(x, t),
            Point(x + t, t),
            Point(x + t, -t),
        ])
    ).translate(Vector(dy=-y))]


def get_trrs_box():
    x = TRRS_W / 2
    y = WALL_THICKNESS - TRRS_L + PLATE_GAP
    return Box(
        p1=Point(-x, y),
        p2=Point(+x, y - TRRS_H),
    )