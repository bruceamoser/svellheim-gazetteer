"""Atlas windows, measured on the approved painted map at 920 pixels wide."""
from pathlib import Path
from PIL import Image

# Section, crop bounds, plate, caption
REGIONS = {
    "The Splintered Fjords": ((0,330,315,560), "hrafnborg-cover", "Hrafnborg, the great harbor of the inner fjords."),
    "The Weeping Coast": ((192,490,698,663), "atlas/wrecks", "Grounded ships in the Mast-Forest off Grátholm."),
    "The Singing Islands": ((0,535,205,662), "atlas/islands", "The warm growing terraces on Eldøy."),
    "Midgard’s Shield": ((232,115,521,395), "titans-stair", "The allied armies at Titan’s Stair during the Second War."),
    "The Iron Bogs": ((72,198,360,348), "atlas/bogs", "Stilt houses and the iron works at Myrkwood."),
    "The Ashen Woods": ((280,270,608,515), "atlas/woods", "Charcoal country on the edge of the burned Greenweald."),
    "The Frozen Steppe": ((488,258,855,460), "atlas/steppe", "Bone carvers working beneath the ribs of the Bone-Fields."),
    "The inland waters": ((115,154,721,576), "ormsund-silver-era", "Grain boats at the mouth of the Ormá during the Silver Era."),
    "The White Waste": ((319,4,915,173), "atlas/ice", "The Frozen City seen through the northern glacier."),
    "The Throat of the World": ((439,92,691,296), "atlas/springs", "Cultivated plots below the northern steam springs."),
}

def prepare_maps():
    destination = Path("maps/regions")
    destination.mkdir(exist_ok=True)
    with Image.open("maps/svellheim-painted-atlas.png") as source:
        scale = source.width / 920
        for name, (bounds, _, _) in REGIONS.items():
            path = destination / (name.lower().replace("’", "").replace(" ", "-") + ".jpg")
            area = source.crop(tuple(round(value * scale) for value in bounds))
            area.convert("RGB").save(path, quality=94, subsampling=0)
