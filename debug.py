from os import path
from .helper import *

logger = open(path.join(path.dirname(__file__), 'debug.log'), 'w')

def formatPoint(p):
    return f"({p.x} {p.y} {p.z})"

def formatRect(rect):
    return f"Rect(max={formatPoint(rect.maxPoint)}, min={formatPoint(rect.minPoint)})"

def formatCircle(circle):
    return f"Circle(center={formatPoint(circle.centerSketchPoint.geometry)}, radius={circle.radius})"

def formatProfile(prof):
    ap = prof.areaProperties()
    return f"Prof(area={ap.area}, center={formatPoint(ap.centroid)})"

def formatLine(line):
    return f"Line(center={get_line_center_tuple(line)}, start={formatPoint(line.startSketchPoint.geometry)}, end={formatPoint(line.endSketchPoint.geometry)})"

def formatFace(face):
    return f"Face({formatPoint(face.centroid)})"

def objectType(entity):
    return f"{entity.objectType}"

def debug(*args):
        logger.write(' '.join(args))
        logger.write('\n')