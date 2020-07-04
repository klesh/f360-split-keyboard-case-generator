from adsk.core import *
from adsk.fusion import *
from typing import Iterable
from .libs.common import *
from .debug import *


class SketchHelper:
    @classmethod
    def wrap(cls, sketch: Sketch):
        return cls(sketch) if isinstance(sketch, Sketch) else None

    def __init__(self, sketch: Sketch):
        self.sketch = sketch

    @property
    def name(self):
        return self.sketch.name

    @name.setter
    def name(self, name):
        self.sketch.name = name

    @property
    def is_visible(self):
        return self.sketch.isVisible

    @is_visible.setter
    def is_visible(self, v):
        self.sketch.isVisible = v

    @property
    def sorted_profiles(self) -> List[Profile]:
        return sorted(
            self.sketch.profiles,
            key=lambda p: (p.boundingBox.minPoint.z, p.boundingBox.minPoint.y, p.boundingBox.minPoint.x),
        )

    @property
    def profiles(self):
        return self.sketch.profiles

    @property
    def points(self) -> SketchPoints:
        return self.sketch.sketchPoints

    @property
    def points_without_origin(self):
        return list(filter(lambda p: p.geometry.x != 0 or p.geometry.y != 0 or p.geometry.z != 0, self.points))

    @property
    def circles(self) -> SketchCircles:
        return self.sketch.sketchCurves.sketchCircles

    @property
    def lines(self) -> SketchLines:
        return self.sketch.sketchCurves.sketchLines

    @property
    def sorted_lines(self) -> List[SketchLine]:
        def get_line_center_tuple(line):
            p1, p2 = line.startSketchPoint.geometry, line.endSketchPoint.geometry
            return (p1.x + p2.x) / 2, (p1.y + p2.y) / 2, (p1.z + p2.z) / 2
        return sorted(self.lines, key=lambda l: get_line_center_tuple(l)[::-1])

    def translate_point(self, point: Point3D, dx=0, dy=0, dz=0):
        copied = point.copy()
        copied.translateBy(Vector3D.create(dx, dy, dz))
        return copied

    def add_point(self, point: Point):
        point = Point3D.create(point.x, point.y, point.z)
        return self.points.add(point)

    def add_center_point_of_bounding_box(self, boundingBox: BoundingBox3D):
        return self.add_point(
            Point(
                (boundingBox.minPoint.x + boundingBox.maxPoint.x) / 2,
                (boundingBox.minPoint.y + boundingBox.maxPoint.y) / 2,
                (boundingBox.minPoint.z + boundingBox.maxPoint.z) / 2,
            ),
        )

    def add_rect(self, rect: Rect):
        return self.sketch.sketchCurves.sketchLines.addTwoPointRectangle(
            self.add_point(rect.p1), self.add_point(rect.p2),
        )

    def add_circle(self, center: Point, radius: float):
        return self.sketch.sketchCurves.sketchCircles.addByCenterRadius(add_point(sketch, center), radius)

    def connect_points(self, points, close=False):
        l = len(points)
        lines = map(lambda i: (points[i], points[(i + 1) % l]), range(l if close else l - 1))
        return [self.sketch.sketchCurves.sketchLines.addByTwoPoints(p1, p2) for p1, p2 in lines]

    def add_polygon(self, polygon: Polygon):
        points = polygon.points
        if polygon.shape == Polygon.RECT:
            return self.add_rect(Rect(*points))
        points = [self.add_point(point) for point in points]
        return self.connect_points(points, True)

    def add_tangent_circle(self, point: SketchPoint, radius: float):
        line1, line2 = point.connectedEntities
        other_point = lambda l: l.startSketchPoint if l.startSketchPoint != point else l.endSketchPoint
        p1, p2 = other_point(line1), other_point(line2)
        center = Point3D.create(
            (p1.geometry.x + p2.geometry.x) / 2,
            (p1.geometry.y + p2.geometry.y) / 2,
            (p1.geometry.z + p2.geometry.z) / 2,
        )
        return self.sketch.sketchCurves.sketchCircles.addByTwoTangents(line1, line2, radius, center)

    def add_center_circle(self, point: SketchPoint, radius: float):
        self.circles.addByCenterRadius(point, radius)

    def project(self, entities):
        for entity in entities:
            self.sketch.project(entity)

    def project_cut_edges(self, bodies):
        for body in bodies:
            self.sketch.projectCutEdges(body)

    def offset(self, profiles, dist):
        tmp = [
            (
                to_collection(map(lambda pc: pc.sketchEntity, p.profileLoops[0].profileCurves)),
                p.areaProperties().centroid,
            )
            for p in profiles
        ]
        for curves, point in tmp:
            self.sketch.offset(curves, point, dist)


class ProfileHelper:

    def __init__(self, profile: Profile):
        self.profile = profile

    @property
    def entities(self):
        entities = []
        for loop in self.profile.profileLoops:
            if not loop:
                continue
            for curve in loop.profileCurves:
                entities.append(curve.sketchEntity)
        return entities

    @property
    def sorted_points(self) -> List[SketchPoint]:
        points = []
        def add(p):
            if p not in points:
                points.append(p)
        for entity in self.entities:
            if entity.objectType.endswith("::SketchPoint"):
                add(entity)
            elif entity.objectType.endswith("::SketchLine") or entity.objectType.endswith("::SketchArc"):
                add(entity.startSketchPoint)
                add(entity.endSketchPoint)
            elif entity.objectType.endswith("::SketchCircle"):
                add(entity.centerSketchPoint)
        return sorted(points, key=lambda p: (p.geometry.z, p.geometry.y, p.geometry.x))

class ExtrudeHelper:
    @classmethod
    def wrap(cls, extrude: ExtrudeFeature):
        return cls(extrude) if isinstance(extrude, ExtrudeFeature) else None

    def __init__(self, extrude: ExtrudeFeature):
        self.extrude = extrude

    @property
    def name(self) -> str:
        return self.extrude.name

    @name.setter
    def name(self, v: str) -> None:
        self.extrude.name = v

    @property
    def bodies(self) -> BRepBodies:
        return self.extrude.bodies

    @property
    def sorted_bodies(self):
        def body_key(b: BRepBody):
            p = b.physicalProperties.centerOfMass
            return (p.z, p.y, p.x)

        return sorted(self.bodies, key=body_key)


class BodyHelper:
    def __init__(self, body: BRepBody):
        self.body = body

    @property
    def faces(self) -> BRepFaces:
        return self.body.faces

    @property
    def sorted_faces(self):
        return sorted(self.faces, key=lambda f: (f.centroid.z, f.centroid.y, f.centroid.x))

    def closest_face(self, vector: Vector) -> BRepFace:
        v = Vector3D.create(vector.dx, vector.dy, vector.dz)
        angle, face = float("inf"), None
        for f in self.faces:
            s, n = f.evaluator.getNormalAtParameter(Point2D.create(0, 0))
            a = n.angleTo(v)
            if a < angle:
                angle = a
                face = f
        return face


class ComponentHelper:
    def __init__(self, component: Component):
        self.component = component

    @property
    def planes(self) -> ConstructionPlanes:
        return self.component.constructionPlanes

    @property
    def sketches(self) -> Sketches:
        return self.component.sketches

    @property
    def xyplane(self) -> ConstructionPlane:
        return self.component.xYConstructionPlane

    @property
    def extrudes(self) -> ExtendFeatures:
        return self.component.features.extrudeFeatures

    @property
    def bodies(self) -> BRepBodies:
        return self.component.bRepBodies

    @property
    def fillets(self) -> FilletFeatures:
        return self.component.features.filletFeatures

    @property
    def offsets(self) -> OffsetFeatures:
        return self.component.features.offsetFeatures

    @property
    def combines(self) -> CombineFeatures:
        return self.component.features.combineFeatures

    def offset_plane(self, plane: ConstructionPlane, offset: float):
        pla_input = self.planes.createInput()
        pla_input.setByOffset(plane, ValueInput.createByReal(offset))
        return self.planes.add(pla_input)

    def add_three_points_plane(self, p1: Point3D, p2: Point3D, p3: Point3D):
        pla_input = self.planes.createInput()
        pla_input.setByThreePoints(p1, p2, p3)
        return self.planes.add(pla_input)

    def add_sketch(self, planar) -> SketchHelper:
        return self.sketches.add(planar)

    def add_two_sides_extrude(self, profiles: Iterable[Profile], operation, dist1, dist2):
        ext_input = self.extrudes.createInput(to_collection(profiles), operation)
        ext_input.setTwoSidesExtent(
            DistanceExtentDefinition.create(ValueInput.createByReal(dist1)),
            DistanceExtentDefinition.create(ValueInput.createByReal(dist2)),
        )
        return self.extrudes.add(ext_input)

    def add_one_side_extrude(
        self, profiles: Iterable[Profile], operation, to_entity=None, direction=None, bodies=None, distance=None, offset=0
    ):
        ext_input = self.extrudes.createInput(to_collection(profiles), operation)
        extent = None
        if to_entity:
            extent = ToEntityExtentDefinition.create(to_entity, False, ValueInput.createByReal(offset))
        elif distance:
            extent = DistanceExtentDefinition.create(ValueInput.createByReal(distance))
        ext_input.setOneSideExtent(extent, direction or ExtentDirections.PositiveExtentDirection)
        if bodies:
            ext_input.participantBodies = bodies 
        return self.extrudes.add(ext_input)

    def add_fillet(self, edges: List[BRepEdge], radius: float):
        fillet_input = self.fillets.createInput()
        fillet_input.addConstantRadiusEdgeSet(to_collection(edges), ValueInput.createByReal(radius), True)
        fillet_input.isRollingBallCorner = True
        return self.fillets.add(fillet_input)

    def add_simple_extrude(self, profiles: List[Profile], operation: FeatureOperations, distance: float):
        return self.extrudes.addSimple(
            to_collection(profiles),
            ValueInput.createByReal(distance),
            operation,
        )

    def present_bodies(self, visible: callable):
        for body in self.bodies:
            body.isVisible = visible(body)


def to_collection(entities):
    coll = ObjectCollection.create()
    for entity in entities:
        coll.add(entity)
    return coll


def pick(points, indexes):
    return [points[i] for i in indexes]
