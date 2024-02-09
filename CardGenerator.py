import math
import yaml
import argparse
import pathlib
import itertools

from copy import copy
from abc import ABC

from reportlab.pdfbase.ttfonts import TTFError
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.platypus.flowables import Flowable, Spacer
from fonts import FreeFonts, AccurateFonts
from card import TemplateTooSmall
from card_item import *
from card_monster import *


ASSET_DIR = pathlib.Path(__file__).parent.resolve() / "assets"


def draw_cards_canvas(canvas, cards, invert=False):
    card_width = 63 * mm
    card_height = 89 * mm

    cards_per_row = math.floor(A4[0] / card_width)
    rows_per_page = math.floor(A4[1] / card_height)

    x = 0 if invert == False else A4[0] - (card_width * cards_per_row)
    y = A4[1] - card_height

    current_col, current_row = 0, 0
    i = 0

    if invert:
        cards = mix_array(cards, cards_per_row)

    for card in cards:
        card.draw(canvas, x, y, front=invert)

        current_col += 1
        x += card_width
        if current_col >= cards_per_row:
            current_row += 1
            current_col = 0
            x = 0 if invert == False else A4[0] - (card_width * cards_per_row)
            y -= card_height
            if current_row >= rows_per_page:
                canvas.showPage()
                current_row, current_col = 0, 0
                x, y = 0, A4[1] - card_height

        i += 1


def mix_array(arr, segment_size):
    # Determine the number of segments
    num_segments = len(arr) // segment_size + (1 if len(arr) % segment_size != 0 else 0)

    # Process each segment
    new_order = []
    for i in range(num_segments):
        start = i * segment_size
        end = min(start + segment_size, len(arr))
        segment = arr[start:end]

        # Reverse the segment
        segment = segment[::-1]

        new_order.extend(segment)

    return new_order


def ExistingFile(p):
    """Argparse type for absolute paths that exist"""
    p = pathlib.Path(p).absolute()
    if p.exists():
        return p
    else:
        raise argparse.ArgumentTypeError(f"`{p}` does not exist")


class CardGenerator(ABC):
    sizes = []  # Set by subclass

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def draw(self, canvas, x=0, y=0, front=True):
        for size, split in itertools.product(self.sizes, [False, True]):
            try:
                card_layout = size(*self._args, **self._kwargs)
                if front:
                    card_layout.draw_front(canvas, x, y)
                else:
                    card_layout.draw_back(canvas, split, x, y)
                break
            except TemplateTooSmall:
                # Reset the page
                canvas._restartAccumulators()
                canvas.init_graphics_state()
                canvas.state_stack = []
        else:
            print("Could not fit {}".format(self._kwargs["title"]))


class MonsterCard(CardGenerator):
    sizes = [MonsterCardSmall, MonsterCardLarge, MonsterCardEpic, MonsterCardSuperEpic]


class ItemCard(CardGenerator):
    sizes = [ItemCardSmall]  # maybe more in the future


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Generate D&D cards.")
    parser.add_argument(
        "-t",
        "--type",
        help="What type of cards to generate",
        action="store",
        default="monster",
        choices=["monster", "item"],
        dest="type",
    )
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

    max_cards = 9
    pages_needed = math.ceil(len(cards) / max_cards)

    for i in range(pages_needed):
        c = cards[i * max_cards : i * max_cards + max_cards]
        draw_cards_canvas(canvas, c, False)
        canvas.showPage()
        draw_cards_canvas(canvas, c, True)
        canvas.showPage()

    canvas.save()
