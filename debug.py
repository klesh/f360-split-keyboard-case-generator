
logger = open(path.join(path.dirname(__file__), 'debug.log'), 'w')

def formatPoint(p):
    return f"({p.x} {p.y} {p.z})"

def formatBox(box):
    return f"Box(max={formatPoint(box.maxPoint)}, min={formatPoint(box.minPoint)})"

def formatCircle(circle):
    return f"Circle(center={formatPoint(circle.centerSketchPoint.geometry)}, radius={circle.radius})"

def formatProfile(prof):
    ap = prof.areaProperties()
    return f"Prof(area={ap.area}, center={formatPoint(ap.centroid)})"

def formatLine(line):
    return f"Line(center={get_line_center_tuple(line)}, start={formatPoint(line.startSketchPoint.geometry)}, end={formatPoint(line.endSketchPoint.geometry)})"

def debug(*args):
        logger.write(' '.join(args))
        logger.write('\n')