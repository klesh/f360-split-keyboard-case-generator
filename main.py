import adsk.core as c
import adsk.fusion as f
from os import path
from .libs.common import *
from .libs import kle, promicro, trrs
from .helper import *


def main(app: c.Application):

    ui = app.userInterface
    root: f.Component = app.activeProduct.rootComponent
    bodies: f.BRepBodies = root.bRepBodies
    sketches: f.Sketches = root.sketches
    extrudes: f.ExtrudeFeatures = root.features.extrudeFeatures
    fillets: f.FilletFeatures = root.features.filletFeatures
    planes: f.ConstructionPlanes = root.constructionPlanes
    combines: f.CombineFeatures = root.features.combineFeatures

    fileDlg = ui.createFileDialog()
    fileDlg.isMultiSelectEnabled = False
    fileDlg.title = "Keyboard Layout Editor  JSON file"
    fileDlg.filter = "*.json"
    dlgResult = fileDlg.showOpen()
    if dlgResult != c.DialogResults.DialogOK:
        return
    KLE.from_file(fileDlg.filename)

    #################################
    #   panel
    #################################
    panel_plane = planes.itemByName("panel")
    if not panel_plane:
        panel_plane_sketch = sketches.add(root.xYConstructionPlane)
        panel_plane_input = planes.createInput()
        solve_intercept = lambda x1, y1, x2, y2: (x1 * y2 - x2 * y1) / (x1 - x2)
        z = solve_intercept(layout.box.p1.y, FRONT_HEIGHT, layout.box.p2.y, REAR_HEIGHT)
        panel_plane_input.setByThreePoints(
            add_point(panel_plane_sketch, Point(0, 0, z)),
            add_point(panel_plane_sketch, Point(5, 0, z)),
            add_point(panel_plane_sketch, Point(0, 5, REAR_HEIGHT)),
        )
        panel_plane_sketch.name = "panel-pos"
        panel_plane = planes.add(panel_plane_input)
        panel_plane.name = "panel"

    panel_sketch = sketches.itemByName("panel")
    if not panel_sketch:
        panel_sketch = sketches.add(panel_plane)
        add_polygon(panel_sketch, layout.left)
        add_polygon(panel_sketch, layout.right)
        panel_sketch.name = "panel"

    panel_ext = extrudes.itemByName("panel_ext")
    if not panel_ext:
        ext_input = extrudes.createInput(
            to_collection(panel_sketch.profiles), f.FeatureOperations.NewBodyFeatureOperation
        )
        ext_input.setTwoSidesDistanceExtent(
            c.ValueInput.createByReal(PANEL_TOP_THICKNESS), c.ValueInput.createByReal(PANEL_BOTTOM_THICKNESS),
        )
        panel_ext = extrudes.add(ext_input)
        panel_ext.name = "panel_ext"
        for index, body in enumerate(sorted_bodies(panel_ext.bodies)):
            body.name = f"case_{index + 1}"

    cases = [case for case in panel_ext.bodies]

    #################################
    #   wall
    #################################
    wall_sketch = sketches.itemByName("wall")
    if not wall_sketch:
        wall_sketch = sketches.add(root.xYConstructionPlane)
        for case in cases:
            wall_sketch.project(case)
        for curves, point in get_offsetters(wall_sketch.profiles):
            wall_sketch.offset(curves, point, WALL_THICKNESS)
        wall_sketch.name = "wall"

    wall_ext = extrudes.itemByName("wall_ext")
    if not wall_ext:
        ext_input = extrudes.createInput(
            to_collection(sorted_profiles(wall_sketch.profiles)[0:2]), f.FeatureOperations.JoinFeatureOperation,
        )
        to_entity = f.ToEntityExtentDefinition.create(panel_ext.endFaces[0], False)
        ext_input.setOneSideExtent(to_entity, f.ExtentDirections.PositiveExtentDirection)
        ext_input.participantBodies = cases
        wall_ext = extrudes.add(ext_input)
        wall_ext.name = "wall_ext"

    #################################
    #   key holes
    #################################
    panel_top_sketch = sketches.itemByName("panel_top")
    if not panel_top_sketch:
        panel_top_sketch = sketches.add(panel_plane)
        for key in layout.keys:
            add_polygon(panel_top_sketch, key.hole)
        panel_top_sketch.name = "panel_top"

    panel_top_ext = extrudes.itemByName("panel_top_ext")
    if not panel_top_ext:
        to_entity = f.ToEntityExtentDefinition.create(sorted_faces(bodies.itemByName("case_1").faces)[-1], False)
        ext_input = extrudes.createInput(
            to_collection(panel_top_sketch.profiles), f.FeatureOperations.CutFeatureOperation,
        )
        ext_input.setOneSideExtent(to_entity, f.ExtentDirections.PositiveExtentDirection)
        ext_input.participantBodies = cases
        panel_top_ext = extrudes.add(ext_input)
        panel_top_ext.name = "panel_top_ext"

    panel_bottom_sketch = sketches.itemByName("panel_bottom")
    if not panel_bottom_sketch:
        panel_bottom_sketch = sketches.add(panel_plane)
        for key in layout.keys:
            add_box(panel_bottom_sketch, key.hole.box)
        panel_bottom_sketch.name = "panel_bottom"

    panel_bottom_ext = extrudes.itemByName("panel_bottom_ext")
    if not panel_bottom_ext:
        to_entity = f.ToEntityExtentDefinition.create(sorted_faces(bodies.itemByName("case_1").faces)[-1], False)
        ext_input = extrudes.createInput(
            to_collection(panel_bottom_sketch.profiles), f.FeatureOperations.CutFeatureOperation,
        )
        ext_input.setOneSideExtent(to_entity, f.ExtentDirections.PositiveExtentDirection)
        ext_input.participantBodies = cases
        panel_bottom_ext = extrudes.add(ext_input)
        panel_bottom_ext.name = "panel_bottom_ext"

    #################################
    #   plate bolt
    #################################
    bolt_plane = planes.itemByName("bolt")
    if not bolt_plane:
        bolt_plane = planes.createInput()
        pla_input = planes.createInput()
        pla_input.setByOffset(
            root.xYConstructionPlane, c.ValueInput.createByReal(PLATE_RAISE + PLATE_THICKNESS + PLATE_BOLT_DIST)
        )
        bolt_plane = planes.add(pla_input)
        bolt_plane.name = "bolt"

    bolt_sketch = sketches.itemByName("bolt")
    if not bolt_sketch:
        bolt_sketch = sketches.add(bolt_plane)
        for case in cases:
            bolt_sketch.projectCutEdges(case)
        profs = sorted_profiles(bolt_sketch.profiles)
        for prof in profs[0:2]:
            for entity in get_profile_entities(prof, is_outer=True):
                entity.deleteMe()
        points = sorted_points(bolt_sketch.sketchPoints)
        for p in pick(points, [0, 1, 2, 3, -4, -3, -2, -1]):
            add_tangent_circle(bolt_sketch, p, BOLT_OUTER_RADIUS)
        bolt_sketch.name = "bolt"

    wall_fillet = fillets.itemByName("wall_fillet")
    if not wall_fillet:
        edges = c.ObjectCollection.create()
        for case in cases:
            for e in case.edges:
                if (
                    e.startVertex.geometry.z == 0
                    and e.endVertex.geometry.z != 0
                    and abs(abs(e.startVertex.geometry.x) - abs(layout.box.p1.x)) <= WALL_THICKNESS * 2
                ):
                    edges.add(e)
        radius = c.ValueInput.createByReal(CORNER_RADIUS)
        fillet_input = fillets.createInput()
        fillet_input.addConstantRadiusEdgeSet(edges, radius, True)
        fillet_input.isRollingBallCorner = True
        wall_fillet = fillets.add(fillet_input)
        wall_fillet.name = "wall_fillet"

    bolt_ext = extrudes.itemByName("bolt_ext")
    if not bolt_ext:
        ext_input = extrudes.createInput(
            to_collection(sorted_profiles(bolt_sketch.profiles)[0:-2]), f.FeatureOperations.JoinFeatureOperation
        )
        ext_input.setDistanceExtent(
            False, c.ValueInput.createByReal(BOLT_HEIGHT),
        )
        ext_input.participantBodies = cases
        bolt_ext = extrudes.add(ext_input)
        bolt_ext.name = "bolt_ext"

    #################################
    #   plate
    #################################
    plate_plane = planes.itemByName("plate")
    if not plate_plane:
        plane_input = planes.createInput()
        offset = c.ValueInput.createByReal(PLATE_RAISE + PLATE_THICKNESS)
        plane_input.setByOffset(root.xYConstructionPlane, offset)
        plate_plane = planes.add(plane_input)
        plate_plane.name = "plate"

    plate_sketch = sketches.itemByName("plate")
    if not plate_sketch:
        plate_sketch = sketches.add(plate_plane)
        for case in cases:
            plate_sketch.projectCutEdges(case)
        for curves, center in get_offsetters(sorted_profiles(plate_sketch.profiles)[-2:]):
            plate_sketch.offset(curves, center, PLATE_GAP)
        plate_sketch.name = "plate"

    plate_ext = extrudes.itemByName("plate_ext")
    if not plate_ext:
        profs = sorted_profiles(plate_sketch.profiles)
        plate_ext = extrudes.addSimple(
            to_collection(profs[-2:]),
            c.ValueInput.createByReal(-PLATE_THICKNESS),
            f.FeatureOperations.NewBodyFeatureOperation,
        )
        plate_ext.name = "plate_ext"
        for index, body in enumerate(sorted_bodies(plate_ext.bodies)):
            body.name = f"plate-{index + 1}"

    plates = [p for p in bodies if p.name.startswith("plate")]

    #################################
    #   screw holes
    #################################
    screw_sketch = sketches.itemByName("screw")
    if not screw_sketch:
        screw_sketch = sketches.add(plate_plane)
        for circle in bolt_sketch.sketchCurves.sketchCircles:
            screw_sketch.project(circle.centerSketchPoint)
        for point in screw_sketch.sketchPoints:
            if point.geometry.x == 0 and point.geometry.y == 0:
                continue
            screw_sketch.sketchCurves.sketchCircles.addByCenterRadius(point, BOLT_HOLE_RADIUS)
            screw_sketch.sketchCurves.sketchCircles.addByCenterRadius(point, PLATE_HOLE_RADIUS)
        screw_sketch.name = "screw"

    plate_screw_ext = extrudes.itemByName("plate_screw_ext")
    if not plate_screw_ext:
        ext_input = extrudes.createInput(to_collection(screw_sketch.profiles), f.FeatureOperations.CutFeatureOperation,)
        ext_input.setOneSideExtent(
            f.ToEntityExtentDefinition.create(plate_ext.endFaces[0], False), f.ExtentDirections.NegativeExtentDirection,
        )
        ext_input.participantBodies = plates
        plate_screw_ext = extrudes.add(ext_input)
        plate_screw_ext.name = "plate_screw_ext"

    bolt_screw_ext = extrudes.itemByName("bolt_screw_ext")
    if not bolt_screw_ext:
        profs = sorted_profiles(screw_sketch.profiles)
        profs = profs[-int(len(profs) / 2) :]
        ext_input = extrudes.createInput(to_collection(profs), f.FeatureOperations.CutFeatureOperation,)
        ext_input.setOneSideExtent(
            f.ToEntityExtentDefinition.create(bolt_ext.endFaces[0], False), f.ExtentDirections.PositiveExtentDirection,
        )
        ext_input.participantBodies = cases
        bolt_screw_ext = extrudes.add(ext_input)
        bolt_screw_ext.name = "bolt_screw_ext"

    #################################
    #   holders
    #################################

    lines = pick(sorted_lines(plate_sketch.sketchCurves.sketchLines), [-5, -6],)
    p1, p2, p3, p4 = sorted_points(
        [lines[0].startSketchPoint, lines[0].endSketchPoint, lines[1].startSketchPoint, lines[1].endSketchPoint]
    )
    v1 = Vector(dx=p1.geometry.x + HOLDER_DIST, dy=p1.geometry.y)
    v2 = Vector(dx=p2.geometry.x - HOLDER_DIST, dy=p2.geometry.y)
    v3 = Vector(dx=p3.geometry.x + HOLDER_DIST, dy=p3.geometry.y)
    v4 = Vector(dx=p4.geometry.x - HOLDER_DIST, dy=p4.geometry.y)

    holder_sketch = sketches.itemByName("holder")
    if not holder_sketch:
        holder_sketch = sketches.add(plate_plane)
        promicro_ploygons = promicro.get_promicro_holder()
        for p in promicro_ploygons:
            add_polygon(holder_sketch, p.translate(v1))
            add_polygon(holder_sketch, p.translate(v4))
        for p in trrs.get_trrs_holder():
            add_polygon(holder_sketch, p.translate(v2))
            add_polygon(holder_sketch, p.translate(v3))
        holder_sketch.name = "holder"

    holder_ext = extrudes.itemByName("holder_ext")
    if not holder_ext:
        ext_input = extrudes.createInput(
            to_collection(sorted_profiles(holder_sketch.profiles)), f.FeatureOperations.JoinFeatureOperation,
        )
        ext_input.setDistanceExtent(False, c.ValueInput.createByReal(HOLDER_HEIGHT))
        ext_input.participantBodies = plates
        holder_ext = extrudes.add(ext_input)
        holder_ext.name = "holder_ext"

    #################################
    #   breakout
    #################################

    promicro_plane = planes.itemByName("promicro")
    if not promicro_plane:
        plane_input = planes.createInput()
        plane_input.setByOffset(plate_plane, c.ValueInput.createByReal(PROMICRO_Y + PROMICRO_T))
        promicro_plane = planes.add(plane_input)
        promicro_plane.name = "promicro"

    promicro_sketch = sketches.itemByName("promicro")
    if not promicro_sketch:
        promicro_sketch = sketches.add(promicro_plane)
        promicro_box1, promicro_box2 = promicro.get_promicro_boxes()
        add_box(promicro_sketch, promicro_box1.translate(v1))
        add_box(promicro_sketch, promicro_box1.translate(v4))
        add_box(promicro_sketch, promicro_box2.translate(v1))
        add_box(promicro_sketch, promicro_box2.translate(v4))
        promicro_sketch.name = "promicro"

    promicro_ext = extrudes.itemByName("promicro_ext")
    if not promicro_ext:
        promicro_ext = extrudes.addSimple(
            to_collection(promicro_sketch.profiles),
            c.ValueInput.createByReal(-PROMICRO_T),
            f.FeatureOperations.NewBodyFeatureOperation,
        )
        promicro_ext.name = "promicro_ext"
        for index, body in enumerate(sorted_bodies(promicro_ext.bodies)):
            body.name = f"promicro_{index + 1}"

    usb_ext1 = extrudes.itemByName("usb_ext1")
    if not usb_ext1:
        usb_ext1 = extrudes.addSimple(
            to_collection(sorted_profiles(promicro_sketch.profiles)[0:2]),
            c.ValueInput.createByReal(USB_H),
            f.FeatureOperations.NewBodyFeatureOperation,
        )
        usb_ext1.name = "usb_ext1"
        for index, body in enumerate(sorted_bodies(usb_ext1.bodies)):
            body.name = f"usb_{index + 1}"

    usbs = [b for b in bodies if b.name.startswith("usb")]

    usb_ext2 = extrudes.itemByName("usb_ext2")
    if not usb_ext2:
        ext_input = extrudes.createInput(
            to_collection(sorted_faces(usb_ext1.bodies[0].faces)[-2:] + sorted_faces(usb_ext1.bodies[1].faces)[-2:]),
            f.FeatureOperations.JoinFeatureOperation,
        )
        ext_input.setDistanceExtent(False, c.ValueInput.createByReal(-USB_H))
        ext_input.participantBodies = usbs
        usb_ext2 = extrudes.add(ext_input)
        usb_ext2.name = "usb_ext2"

    trrs_plane = planes.itemByName("trrs")
    if not trrs_plane:
        plane_input = planes.createInput()
        plane_input.setByOffset(plate_plane, c.ValueInput.createByReal(TRRS_T))
        trrs_plane = planes.add(plane_input)
        trrs_plane.name = "trrs"

    trrs_sketch = sketches.itemByName("trrs")
    if not trrs_sketch:
        trrs_sketch = sketches.add(trrs_plane)
        add_box(trrs_sketch, trrs.get_trrs_box().translate(v2))
        add_box(trrs_sketch, trrs.get_trrs_box().translate(v3))
        trrs_sketch.name = "trrs"

    trrs_ext1 = extrudes.itemByName("trrs_ext1")
    if not trrs_ext1:
        trrs_ext1 = extrudes.addSimple(
            to_collection(sorted_profiles(trrs_sketch.profiles)[0:2]),
            c.ValueInput.createByReal(-TRRS_T),
            f.FeatureOperations.NewBodyFeatureOperation,
        )
        trrs_ext1.name = "trrs_ext1"
        for index, body in enumerate(sorted_bodies(trrs_ext1.bodies)):
            body.name = f"trrs_{index + 1}"

    trrses = [b for b in bodies if b.name.startswith("trrs")]

    def trrs_sock(n: int):
        trrs_sock_sketch = sketches.itemByName(f"trrs{n}_sock")
        if not trrs_sock_sketch:
            face = sorted_faces(bodies.itemByName(f"trrs_{n}").faces)[1]
            trrs_sock_sketch = sketches.add(face)
            prof = trrs_sock_sketch.profiles[0]
            trrs_sock_sketch.sketchCurves.sketchCircles.addByCenterRadius(
                add_center_point_of_bounding_box(trrs_sock_sketch, prof.boundingBox), TRRS_RADIUS
            )
            trrs_sock_sketch.name = f"trrs{n}_sock"

        trrs_sock_ext = extrudes.itemByName(f"trrs{n}_sock_ext")
        if not trrs_sock_ext:
            ext_input = extrudes.createInput(
                sorted_profiles(trrs_sock_sketch.profiles)[-1], f.FeatureOperations.JoinFeatureOperation,
            )
            ext_input.setDistanceExtent(False, c.ValueInput.createByReal(TRRS_L))
            ext_input.participantBodies = trrses
            trrs_sock_ext = extrudes.add(ext_input)
            trrs_sock_ext.name = f"trrs{n}_sock_ext"

    trrs_sock(1)
    trrs_sock(2)

    def breakout(toolbodies, name):
        for i in range(2):
            breakout_name = f"{name}_breakout_{i+1}"
            breakout_ext = combines.itemByName(breakout_name)
            if not breakout_ext:
                cut_input = combines.createInput(cases[i], toolbodies)
                cut_input.operation = f.FeatureOperations.CutFeatureOperation
                cut_input.isKeepToolBodies = True
                breakout_ext = combines.add(cut_input)
                breakout_ext.name = breakout_name

    breakout(to_collection(trrses), "trrs")
    breakout(to_collection(usbs), "usb")
