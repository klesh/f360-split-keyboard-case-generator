import adsk.core, adsk.fusion
from typing import Iterable
from .libs.common import *


def translate_point(point: adsk.core.Point3D, dx=0, dy=0, dz=0):
    copied = point.copy()
    copied.translateBy(adsk.core.Vector3D.create(dx, dy, dz))
    return copied

def translate_points(points: List[adsk.core.Point3D], dx=0, dy=0, dz=0):
    return [translate_point(p, dx=dx, dy=dy, dz=dz) for p in points]

def add_point(sketch: adsk.fusion.Sketch, point: Point):
    point = adsk.core.Point3D.create(point.x, point.y, point.z)
    return sketch.sketchPoints.add(point)

def add_center_point_of_bounding_box(sketch: adsk.fusion.Sketch, boundingBox: adsk.core.BoundingBox3D):
    return add_point(sketch, Point(
        (boundingBox.minPoint.x + boundingBox.maxPoint.x) / 2,
        (boundingBox.minPoint.y + boundingBox.maxPoint.y) / 2,
        (boundingBox.minPoint.z + boundingBox.maxPoint.z) / 2,
    ))

def add_box(sketch: adsk.fusion.Sketch, box: Box):
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        add_point(sketch, box.p1),
        add_point(sketch, box.p2),
    )

def add_circle(sketch: adsk.fusion.Sketch, center: Point, radius: float):
    sketch.sketchCurves.sketchCircles.addByCenterRadius(
        add_point(sketch, center),
        radius
    )

def connect_points(sketch, points, close=False):
    points = [add_point(sketch, point) for point in points]
    l = len(points)
    lines = map(lambda i: (points[i], points[(i + 1) % l]), range(l if close else l - 1))
    return [
        sketch.sketchCurves.sketchLines.addByTwoPoints(p1, p2)
        for p1, p2 in lines
    ]
        

def add_polygon(sketch, polygon: Polygon):
    points = polygon.points
    if polygon.shape == Polygon.BOX:
        return add_box(sketch, Box(*points))
    connect_points(sketch, points, True)

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
    return sorted(body.faces, key=lambda f: (f.area, f.centroid.z, f.centroid.y, f.centroid.x))