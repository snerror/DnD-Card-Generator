import math
import yaml
import argparse
import pathlib

from reportlab.pdfbase.ttfonts import TTFError
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from fonts import FreeFonts, AccurateFonts
from generator import MonsterCard, ItemCard
from export import ExportCards
from card_item import *
from card_monster import *


ASSET_DIR = pathlib.Path(__file__).parent.resolve() / "assets"


def ExistingFile(p):
    """Argparse type for absolute paths that exist"""
    p = pathlib.Path(p).absolute()
    if p.exists():
        return p
    else:
        raise argparse.ArgumentTypeError(f"`{p}` does not exist")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Generate D&D cards.")
    parser.add_argument(
        "-o",
        "--out",
        help="Output file path",
        action="store",
        default="cards.pdf",
        dest="output_path",
        metavar="output_path",
        type=lambda p: pathlib.Path(p).absolute(),
    )
    parser.add_argument(
        "input",
        help="Path to input YAML file",
        action="store",
        type=ExistingFile,
    )
    parser.add_argument(
        "-f",
        "--fonts",
        help="What fonts to use when generating cards",
        action="store",
        default="free",
        choices=["free", "accurate"],
        dest="fonts",
    )
    parser.add_argument(
        "-b",
        "--bleed",
        help="How many millimeters of print bleed radius to add around each card.",
        action="store",
        default=0,
        type=lambda b: float(b) * mm,
    )
    parser.add_argument(
        "-e",
        "--export",
        help="Export as single cards or as a grid",
        action="store",
        default="single",
        choices=["single", "grid"],
        dest="export",
    )
    background_group = parser.add_mutually_exclusive_group()
    background_group.add_argument(
        "--no-bg",
        help="Do not add the 'parchment' effect background.",
        action="store_const",
        const=None,
        default=ASSET_DIR / "background.png",
        dest="background",
    )
    background_group.add_argument(
        "--bg",
        help="Custom background image to use",
        action="store",
        dest="background",
        type=ExistingFile,
    )

    args = parser.parse_args()

    fonts = None
    if args.fonts == "accurate":
        try:
            fonts = AccurateFonts()
        except TTFError:
            raise Exception(
                "Failed to load accurate fonts, are you sure you used the correct file names?"
            )
    else:
        fonts = FreeFonts()

    canvas = canvas.Canvas(str(args.output_path), pagesize=A4)

    with open(args.input, "r") as stream:
        try:
            entries = yaml.load(stream, Loader=yaml.SafeLoader)
        except yaml.YAMLError as exc:
            print(exc)
            exit()

    cards = []

    for entry in entries:
        image_path = None
        if "image_path" in entry:
            image_path = pathlib.Path(entry["image_path"])
            if not image_path.is_absolute():
                image_path = (args.input.parent / image_path).absolute()
            if not image_path.exists():
                raise ValueError(
                    "Invalid `image_path` in `{}`: {}".format(
                        entry["title"], entry["image_path"]
                    )
                )

        if entry.get("type") == None or entry.get("type") == "monster":
            card = MonsterCard(
                **entry,
                background=args.background,
                bleed=args.bleed,
            )
        elif entry.get("type") == "item":
            card = ItemCard(
                **entry,
                background=args.background,
                bleed=args.bleed,
            )

        cards += [card]

    if len(cards) == 0:
        print("No cards to generate")
        exit()

    export = ExportCards(cards, canvas)
    if args.export == "grid":
        export.export_grid()
    else:
        export.export_singles()

    canvas.save()
