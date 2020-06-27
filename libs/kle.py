import json
from .common import *
from .config import *

# create standard holes
x = y = HOLE_SIZE / 2
hole_1u = Polygon(
    points=[
        Point(-x, +y),
        Point(+x, -y),
    ],
    box=Box(
        Point(-x, +y + 0.5*MM),
        Point(+x, -y - 0.5*MM),
    )
)

stb_x1, stb_y1, stb_x2, stb_y2 = rxry_to_xyxy(STB_HOLE_DX, -STB_HOLE_DY, STB_HOLE_W, STB_HOLD_H)
noh_x1, noh_y1, noh_x2, noh_y2 = rxry_to_xyxy(SIDE_NOTCH_DX, SIDE_NOTCH_DY, SIDE_NOTCH_W, SIDE_NOTCH_H)
bot_x1, bot_y1, bot_x2, bot_y2 = rxry_to_xyxy(BOTT_NOTCH_DX, -BOTT_NOTCH_DY, BOTT_NOTCH_W, BOTT_NOTCH_H)

hole_2u = Polygon(
    points=fold_points_y([
        Point(+x, +y),                  # key hole tr
        Point(+x, +y - 3*MM),           # canal tl
        Point(stb_x1, +y - 3*MM),       # canal tr
        Point(stb_x1, stb_y1),          # stablizer tl
        Point(stb_x2, stb_y1),          # stablizer tr
        Point(stb_x2, noh_y1),          # side notch tl
        Point(noh_x2, noh_y1),          # side notch tr
        Point(noh_x2, noh_y2),          # side notch br
        Point(stb_x2, noh_y2),          # side notch bl
        Point(stb_x2, stb_y2),          # stablizer br
        Point(bot_x2, stb_y2),          # bottom notch tr
        Point(bot_x2, bot_y2),          # bottom notch br
        Point(bot_x1, bot_y2),          # bottom notch bl
        Point(bot_x1, stb_y2),          # bottom notch tl
        Point(stb_x1, stb_y2),          # stablizer bl
        Point(stb_x1, stb_y2 + 3*MM),   # canal br
        Point(+x, stb_y2 + 3*MM),       # canal bl
        Point(+x, -y),                  # key hole br
    ]),
    box=Box(
        Point(-noh_x2, +y + 0.5*MM),
        Point(+noh_x2, -y - 3.3*MM),
    )
)


def from_json(data: dict) -> Layout:

    # calculate in screen coordinate
    keys = []
    y = 0
    u = {}
    meta = {}
    for row in data:
        if isinstance(row, dict):
            meta = row
            continue
        x = 0
        for key in row:
            if isinstance(key, dict):
                u = key
                continue
            uw, uh = u.get('w', 1), u.get('h', 1)
            w, h = uw * U, uh * U
            box = Box(Point(x, y), Point(x + w, y - h))
            k = Key(
                text=key,
                box=box,
                hole=(hole_1u if uw < 2 else hole_2u).translate(Vector(box.rx, box.ry))
            )
            keys.append(k)
            u = {}
            x += w
        y -= h
    box = Box(Point(0, 0), Point(x, y)).offset(3*MM)
    return Layout(keys, box, meta.get('name'), meta.get('author')).translate(Vector(- x / 2, - y / 2))


def from_file(file_path: str) -> Layout:
    with open(file_path) as f:
        return from_json(json.load(f))

