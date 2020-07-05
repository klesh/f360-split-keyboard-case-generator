from adsk.core import *
from adsk.fusion import *
from .libs.common import *
from .libs import kle, promicro, trrs
from .helper import *
from .debug import *


def main(app: Application):

    ui = app.userInterface

    fileDlg = ui.createFileDialog()
    fileDlg.isMultiSelectEnabled = False
    fileDlg.title = "Keyboard Layout Editor  JSON file"
    fileDlg.filter = "*.json"
    dlgResult = fileDlg.showOpen()
    if dlgResult != DialogResults.DialogOK:
        return
    layout = kle.from_file(fileDlg.filename)
    # layout = kle.from_file(r"C:\Users\Klesh\Desktop\ks63\ks-63.json")
    root = ComponentHelper(app.activeProduct.rootComponent)

    #################################
    #   panel
    #################################

    panel_plane_sketch = SketchHelper.wrap(root.sketches.itemByName("panel_plane_sketch"))
    if not panel_plane_sketch:
        panel_plane_sketch = SketchHelper.wrap(root.add_sketch(root.xyplane))
        z = solve_intercept(layout.rect.p1.y, FRONT_HEIGHT, layout.rect.p2.y, REAR_HEIGHT)
        panel_plane_sketch.add_point(Point(0, 0, z)),
        panel_plane_sketch.add_point(Point(5, 0, z)),
        panel_plane_sketch.add_point(Point(0, 5, REAR_HEIGHT)),
        panel_plane_sketch.is_visible = False
        panel_plane_sketch.name = "panel_plane_sketch"

    panel_plane = root.planes.itemByName("panel_plane")
    if not panel_plane:
        panel_plane = root.add_three_points_plane(*panel_plane_sketch.points_without_origin)
        panel_plane.name = "panel_plane"

    panel_sketch = SketchHelper.wrap(root.sketches.itemByName("panel"))
    if not panel_sketch:
        panel_sketch = SketchHelper.wrap(root.add_sketch(panel_plane))
        panel_sketch.add_polygon(layout.left)
        panel_sketch.add_polygon(layout.right)
        panel_sketch.name = "panel"

    panel_ext = ExtrudeHelper.wrap(root.extrudes.itemByName("panel_ext"))
    if not panel_ext:
        panel_ext = ExtrudeHelper.wrap(root.add_two_sides_extrude(
            panel_sketch.profiles,
            FeatureOperations.NewBodyFeatureOperation,
            PANEL_TOP_THICKNESS,
            PANEL_BOTTOM_THICKNESS,
        ))
        for index, body in enumerate(panel_ext.sorted_bodies):
            body.name = f"case_{index+1}"
        panel_ext.name = "panel_ext"

    cases = [b for b in root.bodies if b.name.startswith("case")]
    

    #################################
    #   wall
    #################################

    wall_sketch = SketchHelper.wrap(root.sketches.itemByName("wall"))
    if not wall_sketch:
        wall_sketch = SketchHelper.wrap(root.add_sketch(root.xyplane))
        wall_sketch.project(cases)
        wall_sketch.offset(wall_sketch.profiles, WALL_THICKNESS)
        wall_sketch.name = "wall"

    wall_ext = root.extrudes.itemByName("wall_ext")
    if not wall_ext:
        wall_ext = root.add_one_side_extrude(
            wall_sketch.sorted_profiles[0:2],
            FeatureOperations.JoinFeatureOperation,
            to_entity=BodyHelper(cases[0]).closest_face(Vector(0, 0, 1)),
            bodies=cases,
        )
        wall_ext.name = "wall_ext"

    #################################
    #   key holes
    #################################

    panel_top_sketch = SketchHelper.wrap(root.sketches.itemByName("panel_top"))
    if not panel_top_sketch:
        panel_top_sketch = SketchHelper.wrap(root.sketches.add(panel_plane))
        for key in layout.keys:
            panel_top_sketch.add_polygon(key.hole)
        panel_top_sketch.name = "panel_top"

    panel_top_ext = root.extrudes.itemByName("panel_top_ext")
    if not panel_top_ext:
        panel_top_ext = root.add_one_side_extrude(
            panel_top_sketch.profiles,
            FeatureOperations.CutFeatureOperation,
            to_entity=BodyHelper(cases[0]).closest_face(Vector(0, 0, 1)),
            bodies=cases
        )
        panel_top_ext.name = "panel_top_ext"

    panel_bottom_sketch = SketchHelper.wrap(root.sketches.itemByName("panel_bottom"))
    if not panel_bottom_sketch:
        panel_bottom_sketch = SketchHelper.wrap(root.sketches.add(panel_plane))
        for key in layout.keys:
            panel_bottom_sketch.add_rect(key.hole.rect)
        panel_bottom_sketch.name = "panel_bottom"

    panel_bottom_ext = root.extrudes.itemByName("panel_bottom_ext")
    if not panel_bottom_ext:
        panel_bottom_ext = root.add_one_side_extrude(
            panel_bottom_sketch.profiles,
            FeatureOperations.CutFeatureOperation,
            distance=-SWITCH_CLEARANCE,
            bodies=cases
        )
        panel_bottom_ext.name = "panel_bottom_ext"

    #################################
    #   plate bolt
    #################################

    bolt_plane = root.planes.itemByName("bolt")
    if not bolt_plane:
        bolt_plane = root.offset_plane(
            root.xyplane,
            PLATE_RAISE + PLATE_THICKNESS + PLATE_BOLT_DIST
        )
        bolt_plane.name = "bolt"

    bolt_sketch = SketchHelper.wrap(root.sketches.itemByName("bolt"))
    if not bolt_sketch:
        bolt_sketch = SketchHelper.wrap(root.sketches.add(bolt_plane))
        bolt_sketch.project_cut_edges(cases)
        points = []
        for prof in bolt_sketch.sorted_profiles[-2:]:
            for p in pick(ProfileHelper(prof).sorted_points, [0, 1, -2, -1]):
                points.append(p)
        for p in points:
            bolt_sketch.add_tangent_circle(p, BOLT_OUTER_RADIUS)
        bolt_sketch.name = "bolt"

    bolt_ext = root.extrudes.itemByName("bolt_ext")
    if not bolt_ext:
        bolt_ext = root.add_one_side_extrude(
            sorted(bolt_sketch.profiles, key=lambda p: p.areaProperties().area)[:-2],
            FeatureOperations.JoinFeatureOperation,
            to_entity=BodyHelper(cases[0]).closest_face(Vector(0, 0, 1)),
            bodies=cases
        )
        bolt_ext.name = "bolt_ext"


    wall_fillet = root.fillets.itemByName("wall_fillet")
    if not wall_fillet:
        edges = ObjectCollection.create()
        for case in cases:
            for e in case.edges:
                if (
                    e.startVertex.geometry.z == 0
                    and e.endVertex.geometry.z != 0
                    and abs(abs(e.startVertex.geometry.x) - abs(layout.rect.p1.x)) <= WALL_THICKNESS * 2
                ):
                    edges.add(e)
        wall_fillet = root.add_fillet(edges, CORNER_RADIUS)
        wall_fillet.name = "wall_fillet"

    #################################
    #   plate
    #################################

    plate_plane = root.planes.itemByName("plate")
    if not plate_plane:
        plate_plane = root.offset_plane(root.xyplane, PLATE_RAISE + PLATE_THICKNESS)
        plate_plane.name = "plate"

    plate_sketch = SketchHelper.wrap(root.sketches.itemByName("plate"))
    if not plate_sketch:
        plate_sketch = SketchHelper.wrap(root.sketches.add(plate_plane))
        plate_sketch.project_cut_edges(cases)
        plate_sketch.offset(plate_sketch.sorted_profiles[-2:], PLATE_GAP)
        plate_sketch.name = "plate"

    plate_ext = root.extrudes.itemByName("plate_ext")
    if not plate_ext:
        plate_ext = root.add_one_side_extrude(
            plate_sketch.sorted_profiles[4:6],
            FeatureOperations.NewBodyFeatureOperation,
            distance=-PLATE_THICKNESS,
        )
        plate_ext.name = "plate_ext"
        for index, body in enumerate(ExtrudeHelper(plate_ext).sorted_bodies):
            body.name = f"plate_{index + 1}"

    plates = [p for p in root.bodies if p.name.startswith("plate")]

    #################################
    #   screw holes
    #################################

    screw_sketch = SketchHelper.wrap(root.sketches.itemByName("screw"))
    if not screw_sketch:
        screw_sketch = SketchHelper.wrap(root.sketches.add(plate_plane))
        screw_sketch.project(map(lambda c: c.centerSketchPoint, bolt_sketch.circles))
        for point in screw_sketch.points_without_origin:
            screw_sketch.add_center_circle(point, BOLT_HOLE_RADIUS)
            screw_sketch.add_center_circle(point, PLATE_HOLE_RADIUS)
        screw_sketch.name = "screw"

    plate_screw_ext = root.extrudes.itemByName("plate_screw_ext")
    if not plate_screw_ext:
        plate_screw_ext = root.add_one_side_extrude(
            screw_sketch.profiles,
            FeatureOperations.CutFeatureOperation,
            distance=-PLATE_THICKNESS,
            bodies=plates
        )
        plate_screw_ext.name = "plate_screw_ext"

    bolt_screw_ext = root.extrudes.itemByName("bolt_screw_ext")
    if not bolt_screw_ext:
        profs = screw_sketch.sorted_profiles
        bolt_screw_ext = root.add_one_side_extrude(
            profs[4:8] + profs[12:],
            FeatureOperations.CutFeatureOperation,
            to_entity=BodyHelper(cases[0]).closest_face(Vector(0, 0, 1)),
            offset=-WALL_THICKNESS,
            bodies=cases
        )
        bolt_screw_ext.name = "bolt_screw_ext"

    #################################
    #   holders
    #################################

    lines = pick(plate_sketch.sorted_lines, [-5, -6])
    p1, p2, p3, p4 = sorted(
        [lines[0].startSketchPoint, lines[0].endSketchPoint, lines[1].startSketchPoint, lines[1].endSketchPoint],
        key=lambda p: p.geometry.x
    )
    v1 = Vector(dx=p1.geometry.x + HOLDER_DIST, dy=p1.geometry.y)
    v2 = Vector(dx=p2.geometry.x - HOLDER_DIST, dy=p2.geometry.y)
    v3 = Vector(dx=p3.geometry.x + HOLDER_DIST, dy=p3.geometry.y)
    v4 = Vector(dx=p4.geometry.x - HOLDER_DIST, dy=p4.geometry.y)

    holder_sketch = SketchHelper.wrap(root.sketches.itemByName("holder"))
    if not holder_sketch:
        holder_sketch = SketchHelper(root.sketches.add(plate_plane))
        promicro_ploygons = promicro.get_promicro_holder()
        for p in promicro_ploygons:
            holder_sketch.add_polygon(p.translate(v1))
            holder_sketch.add_polygon(p.translate(v4))
        for p in trrs.get_trrs_holder():
            holder_sketch.add_polygon(p.translate(v2))
            holder_sketch.add_polygon(p.translate(v3))
        holder_sketch.name = "holder"

    holder_ext = root.extrudes.itemByName("holder_ext")
    if not holder_ext:
        holder_ext = root.add_one_side_extrude(
            holder_sketch.profiles,
            FeatureOperations.JoinFeatureOperation,
            distance=HOLDER_HEIGHT,
            bodies=plates,
        )
        holder_ext.name = "holder_ext"

    #################################
    #   breakout
    #################################

    promicro_plane = root.planes.itemByName("promicro")
    if not promicro_plane:
        promicro_plane = root.offset_plane( plate_plane,PROMICRO_Y + PROMICRO_T)
        promicro_plane.name = "promicro"

    promicro_sketch = SketchHelper.wrap(root.sketches.itemByName("promicro"))
    if not promicro_sketch:
        promicro_sketch = SketchHelper.wrap(root.sketches.add(promicro_plane))
        promicro_rect1, promicro_rect2 = promicro.get_promicro_rects()
        promicro_sketch.add_rect(promicro_rect1.translate(v1))
        promicro_sketch.add_rect(promicro_rect1.translate(v4))
        promicro_sketch.add_rect(promicro_rect2.translate(v1))
        promicro_sketch.add_rect(promicro_rect2.translate(v4))
        promicro_sketch.name = "promicro"

    promicro_ext = root.extrudes.itemByName("promicro_ext")
    if not promicro_ext:
        promicro_ext = root.add_one_side_extrude(
            promicro_sketch.profiles,
            FeatureOperations.NewBodyFeatureOperation,
            distance=-PROMICRO_T
        )
        promicro_ext.name = "promicro_ext"
        for index, body in enumerate(ExtrudeHelper(promicro_ext).sorted_bodies):
            body.name = f"promicro_{index + 1}"

    usb_ext1 = root.extrudes.itemByName("usb_ext1")
    if not usb_ext1:
        usb_ext1 = root.add_one_side_extrude(
            promicro_sketch.sorted_profiles[-2:],
            FeatureOperations.NewBodyFeatureOperation,
            distance=USB_H
        )
        usb_ext1.name = "usb_ext1"
        for index, body in enumerate(ExtrudeHelper(usb_ext1).sorted_bodies):
            body.name = f"usb_{index + 1}"

    usbs = [b for b in root.bodies if b.name.startswith("usb")]

    usb_ext2 = root.extrudes.itemByName("usb_ext2")
    if not usb_ext2:
        root.present_bodies(lambda b: b.name.startswith("promicro") or b.name.startswith("usb"))
        usb_ext2 = root.add_simple_extrude(
            map(lambda usb: BodyHelper(usb).closest_face(Vector(dy=1)), usbs),
            FeatureOperations.JoinFeatureOperation,
            distance=USB_H,
        )
        usb_ext2.name = "usb_ext2"
        for index, body in enumerate(ExtrudeHelper(usb_ext2).sorted_bodies):
            body.name = f"promicro_{index+1}"

    promicros = [b for b in root.bodies if b.name.startswith("promicro")]

    trrs_plane = root.planes.itemByName("trrs")
    if not trrs_plane:
        trrs_plane = root.offset_plane(plate_plane, TRRS_T)
        trrs_plane.name = "trrs"

    trrs_sketch = SketchHelper.wrap(root.sketches.itemByName("trrs"))
    if not trrs_sketch:
        trrs_sketch = SketchHelper.wrap(root.sketches.add(trrs_plane))
        trrs_sketch.add_rect(trrs.get_trrs_rect().translate(v2))
        trrs_sketch.add_rect(trrs.get_trrs_rect().translate(v3))
        trrs_sketch.name = "trrs"

    trrs_ext1 = root.extrudes.itemByName("trrs_ext1")
    if not trrs_ext1:
        trrs_ext1 = root.add_one_side_extrude(
            trrs_sketch.profiles,
            FeatureOperations.NewBodyFeatureOperation,
            distance=-TRRS_T,
        )
        trrs_ext1.name = "trrs_ext1"
        for index, body in enumerate(ExtrudeHelper(trrs_ext1).sorted_bodies):
            body.name = f"trrs_{index+1}"

    trrses = [b for b in root.bodies if b.name.startswith("trrs")]

    def trrs_sock(n: int):
        trrs_sock_sketch = SketchHelper.wrap(root.sketches.itemByName(f"trrs{n}_sock"))
        if not trrs_sock_sketch:
            face = BodyHelper(root.bodies.itemByName(f"trrs_{n}")).closest_face(Vector(dy=1))
            trrs_sock_sketch = SketchHelper.wrap(root.sketches.add(face))
            center = trrs_sock_sketch.add_center_point_of_bounding_box(
                trrs_sock_sketch.profiles[0].boundingBox
            )
            trrs_sock_sketch.add_center_circle(
                center,
                TRRS_RADIUS,
            )
            trrs_sock_sketch.name = f"trrs{n}_sock"

        trrs_sock_ext = root.extrudes.itemByName(f"trrs{n}_sock_ext")
        if not trrs_sock_ext:
            trrs_sock_ext = root.add_one_side_extrude(
                trrs_sock_sketch.sorted_profiles[2:3],
                FeatureOperations.JoinFeatureOperation,
                distance=TRRS_L,
                bodies=trrses,
            )
            trrs_sock_ext.name = f"trrs{n}_sock_ext"

    trrs_sock(1)
    trrs_sock(2)

    def breakout(toolbodies, name):
        for i in range(2):
            breakout_name = f"{name}_breakout_{i+1}"
            breakout_ext = root.combines.itemByName(breakout_name)
            if not breakout_ext:
                cut_input = root.combines.createInput(cases[i], toolbodies)
                cut_input.operation = FeatureOperations.CutFeatureOperation
                cut_input.isKeepToolBodies = True
                breakout_ext = root.combines.add(cut_input)
                breakout_ext.name = breakout_name

    breakout(to_collection(trrses), "trrs")
    breakout(to_collection(promicros), "usb")

    root.present_bodies(lambda b: b.name.startswith("case") or b.name.startswith("plate"))
