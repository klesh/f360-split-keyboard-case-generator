from .common import *
from .config import *


def get_promicro_holder():
    pcb_height = PROMICRO_H - (WALL_THICKNESS - USB_L + PLATE_GAP)
    x, y, t = PROMICRO_W / 2, pcb_height, HOLDER_THICKNESS
    bottom_clamp = Polygon(
        points=fold_points_y([
            Point(x, 0),
            Point(x, t),
            Point(x + t, t),
            Point(x + t, -t),
        ])
    ) 
    rnub = Polygon(
        points=[
            Point(x, 0),
            Point(x + t, -t)
        ]
    )
    lnub = rnub.mirror_y()
    return [
        lnub,
        rnub,
        bottom_clamp.translate(Vector(dy=-y))
    ]

def get_promicro_boxes():
    x1, x2 = PROMICRO_W / 2, USB_W / 2
    y = WALL_THICKNESS - USB_L + PLATE_GAP
    return (
        Box(Point(-x1, y), Point(x1, y - PROMICRO_H)),
        Box(Point(-x2, y), Point(x2, y - USB_L)),
    )