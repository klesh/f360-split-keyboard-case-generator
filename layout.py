import json
from typing import List, Dict


# x, y : screen coordinate
# cx, cy: cartesian coordinate
# rx, ry: certesian radius center

U: int = 19  # 1U = 14mm
STB_HOLE_DX = 11.9
STB_HOLE_DY = 0.62
SIDE_NOTCH_DX = 15.66
SIDE_NOTCH_DY = 0.9
BOTT_NOTCH_DX = STB_HOLE_DX
BOTT_NOTCH_DY = 7.37


class Hole:
    def __init__(
        self,
        points: List[tuple], # outer shape
        cx1: float,
        cy1: float,
        cx2: float,
        cy2: float,
    ):
        self.points = points
        self.cx1 = cx1
        self.cy1 = cy1
        self.cx2 = cx2
        self.cy2 = cy2

    def origin(self, rx: float, ry: float):
        return Hole(
            [(rx + x, ry + y) for x, y in self.points],
            rx + self.cx1,
            ry + self.cy1,
            rx + self.cx2,
            ry + self.cy2,
        )

    def __str__(self):
        return f"Hole({self.cx1}, {self.cy1}, {self.cx2}, {self.cy2}, total_points={len(self.points)})"

class HoleCreator:
    def __init__(
        self,
        size: float = 14.1,
        stb_w: float = 7.1,  # 6.65
        stb_h: float = 13.4,  # 12.3
        side_notch_w: float = 1,
        side_notch_h: float = 2.9, # 2.8
        bott_notch_w: float = 3.1, # 3.0
        bott_notch_h: float = 1.3, # 1.2
    ):
        self.size = size
        self.stb_w = stb_w
        self.stb_h = stb_h
        self.side_notch_w = side_notch_w
        self.side_notch_h = side_notch_h
        self.bott_notch_w = bott_notch_w
        self.bott_notch_h = bott_notch_h
        self.hole_1u = self.create_std_holes()
        self.hole_2u = self.create_std_holes(True)

    def create(self, rx: float, ry: float, uw: float, uh: float):
        hole = self.hole_2u if uw > 1.75 else self.hole_1u
        return hole.origin(rx, ry)

    @staticmethod
    def rxrywh_to_xyxy(rx, ry, w, h):
        x1 = rx - w / 2
        x2 = rx + w / 2
        y2 = ry - h / 2
        y1 = ry + h / 2
        return x1, y1, x2, y2

    def create_std_holes(self, is_2u=False):
        # align hole center with cartesian origin, draw right part then mirror to left, lastly, move orgin to rx,ry
        key_x1, key_y1, key_x2, key_y2 = self.rxrywh_to_xyxy(
            0, 0, self.size, self.size
        )
        points = [
            (key_x2, key_y1),
            (key_x2, key_y2),
        ]
        bounding = (key_x1, key_y1 + 0.5, key_x2, key_y2 - 0.5)
        if is_2u:
            stb_x1, stb_y1, stb_x2, stb_y2 = self.rxrywh_to_xyxy(
                STB_HOLE_DX, -STB_HOLE_DY, self.stb_w, self.stb_h
            )
            snot_x1, snot_y1, snot_x2, snot_y2 = self.rxrywh_to_xyxy(
                SIDE_NOTCH_DX,
                SIDE_NOTCH_DY,
                self.side_notch_w,
                self.side_notch_h,
            )
            bnot_x1, bnot_y1, bnot_x2, bnot_y2 = self.rxrywh_to_xyxy(
                BOTT_NOTCH_DX,
                -BOTT_NOTCH_DY,
                self.bott_notch_w,
                self.bott_notch_h,
            )
            points = [
                # initial
                (key_x2, key_y1),
                # canal top
                (key_x2, stb_y1 - 2),
                (stb_x1, stb_y1 - 2),
                # stablizer top
                (stb_x1, stb_y1),
                (stb_x2, stb_y1),
                # stableizer side notch
                (stb_x2, snot_y1),
                (snot_x2, snot_y1),
                (snot_x2, snot_y2),
                (stb_x2, snot_y2),
                # stablizer bottom
                (stb_x2, stb_y2),
                # stablizer bottom notch
                (bnot_x2, stb_y2),
                (bnot_x2, bnot_y2),
                (bnot_x1, bnot_y2),
                (bnot_x1, stb_y2),
                (stb_x1, stb_y2),
                # canal bottom
                (stb_x1, key_y2 + 2),
                (key_x2, key_y2 + 2),
                # end
                (key_x2, key_y2),
            ]
            bounding = (-snot_x2, key_y1 + 0.5, snot_x2, key_y2 - 3.3)
        points = points + [(-x, y) for x, y in reversed(points)]
        return Hole(points, *bounding)


class Key:
    def __init__(
        self,
        caption: str,
        row: int,
        col: int,
        x: int,
        y: int,
        prop: Dict = None,
    ):
        self.caption = caption
        self.row = row
        self.col = col
        # screen coordinate
        self.x = x
        self.y = y
        self.uw = prop.get("w", 1) if prop else 1
        self.uh = prop.get("h", 1) if prop else 1
        self.w = self.uw * U
        self.h = self.uh * U
        # cartesian coordinate
        self.cx1 = None
        self.cy1 = None
        self.cx2 = None
        self.cy2 = None
        self.hole = None

    def __str__(self):
        return f"Key({self.cx1}, {self.cy1}, {self.cx2}, {self.cy2}, caption={repr(self.caption)}, row={self.row}, col={self.col}, uw={self.uw}, uh={self.uh})"


class Layout:
    keys: List[Key]

    def __init__(self, grid: Dict):
        self.keys = []
        self.w = 0
        self.h = 0
        meta = {}
        # generate keys on screen coordinate system
        i, j = 0, 0
        x, y = 0.0, 0.0
        prop = None
        for r in grid:
            if isinstance(r, dict):
                meta = r
                continue
            for c in r:
                if isinstance(c, dict):
                    prop = c
                    continue
                key = Key(c, i, j, x, y, prop)
                x += key.w
                self.keys.append(key)
                prop = None
                j += 1
            if x > self.w:
                self.w = x
            x, j = 0, 0
            y += (
                1 * U
            )  # 1 should be replaced by minimum unit height of current row
            i += 1
        self.h = y
        self.author = meta.get("author")
        self.backcolor = meta.get("backcolor")
        self.background = meta.get("background")
        self.name = meta.get("name")
        self.notes = meta.get("notes")
        self.radii = meta.get("radii")
        self.switchBrand = meta.get("switchBrand")
        self.switchMount = meta.get("switchMount")
        self.switchType = meta.get("switchType")

        hole_creator = HoleCreator()
        for key in self.keys:
            # move keys to center for cartesion coordinate
            key.cx1 = key.x - self.w / 2
            key.cy1 = -key.y + self.h / 2
            key.cx2 = key.cx1 + key.w
            key.cy2 = key.cy1 - key.h
            # create key hole base on center point/width/height
            key.hole = hole_creator.create(
                key.cx1 + key.w / 2, key.cy1 - key.h / 2, key.uw, key.uh
            )
        self.cx1 = -self.w / 2 - 5
        self.cy1 = self.h / 2 + 5
        self.w += 10
        self.h += 10
        self.cx2 = self.cx1 + self.w
        self.cy2 = self.cy1 - self.h

    def __str__(self):
        return f"Layout({self.cx1}, {self.cy1}, {self.cx2}, {self.cy2}, name={repr(self.name)}, author={self.name}, total_keys={len(self.keys)})"

    @classmethod
    def from_file(cls, filepath: str):
        with open(filepath) as f:
            return cls(json.load(f))


if __name__ == "__main__":
    layout = Layout.from_file(r"C:\Users\Klesh\Desktop\ks63\ks-63.json")
    for key in layout.keys:
        print(key, key.hole)
    print(layout)
