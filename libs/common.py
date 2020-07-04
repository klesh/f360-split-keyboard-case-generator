from dataclasses import dataclass, field
from typing import List, Iterable
from collections import namedtuple
from .config import *


@dataclass
class Vector:
    dx: float = 0
    dy: float = 0
    dz: float = 0


@dataclass
class Point:
    x: float = 0
    y: float = 0
    z: float = 0

    def translate(self, v: Vector):
        return Point(self.x + v.dx, self.y + v.dy, self.z + v.dz)

    def mirror_y(self):
        return Point(-self.x, self.y, self.z)

    def __repr__(self):
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"


@dataclass
class Rect:
    p1: Point
    p2: Point

    @property
    def rx(self) -> float:
        return (self.p1.x + self.p2.x) / 2

    @property
    def ry(self) -> float:
        return (self.p1.y + self.p2.y) / 2

    @property
    def w(self) -> float:
        return abs(self.p1.x - self.p2.x)

    @property
    def h(self) -> float:
        return abs(self.p1.y - self.p2.y)

    @property
    def tr(self) -> Point:
        return Point(self.p2.x, self.p1.y)

    @property
    def br(self) -> Point:
        return self.p2

    @property
    def tl(self) -> Point:
        return self.p1

    @property
    def bl(self) -> Point:
        return Point(self.p1.x, self.p2.y)

    def translate(self, v: Vector):
        return Rect(self.p1.translate(v), self.p2.translate(v))

    def offset(self, v: float):
        return Rect(self.p1.translate(Vector(-v, +v)), self.p2.translate(Vector(+v, -v)))

    def mirror_y(self):
        return Rect(self.p1.mirror_y(), self.p2.mirror_y())


@dataclass
class Polygon:
    RECT = 1
    POLYGON = 2

    points: List[Point]
    rect: Rect

    def __init__(self, points: List[Point], rect: Rect = None):
        self.points = points
        self.rect = rect
        if not rect:
            x1, y1, x2, y2 = float("inf"), float("-inf"), float("-inf"), float("inf")
            for p in points:
                x1 = p.x if p.x < x1 else x1
                x2 = p.x if p.x > x2 else x2
                y1 = p.y if p.y > y1 else y1
                y2 = p.y if p.y < y2 else y2
            self.rect = Rect(Point(x1, y1), Point(x2, y2))

    @property
    def shape(self) -> int:
        return self.RECT if len(self.points) == 2 else self.POLYGON

    def translate(self, v: Vector):
        return Polygon([p.translate(v) for p in self.points], self.rect.translate(v))

    def mirror_y(self):
        return Polygon([p.mirror_y() for p in self.points], self.rect.mirror_y())


@dataclass
class Key:
    text: str
    rect: Rect
    hole: Polygon

    def translate(self, v: Vector):
        return Key(self.text, self.rect.translate(v), self.hole.translate(v))


@dataclass
class Layout:
    keys: List[Key] = field(repr=False)
    rect: Rect
    left: Polygon
    right: Polygon
    name: str = None
    author: str = None

    def translate(self, v: Vector):
        return Layout(
            keys=[k.translate(v) for k in self.keys],
            rect=self.rect.translate(v),
            left=self.left.translate(v),
            right=self.right.translate(v),
            name=self.name,
            author=self.author,
        )


def rxry_to_xyxy(rx, ry, w, h):
    return rx - w / 2, ry + h / 2, rx + w / 2, ry - h / 2


def fold_points_y(points: List[Point]):
    return points + [p.mirror_y() for p in reversed(points)]


def offset_points(points, dx):
    result = [points[0].translate(Vector(dx=dx))]
    for i in range(0, len(points) - 2, 2):
        p1, p2, p3 = points[i:i+3]
        dy = 0
        if p1.x == p2.x:
            dy=-dx if (p3.x - p2.x) < 0 else dx
        v = Vector(dx, dy)
        result.append(p2.translate(v))
        result.append(p3.translate(v))
    if len(points) % 2 == 0:
        result.append(points[-1].translate(Vector(dx=dx)))
    return result


def solve_intercept(x1, y1, x2, y2):
    return (x1 * y2 - x2 * y1) / (x1 - x2)