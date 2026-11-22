"""Build the Campaign World front cover at the World Gazetteer's trim size."""
import subprocess
from pathlib import Path

from PIL import Image
from reportlab.pdfgen.canvas import Canvas

from build_book import ART, AUTHOR, H, W, color_cover_titles


def build():
    output = Path("output/pdf/Svellheim-Campaign-World-cover")
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = output.with_suffix(".pdf")
    canvas = Canvas(str(pdf), pagesize=(W, H))
    canvas.setTitle("Svellheim — Campaign World")
    canvas.setAuthor(AUTHOR)
    painting = ART / "harald-on-the-throne.png"
    with Image.open(painting) as source:
        scale = max(W / source.width, H / source.height)
        width, height = source.width * scale, source.height * scale
    canvas.drawImage(str(painting), (W - width) / 2, (H - height) / 2, width, height)
    color_cover_titles(canvas, "CAMPAIGN WORLD")
    canvas.showPage()
    canvas.save()
    subprocess.run(["pdftoppm", "-singlefile", "-scale-to", "1500", "-jpeg",
                    "-jpegopt", "quality=96", str(pdf), str(output)], check=True)


if __name__ == "__main__":
    build()
