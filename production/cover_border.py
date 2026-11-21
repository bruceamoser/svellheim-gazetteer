"""Vector interlace shared by the Svellheim covers and interiors."""
from math import ceil, cos, pi, sin
from reportlab.lib.colors import HexColor

INK = "#32271e"
BRONZE = "#875a2d"
GOLD = "#e1b765"
GLINT = "#f5d58a"


def polyline(canvas, points):
    path = canvas.beginPath()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    canvas.drawPath(path)


def strand(canvas, points, widths):
    for color, width in zip((INK, BRONZE, GOLD, GLINT), widths):
        canvas.setStrokeColor(HexColor(color))
        canvas.setLineWidth(width)
        polyline(canvas, points)


def braid(canvas, start, end, vertical=False):
    length = (end[1]-start[1]) if vertical else (end[0]-start[0])
    cycles = max(1, round(length/48))
    period = length/cycles

    def samples(thread, first, last):
        count = max(4, ceil((last-first)/1.4))
        points = []
        for j in range(count+1):
            d = first+(last-first)*j/count
            lateral = 4.1*sin(2*pi*(d/period+thread/3))
            points.append((start[0]+lateral,start[1]+d) if vertical
                          else (start[0]+d,start[1]+lateral))
        return points

    widths = (3.0, 2.35, 1.65, .36)
    for thread in range(3):
        strand(canvas,samples(thread,0,length),widths)
    # Reverse the crossing at the opposite rail.
    # Three sinusoids cross six times per repeat. Alternating the top strand
    # gives every ribbon a visible underpass on both sides.
    for cycle in range(cycles):
        for step in range(6):
            phase = (1+2*step)/12
            offsets = [sin(2*pi*(phase+t/3)) for t in range(3)]
            _,a,b = min((abs(offsets[a]-offsets[b]),a,b)
                        for a,b in ((0,1),(1,2),(2,0)))
            choose = max if offsets[a] > 0 else min
            over = choose((a,b), key=lambda t:cos(2*pi*(phase+t/3)))
            center = (cycle+phase)*period
            strand(canvas,samples(over,max(0,center-2.6),min(length,center+2.6)),widths)


def corner(canvas, x, y, angle):
    canvas.saveState()
    canvas.translate(x,y)
    canvas.rotate(angle)
    canvas.setFillColor(HexColor(INK))
    canvas.setStrokeColor(HexColor(GOLD))
    canvas.setLineWidth(.8)
    canvas.circle(0,0,10.8,fill=1)
    canvas.setLineWidth(.4)
    canvas.circle(0,0,9.3)

    def curve(start, end, count):
        points=[]
        for j in range(count+1):
            t=start+(end-start)*j/count
            points.append((2.72*(sin(t)+2*sin(2*t)),2.72*(cos(t)-2*cos(2*t))))
        return points

    widths=(2.0,1.55,1.1,.24)
    strand(canvas,curve(0,2*pi,144),widths)
    for k in range(3):
        start=(2*k+1)*pi/3
        strand(canvas,curve(start,start+pi/3,24),widths)
    canvas.restoreState()


def gold_interlace(canvas, width, height):
    canvas.saveState()
    canvas.setLineCap(1)
    canvas.setLineJoin(1)
    inset = 17
    for offset in (-6,6):
        margin = inset+offset
        for color,weight in ((INK,2),(GOLD,.7)):
            canvas.setStrokeColor(HexColor(color))
            canvas.setLineWidth(weight)
            canvas.rect(margin,margin,width-2*margin,height-2*margin)
    for y in (inset,height-inset):
        braid(canvas,(inset+7,y),(width-inset-7,y))
    for x in (inset,width-inset):
        braid(canvas,(x,inset+7),(x,height-inset-7),vertical=True)
    for x,y,angle in ((inset,inset,-45),(width-inset,inset,45),
                      (width-inset,height-inset,135),(inset,height-inset,225)):
        corner(canvas,x,y,angle)
    canvas.restoreState()

def interior_braid(canvas, x, y, width):
    """Place a reusable vector ribbon between two small gilt finials."""
    scale = .48
    name = f"interior_braid_{int(width)}"
    if not canvas.hasForm(name):
        canvas.beginForm(name, -3, -4, width+3, 4)
        canvas.scale(scale, scale)
        canvas.setLineCap(1)
        canvas.setLineJoin(1)
        length = width / scale
        braid(canvas, (0, 0), (length, 0))
        for end in (0, length):
            canvas.setStrokeColor(HexColor(INK))
            canvas.setFillColor(HexColor(GOLD))
            canvas.setLineWidth(.8)
            canvas.circle(end, 0, 4.7, fill=1)
        canvas.endForm()
    canvas.saveState()
    canvas.translate(x, y)
    canvas.doForm(name)
    canvas.restoreState()
