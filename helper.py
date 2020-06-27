import adsk.core, adsk.fusion
from typing import Iterable
from .libs.common import *


def translate_point(point: adsk.core.Point3D, dx=0, dy=0, dz=0):
    copied = point.copy()
    copied.translateBy(adsk.core.Vector3D.create(dx, dy, dz))
    return copied

def add_point(sketch: adsk.fusion.Sketch, point: Point):
    point = adsk.core.Point3D.create(point.x, point.y, point.z)
    return sketch.sketchPoints.add(point)

def add_box(sketch: adsk.fusion.Sketch, box: Box):
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        add_point(sketch, box.p1),
        add_point(sketch, box.p2),
    )

def add_polygon(sketch, polygon: Polygon):
    points = polygon.points
    if polygon.shape == Polygon.BOX:
        return add_box(sketch, Box(*points))
    l = len(points)
    points = [add_point(sketch, point) for point in points]
    lines = map(lambda i: (points[i], points[(i + 1) % l]), range(l))
    for p1, p2 in lines:
        sketch.sketchCurves.sketchLines.addByTwoPoints(p1, p2)

def to_collection(entities):
    coll = adsk.core.ObjectCollection.create()
    for entity in entities:
        coll.add(entity)
    return coll

def sorted_profiles(sketch: adsk.fusion.Sketch):
    return sorted(sketch.profiles, key=lambda p: p.areaProperties().area)

def sorted_vertices(face: adsk.fusion.BRepFace):
    return sorted(face.vertices, key=lambda v: (v.geometry.z, v.geometry.y, v.geometry.x))

def sorted_faces(body: adsk.fusion.BRepBody):
    return sorted(body.faces, key=lambda f: f.area)