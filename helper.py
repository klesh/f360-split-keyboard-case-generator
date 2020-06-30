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
    points = [add_point(sketch, point) for point in points]
    connect_points(sketch, points, True)

def add_tangent_circle(sketch, point: adsk.fusion.SketchPoint, radius: float):
    line1, line2 = point.connectedEntities
    other_point = lambda l: l.startSketchPoint if l.startSketchPoint != point else l.endSketchPoint
    p1, p2 = other_point(line1), other_point(line2)
    center = adsk.core.Point3D.create(
        (p1.geometry.x + p2.geometry.x) / 2,
        (p1.geometry.y + p2.geometry.y) / 2,
        (p1.geometry.z + p2.geometry.z) / 2
    )
    sketch.sketchCurves.sketchCircles.addByTwoTangents(line1, line2, radius, center)

def to_collection(entities):
    coll = adsk.core.ObjectCollection.create()
    for entity in entities:
        coll.add(entity)
    return coll

def sorted_profiles(profiles):
    return sorted(profiles, key=lambda p: p.areaProperties().area)

def sorted_points(points):
    return sorted(points, key=lambda p: (p.geometry.z, p.geometry.y, p.geometry.x))

def sorted_faces(faces):
    return sorted(faces, key=lambda f: (f.area, f.centroid.z, f.centroid.y, f.centroid.x))

def sorted_bodies(bodies):
    return sorted(bodies, key=lambda b: (
        b.volume,
        b.physicalProperties.centerOfMass.z,
        b.physicalProperties.centerOfMass.y,
        b.physicalProperties.centerOfMass.x,
    ))

def get_line_center_tuple(line):
    p1, p2 = line.startSketchPoint.geometry, line.endSketchPoint.geometry
    return (p1.x + p2.x) / 2, (p1.y + p2.y) / 2, (p1.z + p2.z) / 2

def sorted_lines(lines):
    return sorted(lines, key=lambda l: get_line_center_tuple(l)[::-1])

def get_profile_entities(profile, is_outer=None, object_type=None):
    curves = []
    for loop in profile.profileLoops:
        if loop and (is_outer is None or is_outer == loop.isOuter):
            for curve in loop.profileCurves:
                if not object_type or curve.sketchEntity.objectType == f"adsk::fusion::{object_type}":
                    curves.append(curve.sketchEntity)
    return curves

def get_offsetters(profiles):
    return [
        (
            to_collection(map(lambda pc: pc.sketchEntity, p.profileLoops[0].profileCurves)),
            p.areaProperties().centroid,
        )
        for p in profiles
    ]

def pick(points, indexes):
    return [points[i] for i in indexes]
