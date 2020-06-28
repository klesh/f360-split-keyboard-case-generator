import adsk.core, adsk.fusion
from .libs.common import *
from .libs import kle, promicro, trrs
from .helper import *


def main(app: adsk.core.Application):

    ui = app.userInterface
    # doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    root: adsk.fusion.Component = app.activeProduct.rootComponent
    bodies: adsk.fusion.BRepBodies = root.bRepBodies
    sketches: adsk.fusion.Sketches = root.sketches
    extrudes: adsk.fusion.ExtrudeFeatures = root.features.extrudeFeatures
    fillets: adsk.fusion.FilletFeatures = root.features.filletFeatures
    planes: adsk.fusion.ConstructionPlanes = root.constructionPlanes
    combines: adsk.fusion.CombineFeatures = root.features.combineFeatures

    # fileDlg = ui.createFileDialog()
    # fileDlg.isMultiSelectEnabled = False
    # fileDlg.title = "Keyboard Layout Editor  JSON file"
    # fileDlg.filter = "*.json"
    # dlgResult = fileDlg.showOpen()
    # if dlgResult != adsk.core.DialogResults.DialogOK:
    #     return
    # KLE.from_file(fileDlg.filename)
    layout = kle.from_file(r"C:\Users\Klesh\Desktop\ks63\ks-63.json")

    panel_plane = planes.itemByName("panel_plane")
    if not panel_plane:
        panel_plane_sketch = sketches.add(root.xYConstructionPlane)
        panel_plane_input = planes.createInput()
        panel_plane_input.setByThreePoints(
            *map(lambda p: add_point(panel_plane_sketch, p), params.get_panel_plane_points(layout))
        )
        panel_plane_sketch.name = "panel_plane"
        panel_plane = planes.add(panel_plane_input)
        panel_plane.name = "panel_plane"

    panel_top_sketch = sketches.itemByName("panel_top")
    if not panel_top_sketch:
        panel_top_sketch = sketches.add(panel_plane)
        for key in layout.keys:
            add_polygon(panel_top_sketch, key.hole)
        add_box(panel_top_sketch, layout.box)
        panel_top_sketch.name = "panel_top"

    panel_top_ext = extrudes.itemByName("panel_top_ext")
    if not panel_top_ext:
        panel_top_ext = extrudes.addSimple(
            sorted_profiles(panel_top_sketch)[-1],
            adsk.core.ValueInput.createByReal(PANEL_TOP_THICKNESS),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        )
        panel_top_ext.name = "panel_top_ext"

    case = panel_top_ext.bodies[0]
    case.name = "case"

    panel_bottom_sketch = sketches.itemByName("panel_bottom")
    if not panel_bottom_sketch:
        panel_bottom_sketch = sketches.add(panel_plane)
        for key in layout.keys:
            add_box(panel_bottom_sketch, key.hole.box)
        add_box(panel_bottom_sketch, layout.box)
        panel_bottom_sketch.name = "panel_bottom"

    panel_bottom_ext = extrudes.itemByName("panel_bottom_ext")
    if not panel_bottom_ext:
        panel_bottom_ext = extrudes.addSimple(
            sorted_profiles(panel_bottom_sketch)[-1],
            adsk.core.ValueInput.createByReal(-PANEL_TOP_THICKNESS),
            adsk.fusion.FeatureOperations.JoinFeatureOperation,
        )
        panel_bottom_ext.name = "panel_bottom_ext"

    wall_sketch = sketches.itemByName("wall")
    if not wall_sketch:
        wall_sketch = sketches.add(root.xYConstructionPlane)
        p1 = wall_sketch.project(sorted_vertices(panel_bottom_ext.endFaces[0])[0])[0]
        p2 = wall_sketch.project(sorted_vertices(panel_top_ext.endFaces[0])[-1])[0]
        wall_sketch.sketchCurves.sketchLines.addTwoPointRectangle(p1, p2)
        p3 = wall_sketch.sketchPoints.add(
            adsk.core.Point3D.create(p1.geometry.x - WALL_THICKNESS, p1.geometry.y - WALL_THICKNESS, 0)
        )
        p4 = wall_sketch.sketchPoints.add(
            adsk.core.Point3D.create(p2.geometry.x + WALL_THICKNESS, p2.geometry.y + WALL_THICKNESS, 0)
        )
        wall_sketch.sketchCurves.sketchLines.addTwoPointRectangle(p3, p4)
        wall_sketch.name = "wall"

    wall_ext = extrudes.itemByName("wall_ext")
    if not wall_ext:
        prof = sorted_profiles(wall_sketch)[0]
        ext_input = extrudes.createInput(prof, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        to_entity = adsk.fusion.ToEntityExtentDefinition.create(panel_top_ext.endFaces[0], False)
        ext_input.setOneSideExtent(to_entity, adsk.fusion.ExtentDirections.PositiveExtentDirection)
        wall_ext = extrudes.add(ext_input)
        wall_ext.name = "wall_ext"

    wall_fillet = fillets.itemByName("wall_fillet")
    if not wall_fillet:
        edges = to_collection(
            filter(lambda e: e.startVertex.geometry.z == 0 and e.endVertex.geometry.z != 0, wall_ext.bodies[0].edges)
        )
        radius = adsk.core.ValueInput.createByReal(5 * MM)
        fillet_input = fillets.createInput()
        fillet_input.addConstantRadiusEdgeSet(edges, radius, True)
        fillet_input.isRollingBallCorner = True
        wall_fillet = fillets.add(fillet_input)
        wall_fillet.name = "wall_fillet"

    plate_plane = planes.itemByName("plate")
    if not plate_plane:
        plane_input = planes.createInput()
        offset = adsk.core.ValueInput.createByReal(1 * MM)
        plane_input.setByOffset(root.xYConstructionPlane, offset)
        plate_plane = planes.add(plane_input)
        plate_plane.name = "plate"

    plate_sketch = sketches.itemByName("plate")
    if not plate_sketch:
        plate_sketch = sketches.add(plate_plane)
        plate_sketch.projectCutEdges(case)
        wall_outer_prof, wall_inner_prof = sorted_profiles(plate_sketch)
        curves = to_collection(map(lambda pc: pc.sketchEntity, wall_inner_prof.profileLoops.item(0).profileCurves))
        plate_sketch.offset(curves, plate_sketch.origin, PLATE_GAP)
        plate_sketch.name = "plate"

    plate_ext = extrudes.itemByName("plate_ext")
    if not plate_ext:
        plate_ext = extrudes.addSimple(
            sorted_profiles(plate_sketch)[-1],
            adsk.core.ValueInput.createByReal(2 * MM),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        )
        plate_ext.bodies[0].name = "plate"
        plate_ext.name = "plate_ext"

    holder_face = plate_ext.endFaces[0]
    x1 = holder_face.boundingBox.minPoint.x + HOLDER_DIST
    x2 = holder_face.boundingBox.maxPoint.x - HOLDER_DIST
    y = holder_face.boundingBox.maxPoint.y
    v1, v2 = Vector(x1, y), Vector(x2, y)
    v3, v4 = Vector(x1 + HOLDER_DIST, y), Vector(x2 - HOLDER_DIST, y)

    holder_sketch = sketches.itemByName("holder")
    if not holder_sketch:
        holder_sketch = sketches.add(holder_face)
        promicro_ploygons = promicro.get_promicro_holder()
        for p in promicro_ploygons:
            add_polygon(holder_sketch, p.translate(v1))
            add_polygon(holder_sketch, p.translate(v2))
        for p in trrs.get_trrs_holder():
            add_polygon(holder_sketch, p.translate(v3))
            add_polygon(holder_sketch, p.translate(v4))
        holder_sketch.name = "holder"

    holder_ext = extrudes.itemByName("holder_ext")
    if not holder_ext:
        holder_ext = extrudes.addSimple(
            to_collection(sorted_profiles(holder_sketch)[0:-1]),
            adsk.core.ValueInput.createByReal(HOLDER_HEIGHT),
            adsk.fusion.FeatureOperations.JoinFeatureOperation,
        )
        holder_ext.name = "holder_ext"

    promicro_plane = planes.itemByName("promicro")
    if not promicro_plane:
        plane_input = planes.createInput()
        plane_input.setByOffset(holder_face, adsk.core.ValueInput.createByReal(PROMICRO_Y + PROMICRO_T))
        promicro_plane = planes.add(plane_input)
        promicro_plane.name = "promicro"

    promicro_sketch = sketches.itemByName("promicro")
    if not promicro_sketch:
        promicro_sketch = sketches.add(promicro_plane)
        promicro_box1, promicro_box2 = promicro.get_promicro_boxes()
        add_box(promicro_sketch, promicro_box1.translate(v1))
        add_box(promicro_sketch, promicro_box1.translate(v2))
        add_box(promicro_sketch, promicro_box2.translate(v1))
        add_box(promicro_sketch, promicro_box2.translate(v2))
        profs = sorted_profiles(promicro_sketch)
        promicro_sketch.name = "promicro"

    promicro_ext = extrudes.itemByName("promicro_ext")
    if not promicro_ext:
        promicro_ext = extrudes.addSimple(
            to_collection(promicro_sketch.profiles),
            adsk.core.ValueInput.createByReal(-PROMICRO_T),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        )
        promicro_ext.name = "promicro_ext"

    usb_ext1 = extrudes.itemByName("usb_ext1")
    if not usb_ext1:
        usb_ext1 = extrudes.addSimple(
            to_collection(sorted_profiles(promicro_sketch)[0:2]),
            adsk.core.ValueInput.createByReal(USB_H),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        )
        usb_ext1.name = "usb_ext1"
        for index, body in enumerate(usb_ext1.bodies):
            body.name = f"usb_{index + 1}"

    usb_ext2 = extrudes.itemByName("usb_ext2")
    if not usb_ext2:
        usb_ext2 = extrudes.addSimple(
            to_collection(sorted_faces(usb_ext1.bodies[0])[-2:] + sorted_faces(usb_ext1.bodies[1])[-2:]),
            adsk.core.ValueInput.createByReal(USB_H),
            adsk.fusion.FeatureOperations.JoinFeatureOperation,
        )
        usb_ext2.name = "usb_ext2"
        for index, body in enumerate(usb_ext2.bodies):
            body.name = f"promicro_{index + 1}"

    promicro1_cut = combines.itemByName("promicro1_cut")
    if not promicro1_cut:
        cut_input = combines.createInput(case, to_collection([bodies.itemByName("promicro_1")]))
        cut_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
        promicro1_cut = combines.add(cut_input)
        promicro1_cut.name = "promicro1_cut"

    promicro2_cut = combines.itemByName("promicro2_cut")
    if not promicro2_cut:
        cut_input = combines.createInput(case, to_collection([bodies.itemByName("promicro_2")]))
        cut_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
        promicro2_cut = combines.add(cut_input)
        promicro2_cut.name = "promicro2_cut"

    trrs_plane = planes.itemByName("trrs")
    if not trrs_plane:
        plane_input = planes.createInput()
        plane_input.setByOffset(holder_face, adsk.core.ValueInput.createByReal(TRRS_T))
        trrs_plane = planes.add(plane_input)
        trrs_plane.name = "trrs"

    trrs_sketch = sketches.itemByName("trrs")
    if not trrs_sketch:
        trrs_sketch = sketches.add(trrs_plane)
        add_box(trrs_sketch, trrs.get_trrs_box().translate(v3))
        add_box(trrs_sketch, trrs.get_trrs_box().translate(v4))
        trrs_sketch.name = "trrs"

    trrs_ext1 = extrudes.itemByName("trrs_ext1")
    if not trrs_ext1:
        trrs_ext1 = extrudes.addSimple(
            to_collection(sorted_profiles(trrs_sketch)[0:2]),
            adsk.core.ValueInput.createByReal(-TRRS_T),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        )
        trrs_ext1.name = "trrs_ext1"
        for index, body in enumerate(trrs_ext1.bodies):
            body.name = f"trrs-{index + 1}"

    def trrs_sock(n: int):
        trrs_sock_sketch = sketches.itemByName(f"trrs{n}_sock")
        if not trrs_sock_sketch:
            face = sorted_faces(bodies.itemByName(f"trrs_{n}"))[1]
            trrs_sock_sketch = sketches.add(face)
            prof = trrs_sock_sketch.profiles[0]
            trrs_sock_sketch.sketchCurves.sketchCircles.addByCenterRadius(
                add_center_point_of_bounding_box(trrs_sock_sketch, prof.boundingBox), TRRS_RADIUS
            )
            trrs_sock_sketch.name = f"trrs{n}_sock"

        trrs_sock_ext = extrudes.itemByName(f"trrs{n}_sock_ext")
        if not trrs_sock_ext:
            trrs_sock_ext = extrudes.addSimple(
                sorted_profiles(trrs_sock_sketch)[-1],
                adsk.core.ValueInput.createByReal(TRRS_L),
                adsk.fusion.FeatureOperations.JoinFeatureOperation,
            )
            trrs_sock_ext.name = f"trrs{n}_sock_ext"

        trrs_cut = combines.itemByName(f"trrs{n}_cut")
        if not trrs_cut:
            cut_input = combines.createInput(case, to_collection([bodies.itemByName(f"trrs_{n}")]))
            cut_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
            promicro1_cut = combines.add(cut_input)
            promicro1_cut.name = f"trrs{n}_cut"

    trrs_sock(1)
    trrs_sock(2)

    splitter_ref_sketch = sketches.itemByName("splitter_ref")
    if not splitter_ref_sketch:
        splitter_ref_sketch = sketches.add(panel_plane)
        splitter = layout.splitter
        a, b = splitter[0], splitter[-1]
        for p in splitter:
            add_point(splitter_ref_sketch, p)
        splitter_ref_sketch.name = "splitter_ref"

    splitter_sketch = sketches.itemByName("splitter")
    if not splitter_sketch:
        splitter_sketch = sketches.add(root.xYConstructionPlane)
        split_points = []
        for p in splitter_ref_sketch.sketchPoints:
            if not (p.geometry.x == 0 and p.geometry.y == 0):
                split_points.append(splitter_sketch.project(p)[0].geometry)
        tmp = connect_points(splitter_sketch, split_points)
        lines = to_collection(tmp)
        a = splitter_sketch.offset(lines, splitter_sketch.origin, SPLIT_GAP / 2)
        b = splitter_sketch.offset(lines, splitter_sketch.origin, -SPLIT_GAP / 2)
        for line in lines:
            line.deleteMe()
        ui.messageBox(f"{case.boundingBox.minPoint.y - a[-1].endSketchPoint.geometry.y}")
        v1 = adsk.core.Vector3D.create(0, case.boundingBox.maxPoint.y - a[0].startSketchPoint.geometry.y, 0)
        v2 = adsk.core.Vector3D.create(0, case.boundingBox.minPoint.y - a[-1].endSketchPoint.geometry.y, 0)
        a[0].startSketchPoint.move(v1)
        b[0].startSketchPoint.move(v1)
        a[-1].endSketchPoint.move(v2)
        b[-1].endSketchPoint.move(v2)
        splitter_sketch.sketchCurves.sketchLines.addByTwoPoints(
            a[0].startSketchPoint,
            b[0].startSketchPoint
        )
        splitter_sketch.sketchCurves.sketchLines.addByTwoPoints(
            a[-1].endSketchPoint,
            b[-1].endSketchPoint
        )
        splitter_sketch.name = "splitter"

    splitter_ext = extrudes.itemByName("splitter_ext")
    if not splitter_ext:
        prof = splitter_sketch.profiles[0]
        ext_input = extrudes.createInput(prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
        to_entity = adsk.fusion.ToEntityExtentDefinition.create(sorted_faces(case)[-1], False)
        ext_input.setOneSideExtent(to_entity, adsk.fusion.ExtentDirections.PositiveExtentDirection)
        splitter_ext = extrudes.add(ext_input)
        splitter_ext.name = "splitter_ext"

