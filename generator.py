import adsk.core

from .layout import Layout, HoleCreator
from typing import List

def cm(s):
    return s * 10.0

def mm(s):
    return s / 10.0

def point3d(x, y, z=0):
    return adsk.core.Point3D.create(mm(x), mm(y), mm(z))

def add_polygon(lines, points: List[tuple]):
    points = [ point3d(x, y) for x, y in points ]
    l = len(points)
    for i in range(l):
        lines.addByTwoPoints(points[i], points[(i + 1) % l])

def find_item_by_name(collection, name):
    for i in range(collection.count):
        if collection.item(i).name == name:
            return name
    return None

def find_point(sketch, cx, cy):
    for point in sketch.sketchPoints:
        if point.geometry.x == mm(cx) and point.geometry.y == mm(cy):
            return point

def main(app: adsk.core.Application):
    layout = Layout.from_file(r'C:\Users\Klesh\Desktop\ks63\ks-63.json')
    ui  = app.userInterface
    # doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = app.activeProduct
    rootComp = design.rootComponent
    bodies = rootComp.bRepBodies
    sketches = rootComp.sketches
    extrudes = rootComp.features.extrudeFeatures
    fillets = rootComp.features.filletFeatures
    planes: adsk.core.Planes = rootComp.constructionPlanes

    def prompt_kle_json():
        fileDlg = ui.createFileDialog()
        fileDlg.isMultiSelectEnabled = False
        fileDlg.title = 'Keyboard Layout Editor  JSON file'
        fileDlg.filter = '*.json'
        dlgResult = fileDlg.showOpen()
        if dlgResult == adsk.core.DialogResults.DialogOK:
            return fileDlg.filename

    panel_plane = find_item_by_name(planes, 'panel_plane')
    if not panel_plane:
        xyPlane = rootComp.xYConstructionPlane
        xySketch = sketches.add(xyPlane)
        xySketch = 'panel_plane'
        p1 = xySketch.sketchPoints.add(point3d(0, 0, 25))
        p2 = xySketch.sketchPoints.add(point3d(50, 0, 25))
        p3 = xySketch.sketchPoints.add(point3d(0, layout.cy1, 35))
        panel_plane_input = planes.createInput()
        panel_plane_input.setByThreePoints(p1, p2, p3)
        panel_plane = planes.add(panel_plane_input)
        panel_plane.name = 'panel_plane'

    panel_top_sketch = sketches.itemByName('panel_top')
    if not panel_top_sketch:
        panel_top_sketch = sketches.add(panel_plane)
        panel_top_sketch.name = 'panel_top'

    panel = bodies.itemByName('panel')
    if not panel:
        panel_top_lines = panel_top_sketch.sketchCurves.sketchLines
        for key in layout.keys:
            add_polygon(panel_top_lines, key.hole.points)
        panel_top_lines.addTwoPointRectangle(point3d(layout.cx1, layout.cy1), point3d(layout.cx2, layout.cy2))
        # seems profiles are ordered ascendingly
        prof = panel_top_sketch.profiles.item(panel_top_sketch.profiles.count - 1)
        dist = adsk.core.ValueInput.createByReal(mm(1.5))
        panel_top_ext = extrudes.addSimple(prof, dist, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        panel_top_ext.name = 'panel_top_ext'
        panel = panel_top_ext.bodies.item(0)
        panel.name = 'panel'

    panel_top_ext = extrudes.itemByName('panel_top_ext')
    top_face = panel_top_ext.startFaces.item(0)
    
    # create single 2u panel for testing #2
    # hole_creator = HoleCreator()
    # add_polygon(hole_creator.points_2u)
    # lines.addTwoPointRectangle(point3d(-19, 8.5), point3d(19, -11.5))

    panel_bottom_sketch = sketches.itemByName('panel_bottom')
    if not panel_bottom_sketch:
        panel_bottom_sketch = sketches.add(panel_plane)
        panel_bottom_sketch.name = 'panel_bottom'

    panel_bottom_ext = extrudes.itemByName('panel_bottom_ext')
    if not panel_bottom_ext:
        panel_bottom_lines = panel_bottom_sketch.sketchCurves.sketchLines
        for key in layout.keys:
            panel_bottom_lines.addTwoPointRectangle(point3d(key.hole.cx1, key.hole.cy1), point3d(key.hole.cx2, key.hole.cy2))
        panel_bottom_lines.addTwoPointRectangle(point3d(layout.cx1, layout.cy1), point3d(layout.cx2, layout.cy2))
        prof = panel_bottom_sketch.profiles.item(panel_bottom_sketch.profiles.count - 1)
        dist = adsk.core.ValueInput.createByReal(mm(-1.5))
        panel_bottom_ext = extrudes.addSimple(prof, dist, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        panel_bottom_ext.name = 'panel_bottom_ext'

    bottom_face = panel_bottom_ext.endFaces.item(0)
    # [top_face, bottom_face] = sorted(panel.faces, key=lambda f: f.area, reverse=True)[0:2]

    wall_sketch = sketches.itemByName('wall')
    if not wall_sketch:
        wall_sketch = sketches.add(rootComp.xYConstructionPlane)
        wall_sketch_lines = wall_sketch.sketchCurves.sketchLines

        # find project points
        [top_face, bottom_face] = sorted(panel.faces, key=lambda f: f.area, reverse=True)[0:2]
        tl = bottom_face.vertices.item(0)
        for p in bottom_face.vertices:
            if p.geometry.y >= tl.geometry.y and p.geometry.x < tl.geometry.x:
                tl = p
        br = top_face.vertices.item(0)
        for p in top_face.vertices:
            if p.geometry.y <= br.geometry.y and p.geometry.x > br.geometry.x:
                br = p

        ptl = wall_sketch.project(tl).item(0)
        pbr = wall_sketch.project(br).item(0)
        wall_sketch_lines.addTwoPointRectangle(ptl, pbr)
        itl = point3d(cm(ptl.geometry.x + 0.2), cm(ptl.geometry.y - 0.2))
        ibr = point3d(cm(pbr.geometry.x - 0.2), cm(pbr.geometry.y + 0.2))
        wall_sketch_lines.addTwoPointRectangle(itl, ibr)
        wall_sketch.name = 'wall'

    wall_ext = extrudes.itemByName('wall_ext')
    if not wall_ext:
        prof = wall_sketch.profiles.item(0)
        ext_input = extrudes.createInput(prof, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        to_entity = adsk.fusion.ToEntityExtentDefinition.create(top_face, False)
        ext_input.setOneSideExtent(to_entity, adsk.fusion.ExtentDirections.PositiveExtentDirection)
        wall_ext = extrudes.add(ext_input)
        wall_ext.name = 'wall_ext'

    wall_fillet = fillets.itemByName('wall_fillet')
    if not wall_fillet:
        edges = adsk.core.ObjectCollection.create()
        for edge in panel.edges:
            if edge.startVertex.geometry.z == 0 and edge.endVertex.geometry.z > 0:
                edges.add(edge)
        radius = adsk.core.ValueInput.createByReal(mm(5))
        fillet_input = fillets.createInput()
        fillet_input.addConstantRadiusEdgeSet(edges, radius, True)
        fillet_input.isRollingBallCorner = True
        wall_fillet = fillets.add(fillet_input)
        wall_fillet.name = 'wall_fillet'

    plate_plane = planes.itemByName('plate')
    if not plate_plane:
        plane_input = planes.createInput()
        offset = adsk.core.ValueInput.createByReal(mm(1))
        plane_input.setByOffset(rootComp.xYConstructionPlane, offset)
        plate_plane = planes.add(plane_input)
        plate_plane.name = 'plate'

    plate_sketch = sketches.itemByName('plate')
    if not plate_sketch:
        plate_sketch = sketches.add(plate_plane)
        plate_sketch.projectCutEdges(panel)
        plate_sketch.name = 'plate'
        outer_profile = plate_sketch.profiles.item(0)
        for loop in outer_profile.profileLoops:
            if loop.isOuter:
                for curve in loop.profileCurves:
                    curve.sketchEntity.deleteMe()
        prof = plate_sketch.profiles.item(0)
        curves = adsk.core.ObjectCollection.create()
        for pc in prof.profileLoops.item(0).profileCurves:
            curves.add(pc.sketchEntity)
        plate_sketch.offset(curves, point3d(0, 0, 0), mm(1))

    plate = bodies.itemByName('plate')
    if not plate:
        prof = plate_sketch.profiles.item(1)
        dist = adsk.core.ValueInput.createByReal(mm(2))
        plate_ext = extrudes.addSimple(prof, dist, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        plate_ext.name = 'plate_ext'
        plate = plate_ext.bodies.item(0)
        plate.name = 'plate'


    # create single 2u panel for testing #2
    # lines.addTwoPointRectangle(point3d(-18, 7.5), point3d(18, -10.5))
    # prof = profiles.item(1)
    # dist = adsk.core.ValueInput.createByReal(cm(-3))
    # extrudes.addSimple(prof, dist, adsk.fusion.FeatureOperations.JoinFeatureOperation)