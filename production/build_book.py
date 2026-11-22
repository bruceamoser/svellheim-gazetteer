"""Build the illustrated reading edition from the Markdown chapters."""
from cover_border import gold_interlace, interior_braid
from regional_art import REGIONS, prepare_maps
from math import cos, radians, sin
from reportlab.graphics.shapes import Circle, Drawing, Line, String, Wedge
from io import BytesIO
from functools import lru_cache
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as Raster, ImageOps
from reportlab.lib.colors import HexColor
from reportlab.lib.sequencer import _format_i as lower_roman
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, FrameBreak, Image, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, ParagraphAndImage, Spacer, KeepTogether, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
ART = Path("artwork")
FILES = [Path("gazetteer")/name for name in (
    "03-history.md", "01-the-age-of-embers.md", "04-atlas.md",
    "02-hrafnborg.md", "05-ancestries.md", "06-pantheon.md", "07-reckonings.md",
)]
W, H = 612, 792
M = 40
GUTTER = 22
COLUMN = (W - 2*M - GUTTER) / 2
INK, BLUE, RUST = "#232c32", "#263e50", "#934d30"
for face, path in {
    "Book": "noto/NotoSerif-Regular", "BookBold": "noto/NotoSerif-Bold",
    "BookItalic": "noto/NotoSerif-Italic", "Label": "lato/Lato-Bold"
}.items():
    pdfmetrics.registerFont(TTFont(face, f"/usr/share/fonts/truetype/{path}.ttf"))
pdfmetrics.registerFontFamily("Book", normal="Book", bold="BookBold", italic="BookItalic")

def style(name, font, size, leading, color, **kw):
    return ParagraphStyle(name, fontName=font, fontSize=size, leading=leading,
                          textColor=HexColor(color), **kw)

body = style("body", "Book", 10, 13.35, INK, spaceAfter=5, allowWidows=0, allowOrphans=0)
atlas_body = ParagraphStyle("atlas text",parent=body,leading=13.5,spaceAfter=5)
label = style("label", "Label", 9, 13, RUST, spaceAfter=9, keepWithNext=True)
heads = [None] + [style("h"+str(i), "BookBold", size, lead, BLUE, keepWithNext=True,
                       spaceBefore=before, spaceAfter=after)
                 for i,size,lead,before,after in [(1,26,30,0,10),(2,17,21,10,5),
                                                  (3,14,17,8,4),(4,12,15,6,4)]]
caption = style("caption", "BookItalic", 9, 12, BLUE, spaceBefore=5, spaceAfter=9)
STORIES = sorted(Path("stories").glob("[0-9]*.md"))
PROFILE_NAMES = [p.stem.capitalize() for p in sorted((ART/"peoples").glob("*.png"))]

@lru_cache(maxsize=None)
def jpeg(path):
    with Raster.open(path) as im:
        buf = BytesIO()
        im.convert("RGB").save(buf, format="JPEG", quality=94, subsampling=0)
        return buf.getvalue()

def art(path, width):
    with Raster.open(path) as im:
        return Image(BytesIO(jpeg(path)), width=width, height=width*im.height/im.width)

SPOTS = {
    "How a city came to hold the keys": ("grain-carter", 86, 105, "left"),
    "Settlements of the high ranges": ("cragbound-guide", 80, 114, "right"),
    "Frigg's portion": ("ember-pot", 98, 80, "left"),
    "The names borne at the ford": ("ormsbani-scale", 96, 78, "right"),
    "Frigg, the Hearth-Mother": ("weaving-shuttle", 115, 66, "right"),
}

def spot(name, max_width, max_height):
    with Raster.open(ART/"spots"/(name+".png")) as im:
        scale = min(max_width/im.width, max_height/im.height)
        width, height = im.width*scale, im.height*scale
        im.thumbnail((round(width*4),round(height*4)), Raster.Resampling.LANCZOS)
        buf = BytesIO()
        im.save(buf, format="PNG")
        buf.seek(0)
        return Image(buf, width, height, mask="auto")

def slug(text):
    return re.sub(r'[^\w -]', '', text.lower()).replace(' ', '-')

def inline(text, path):
    def link(m):
        filename, _, section = m[2].partition("#")
        target = "map" if filename.endswith(".png") else (Path(filename).stem if filename else path.stem)
        if section:
            target += "-"+section
        return f'<link href="#{target}" color="{BLUE}">{m[1]}</link>'
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, escape(text))
    text = re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    return re.sub(r'(?<!\w)[*_]([^*_]+?)[*_](?!\w)',r'<i>\1</i>',text)

def cover(c, doc):
    c.drawImage(ImageReader(BytesIO(jpeg(ART/"hrafnborg-cover.png"))), (W-H*1122/1402)/2, 0, H*1122/1402,H)
    c.drawImage(str(ART/"svellheim-logo.png"), 48,H-202,W-96,(W-96)/3,mask="auto")
    c.setFillColor(HexColor("#f8ecdb"))
    c.setFont("Label",15)
    c.drawCentredString(W/2,H-222,"WORLD GAZETTEER")
    gold_interlace(c,W,H)

def stories_cover(c, doc):
    width, height = doc.pagesize
    with Raster.open(ART/"stories-cover.png") as source:
        c.drawImage(ImageReader(source.convert("L")),0,0,width,height)
    c.setFillColor(HexColor("#171717"))
    c.setFont("BookBold",20)
    c.drawCentredString(width/2,height-54,"Stories of")
    c.setFont("BookBold",38)
    c.drawCentredString(width/2,height-99,"Svellheim")
    gold_interlace(c,width,height)

def publication_page(source, heading_style, book_style, credit_style):
    blocks = source.read_text().strip().split("\n\n")
    title = blocks[0].removeprefix("# ")
    opening = Paragraph(escape(title), heading_style)
    opening.destination = ("publication", title, 1)
    flow = [opening, Paragraph(escape(blocks[1].removeprefix("## ")), book_style), Spacer(1,18)]
    for block in blocks[2:]:
        lines = []
        for line in block.splitlines():
            value = escape(line.strip())
            if value.startswith("www."):
                value = f'<link href="https://{value}">{value}</link>'
            lines.append(value)
        flow.append(Paragraph("<br/>".join(lines), credit_style))
        flow.append(Spacer(1,10))
    return flow


def manuscript_image(path, legend):
    with Raster.open(path) as source:
        im = source.copy()
    if path.parent.name == "peoples":
        bounds = im.getchannel("A").point(lambda a: 255 if a > 20 else 0).getbbox()
        im = im.crop(bounds)
        width = min(COLUMN, 258 * im.width / im.height)
        height = width * im.height / im.width
        im.thumbnail((round(width*4),round(height*4)),Raster.Resampling.LANCZOS)
        buf = BytesIO()
        im.save(buf,format="PNG")
        return [Image(BytesIO(buf.getvalue()),width,height,mask="auto"),Spacer(1,8)]
    if path.parent.name == "regions":
        # Show the complete map window. Lettering at its edges is never clipped by a frame.
        height_limit = 115 if path.stem == "the-splintered-fjords" else 167
        width = min(COLUMN, height_limit * im.width / im.height)
        return [art(path,width),Spacer(1,7)]
    height = 88 if path.stem == "hrafnborg-cover" else 118
    im = ImageOps.fit(im.convert("RGB"),(int(COLUMN*4),height*4),centering=(.5,.52))
    buf = BytesIO()
    im.save(buf, format="JPEG", quality=95)
    return [KeepTogether([Image(BytesIO(buf.getvalue()),COLUMN,height),Paragraph(escape(legend),caption)])]


TAILPIECES = {
    "03-history": "harbor-tally",
    "01-the-age-of-embers": "ember-pot", "02-hrafnborg": "store-key",
    "06-pantheon": "weaving-shuttle", "07-reckonings": "harbor-tally",
}


class Tailpiece(Flowable):
    """Set a small illustration in the space left below a section's final paragraph."""
    _ZEROSIZE = True

    def __init__(self, name):
        super().__init__()
        self.name = name

    def wrap(self, available_width, available_height):
        self.image = None
        if available_height < 62:
            return 0, 0
        self.image = spot(self.name, available_width * .8, min(150, available_height - 14))
        self.width, self.height = available_width, self.image.drawHeight + 12
        return self.width, self.height

    def draw(self):
        if self.image:
            self.image.drawOn(self.canv, (self.width-self.image.drawWidth)/2, 0)


def footer(c, doc):
    c.setStrokeColor(HexColor("#cdbfae"))
    ribbon = 152
    left = (W-ribbon)/2
    c.setLineWidth(.5)
    c.line(M,34,left,34)
    c.line(left+ribbon,34,W-M,34)
    interior_braid(c,left,34,ribbon)
    c.setFillColor(HexColor(BLUE))
    c.setFont("Label",8)
    c.drawString(M,20,doc.section.upper())
    c.drawRightString(W-M,20,str(doc.page))

def atlas(c, doc):
    doc.starts["map"] = doc.page
    c.bookmarkPage("map")
    c.addOutlineEntry("Illustrated map","map",0)
    c.drawImage(ImageReader(BytesIO(jpeg("maps/svellheim-painted-atlas.png"))),8,8,H-16,W-16,
                preserveAspectRatio=True,anchor="c")

class Book(BaseDocTemplate):
    section = "Svellheim"
    def afterFlowable(self, item):
        if hasattr(item,"destination"):
            key, title, level = item.destination
            self.canv.bookmarkHorizontalAbsolute(key,self.frame._y+item.height)
            if level <= 3:
                self.canv.addOutlineEntry(title,key,level-1,closed=level==2)
            if level <= 2:
                self.starts[key] = self.page
            if level == 1:
                self.section = title

def year_wheel(rows):
    center = COLUMN / 2
    guide = Drawing(COLUMN, 180)
    months = [row[col].getPlainText() for col in (1, 3) for row in rows[1:]]
    for i, month in enumerate(months):
        angle = 90 - 30 * i
        tint = "#b97745" if i < 6 else "#527486"
        guide.add(Wedge(center, 90, 65, angle-30, angle, fillColor=HexColor(tint),
                        strokeColor=HexColor("#ffffff"), strokeWidth=1))
        dx, dy = cos(radians(angle-15)), sin(radians(angle-15))
        guide.add(String(center+54*dx, 87+54*dy, str(i+1), fontName="Label",
                         fontSize=9, textAnchor="middle", fillColor=HexColor("#ffffff")))
        guide.add(String(center+70*dx, 87+78*dy, month, fontName="Book", fontSize=10,
                         textAnchor="start" if dx > 0 else "end", fillColor=HexColor(BLUE)))
    guide.add(Circle(center,90,42,fillColor=HexColor("#faf7ef"),strokeWidth=0))
    for y, word in [(94,"360 days"),(79,"of the year")]:
        guide.add(String(center,y,word,fontName="Book",fontSize=10,textAnchor="middle"))
    return guide


def layout_gazetteer(path, pages):
    files = FILES
    doc = Book(str(path),pagesize=(W,H),title="Svellheim — World Gazetteer")
    doc.starts = {}
    def frame(left, width):
        return Frame(left, 45, width, H-85, leftPadding=0, rightPadding=0,
                     topPadding=0, bottomPadding=0)
    columns = [frame(M, COLUMN), frame(M+COLUMN+GUTTER, COLUMN)]
    for key, fn, size in [("cover",cover,(W,H)),("front",footer,(W,H)),("body",footer,(W,H)),("map",atlas,(H,W))]:
        callback = {"onPageEnd": fn} if key in ("body","front") else {"onPage": fn}
        doc.addPageTemplates(PageTemplate(key,columns if key == "body" else [frame(M,W-2*M)],pagesize=size, **callback))
    flow = [Spacer(1,1),NextPageTemplate("front"),PageBreak(),Spacer(1,18),
            Paragraph("SVELLHEIM",label),Paragraph("World Gazetteer",heads[1]),
            Paragraph("Contents",heads[2])]
    toc_style = style("contents","Book",13,18,BLUE)
    toc_page = style("folio","Label",12,18,RUST,alignment=2)
    descriptions = [
        "The first kingdoms, the great wars, and Harald’s peace",
        "Food, shelter, and belief in the third winter",
        "From the Splintered Fjords to the White Waste",
        "Inside the gates of Harald’s city",
        "The old homelands and the families who left them",
        "The gods at the hearth, on the road, and at sea",
        "Calendar, chronology, languages, worship and the nine worlds",
    ]
    entries = [("Publication and credits","publication",""),("Foreword","foreword",""),("Illustrated map","map","")]
    for idx, manuscript in enumerate(files):
        lines = manuscript.read_text().splitlines()
        entries.append((lines[0][2:],manuscript.stem,escape(descriptions[idx])))
    toc_detail = style("contents detail","Label",9,12,INK,leftIndent=13,spaceBefore=2)
    rows = []
    for title,key,detail in entries:
        title_cell = [Paragraph(f'<link href="#{key}">{escape(title)}</link>',toc_style)]
        if detail:
            title_cell.append(Paragraph(detail,toc_detail))
        rows.append([title_cell,Paragraph(f'<link href="#{key}">{pages.get(key, "")}</link>',toc_page)])
    flow.append(Table(rows,colWidths=[W-2*M-34,34],style=TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),9),
    ])))
    flow.extend([PageBreak(),Spacer(1,44)])
    credit_heading = ParagraphStyle("gazetteer credit heading",parent=heads[1],alignment=1)
    credit_book = ParagraphStyle("gazetteer credit book",parent=heads[2],alignment=1)
    credit_text = style("gazetteer credits","Book",12,18,INK,alignment=1)
    flow.extend(publication_page(Path("editorial/publication.md"),credit_heading,credit_book,credit_text))
    flow.extend([Spacer(1,24),spot("ember-pot",156,136),PageBreak()])
    foreword = Path("editorial/foreword.md").read_text().strip().split("\n\n")
    opening = Paragraph("Foreword",heads[1])
    opening.destination = ("foreword","Foreword",1)
    flow.extend([opening, art(ART/"roadside-shrine.png",(W-2*M)*.93),Spacer(1,10)])
    flow.extend(Paragraph(escape(para),body) for para in foreword[1:])
    flow.extend([NextPageTemplate("map"),PageBreak(),Spacer(1,1)])
    flow.extend([NextPageTemplate("body"),PageBreak()])
    for idx,f in enumerate(files,1):
        if idx>1:
            flow.append(PageBreak())
        current_spot = None
        area_seen = False
        at_belt_start = False
        profile = None
        lines = iter(f.read_text().splitlines())
        for line in lines:
            if not line.strip():continue
            picture = re.fullmatch(r"!\[([^]]+)\]\(([^)]+)\)",line)
            if picture:
                flow.extend(manuscript_image(f.parent/picture[2],picture[1]))
                continue
            if line.startswith("|"):
                rows = []
                while line.startswith("|"):
                    cells = [cell.strip() for cell in line.strip("|").split("|")]
                    if cells[0] != "---":
                        rows.append([Paragraph(escape(cell), caption) for cell in cells])
                    line = next(lines, "")
                if len(rows[0]) == 4:
                    flow.append(year_wheel(rows))
                else:
                    # The spine and its dated stations continue across page breaks.
                    for row in rows[1:]:
                        station = Drawing(11, 13)
                        station.add(Line(5, -5, 5, 18, strokeColor=HexColor(RUST)))
                        station.add(Circle(5, 6, 3, fillColor=HexColor(RUST), strokeWidth=0))
                        row.insert(0, station)
                    rows[0].insert(0, "")
                widths = [43, COLUMN/2-43, 43, COLUMN/2-43] if len(rows[0]) == 4 else [12, 65, COLUMN-77]
                flow.append(Table(rows, colWidths=widths, repeatRows=1, style=TableStyle([
                    ("LEFTPADDING", (0,0), (-1,-1), 3),
                    ("RIGHTPADDING", (0,0), (-1,-1), 3),
                    ("TOPPADDING", (0,0), (-1,-1), 2),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 2),
                    ("BACKGROUND", (0,0), (-1,0), HexColor("#cad9db")),
                    ("ROWBACKGROUNDS", (0,1), (-1,-1), [HexColor("#f7f3e9"), HexColor("#eaf0ef")]),
                    ("LINEBEFORE", (0,1), (0,-1), 3, HexColor(RUST)),
                    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ])))
                flow.append(Spacer(1,10))
                continue
            if line.startswith("#"):
                marks,title = line.split(" ",1)
                if title in ("The spring and the market", "The southern routes"):
                    flow.append(FrameBreak())
                if title == "The ages in living memory and song":
                    flow.append(CondPageBreak(540))
                elif title == "The worlds of the ash":
                    flow.append(CondPageBreak(310))
                current_spot = SPOTS.get(title)
                level=len(marks)
                if f.stem == "04-atlas":
                    if level == 2:
                        if area_seen:
                            flow.append(FrameBreak())
                        at_belt_start = True
                    if title in REGIONS:
                        if area_seen and not at_belt_start:
                            flow.append(FrameBreak())
                        at_belt_start = False
                        area_seen = True
                if f.stem == "05-ancestries":
                    if title in PROFILE_NAMES:
                        profile = title
                        if not area_seen:
                            flow.extend([art(ART/"deepforged-hold.png",COLUMN),Paragraph("Homes beneath Midgard’s Shield.",caption),FrameBreak(),Paragraph("Peoples and homelands",heads[2])])
                            for name, homeland in re.findall(r"^## (\w+)\n\n!.*?\n\n### (.+)$", f.read_text(),re.M):
                                flow.append(Paragraph(f'<link href="#{f.stem}-{slug(name)}"><b>{name}</b></link><br/>{escape(homeland)}',body))
                            area_seen = True
                        flow.append(PageBreak())
                    elif level == 3 and title.startswith("The "):
                        # Sacred accounts occupy the facing column of the same page.
                        if title.split()[1].rstrip(",") in PROFILE_NAMES:
                            flow.append(FrameBreak())
                key=f.stem if level==1 else f.stem+"-"+slug(title)
                if title == "Faith and custom" and profile:
                    key += "-" + slug(profile)
                if level==1:
                    flow.append(Paragraph(f"CHAPTER {idx:02}",label))
                h = Paragraph(escape(title),heads[level])
                h.destination=(key,title,level)
                flow.append(h)
                plates = {
                    "The Silver Era": ("ormsund-silver-era","Grain boats at Ormsund during the Silver Era."),
                    "The battle of Titan's Stair": ("titans-stair","The allied hosts climb the two approaches to Titan’s Stair."),
                    "Caves and mines beneath the mountains": ("deepforged-hold","A child follows the family passage beneath the Shield."),
                    "The Gods of Svellheim": ("brimstead-weavers","The lighthouse weavers at Brimstead remember the drowned."),
                    "The spring and the market": ("hrafnborg-cover","Harbor streets below the Ever-Ember at Hrafnborg."),
                    "The southern routes": ("ormsund-silver-era","Ormsund shipped inland grain to the south during the Silver Era.")
                }
                if title in plates:
                    name, legend = plates[title]
                    plate_width = COLUMN
                    flow.pop()
                    if name == "hrafnborg-cover":
                        flow.append(KeepTogether([h, *manuscript_image(ART/(name+".png"),legend)]))
                    else:
                        flow.append(KeepTogether([h,art(ART/(name+".png"),plate_width),Paragraph(legend,caption)]))
            else:
                text_style = atlas_body if f.stem=="04-atlas" else body
                paragraph = Paragraph(inline(line,f),text_style)
                if f.stem == "02-hrafnborg" and line.startswith("The **Chain-Boom**"):
                    current_spot = ("ferrymans-oar", 100, 64, "right")
                if current_spot:
                    name, width, height, side = current_spot
                    paragraph = ParagraphAndImage(paragraph, spot(name, min(width,78), height),
                                                  xpad=7, ypad=5, side=side)
                    current_spot = None
                flow.append(paragraph)
        if f.stem in TAILPIECES:
            flow.append(Tailpiece(TAILPIECES[f.stem]))
    doc.build(flow)
    return doc.starts


def layout_stories(path, pages):
    width, height = 432, 648
    side_margin = 50
    text_width = width - 2*side_margin
    doc = Book(str(path), pagesize=(width,height), title="Stories of Svellheim")
    doc.starts = {}
    serif = "Book"
    italic = "BookItalic"
    fonts = Path.home()/".local/share/fonts/hol"
    if all((fonts/name).exists() for name in ("CrimsonText-Regular.ttf","CrimsonText-Italic.ttf")):
        for name in ("Regular","Italic"):
            pdfmetrics.registerFont(TTFont("Crimson"+name,str(fonts/("CrimsonText-"+name+".ttf"))))
        serif, italic = "CrimsonRegular", "CrimsonItalic"
        pdfmetrics.registerFontFamily(serif,normal=serif,italic=italic)

    black = "#221f1b"
    prose = style("novel",serif,12.3,15.6,black,firstLineIndent=14,
                  alignment=4,allowWidows=0,allowOrphans=0)
    first = ParagraphStyle("novel first",parent=prose,firstLineIndent=0)
    title = style("novel title",serif,28,34,black,alignment=1,spaceAfter=18,keepWithNext=True)
    chapter = style("novel chapter",italic,15,19,black,alignment=1,spaceAfter=10,keepWithNext=True)
    small = style("novel small",serif,10.5,13,black,alignment=1)
    story_index = style("story contents",serif,14,17,black,spaceBefore=5)
    chapter_index = style("chapter contents",serif,11.5,15,black,leftIndent=15)
    first_key = STORIES[0].stem

    def folio(c, book):
        page = book.page
        start = book.starts.get(first_key)
        if page == 1:
            c.addPageLabel(0,prefix="Cover")
        elif page == 2:
            c.addPageLabel(1,style="ROMAN_LOWER",start=1)
        else:
            if page == start:
                c.addPageLabel(page-1,style="ARABIC",start=1)
            number = str(page-start+1) if start else lower_roman(page-1)
            c.setFont(serif,10.5)
            c.setFillColor(HexColor(black))
            c.drawCentredString(width/2,28,number)

    def frame(name):
        return Frame(side_margin,50,text_width,height-102,id=name,leftPadding=0,rightPadding=0,
                     topPadding=0,bottomPadding=0)

    doc.addPageTemplates([PageTemplate("cover",[frame("cover")],onPage=stories_cover,onPageEnd=folio),
                          PageTemplate("novel",[frame("text")],onPageEnd=folio)])

    def heading(text, key, level, face=title, bookmark=None):
        h = Paragraph(escape(text),face)
        h.destination = (key,bookmark or text,level)
        return h

    flow = [Spacer(1,1),NextPageTemplate("novel"),PageBreak(),Spacer(1,132),
            Paragraph("Stories of Svellheim",title),Paragraph("Seven short stories",chapter),
            Spacer(1,88),Paragraph("World created by Bruce Moser",small)]
    def contents_row(name, key, face, number):
        linked = f'<link href="#{key}">{escape(name)}</link>'
        right = ParagraphStyle("right folio",parent=face,alignment=2,leftIndent=0)
        return [Paragraph(linked,face),Paragraph(f'<link href="#{key}">{number}</link>',right)]

    manuscripts = [(f,f.read_text().strip().split("\n\n")) for f in STORIES]
    rows = [contents_row(name,key,story_index,lower_roman(pages[key]-1) if pages else "")
            for name,key in (("Publication and credits","publication"),("Foreword","foreword"))]
    # Keep the chapters of each story together across the two contents pages.
    for group in (manuscripts[:3], manuscripts[3:]):
        for f,blocks in group:
            for block in blocks:
                if block.startswith("# "):
                    name, key, face = block[2:], f.stem, story_index
                elif block.startswith("## "):
                    name = block[3:]
                    key, face = f.stem+"-"+slug(name), chapter_index
                else:
                    continue
                number = pages[key]-pages[first_key]+1 if pages else ""
                rows.append(contents_row(name,key,face,number))
        flow.extend([PageBreak(),Paragraph("Contents",title),Table(
            rows,colWidths=[text_width-24,24],hAlign="CENTER",style=TableStyle([
                ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),
                ("RIGHTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),0),
                ("BOTTOMPADDING",(0,0),(-1,-1),1),
                *[("TOPPADDING",(0,i),(-1,i),7) for i,row in enumerate(rows) if row[0].style is story_index],
            ]))])
        rows = []
    flow.extend([PageBreak(),Spacer(1,48)])
    flow.extend(publication_page(Path("stories/publication.md"),title,chapter,small))
    flow.extend([PageBreak(),Spacer(1,16),heading("Foreword","foreword",1)])
    for i,para in enumerate(Path("stories/foreword.md").read_text().strip().split("\n\n")[1:]):
        flow.append(Paragraph(escape(para),prose if i else first))
    for f,blocks in manuscripts:
        flow.extend([PageBreak(),Spacer(1,48),heading(blocks[0][2:],f.stem,1)])
        opens = True
        for block in blocks[1:]:
            if block.startswith("## "):
                name = block[3:]
                if not opens:
                    flow.extend([CondPageBreak(104),Spacer(1,16)])
                flow.append(heading(name,f.stem+"-"+slug(name),2,chapter))
                opens = True
            else:
                flow.append(Paragraph(inline(block,f),first if opens else prose))
                opens = False
    doc.build(flow)
    return doc.starts


if __name__ == "__main__":
    prepare_maps()
    cli = shutil.which("pdfcraft-cli") or str(Path.home()/".local/bin/pdfcraft-cli")
    for stories, filename, title in [
        (False,"Svellheim-World-Gazetteer.pdf","Svellheim — World Gazetteer"),
        (True,"Stories-of-Svellheim.pdf","Stories of Svellheim"),
    ]:
        output = Path("output/pdf")/filename
        output.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory() as temp:
            draft = Path(temp)/"typeset.pdf"
            typeset = layout_stories if stories else layout_gazetteer
            pages = typeset(draft,{})
            assert pages == typeset(draft,pages)
            subprocess.run([cli,"edit",str(draft),"--out",str(Path(temp)/"book.pdf"),
                            "--title",title,"--author","Bruce Moser"],check=True)
            shutil.copyfile(Path(temp)/"book.pdf",output)
