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
from card import CardLayout, SmallCard, LargeCard, EpicCard, SuperEpicCard, TemplateTooSmall, Border, LineDivider


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





class KeepTogether(Flowable):
    def __init__(self, flowables):
        self.flowables = flowables
        self._available_height = None
        self._available_width = None

    def wrap(self, aW, aH):
        self._available_width = aW
        self._available_height = aH

        height = 0
        width = 0
        for flowable in self.flowables:
            w, h = flowable.wrap(aW, 0xFFFFFFFF)
            height += flowable.getSpaceBefore()
            height += h
            height += flowable.getSpaceAfter()
            if w > width:
                width = w
        return width, height

    def drawOn(self, canvas, x, y, _sW=0):
        y -= self.flowables[0].getSpaceBefore()
        for flowable in self.flowables[::-1]:
            y += flowable.getSpaceBefore()
            width, height = flowable.wrap(self._available_width, self._available_height)
            flowable.drawOn(canvas, x, y, _sW=_sW)
            y += height
            y += flowable.getSpaceAfter()
            self._available_height -= (
                flowable.getSpaceBefore() + height + flowable.getSpaceBefore()
            )

class MonsterCardLayout(CardLayout):
    def __init__(
        self,
        armor_class,
        max_hit_points,
        speed,
        strength,
        dexterity,
        constitution,
        intelligence,
        wisdom,
        charisma,
        challenge_rating,
        experience_points,
        source,
        attributes,
        abilities=None,
        actions=None,
        reactions=None,
        legendary=None,
        image_path=ASSET_DIR / "placeholder_monster.png",
        **kwargs,
    ):
        super().__init__(image_path=image_path, **kwargs)
        self.armor_class = armor_class
        self.max_hit_points = max_hit_points
        self.speed = speed
        self.strength = strength
        self.dexterity = dexterity
        self.constitution = constitution
        self.intelligence = intelligence
        self.wisdom = wisdom
        self.charisma = charisma
        self.attributes = attributes
        self.abilities = abilities
        self.actions = actions
        self.reactions = reactions
        self.legendary = legendary
        self.challenge_rating = challenge_rating
        self.experience_points = experience_points
        self.source = source

    def _draw_back(self, canvas):
        super()._draw_back(canvas)

        # Challenge
        canvas.setFillColor("white")
        self.fonts.set_font(canvas, "challenge")
        canvas.drawString(
            self.width + self.border_front[Border.LEFT],
            self.challenge_bottom,
            "Challenge {} ({} XP)".format(
                self.challenge_rating, self.experience_points
            ),
        )
        ### Source
        self.fonts.set_font(canvas, "text")
        canvas.drawString(*self.source_location, self.source)

    def fill_frames(self, canvas):

        # Title font scaling
        custom_scale = (
            min(1.0, 20 / len(self.title)) if isinstance(self, SmallCard) else 1.0
        )
        original_font_size = self.fonts.styles["title"][1] * self.fonts.FONT_SCALE
        font_size = original_font_size * custom_scale
        spacer_height = (original_font_size - font_size + 0.5 * mm) / 2
        style = copy(self.fonts.paragraph_styles["title"])
        style.fontSize = font_size
        style.leading = font_size + spacer_height

        # Title
        self.elements.append(Spacer(1 * mm, spacer_height))
        self.elements.append(
            Paragraph(
                self.title,
                style,
            )
        )

        # Subtitle
        self.elements.append(
            Paragraph(
                self.subtitle,
                self.fonts.paragraph_styles["subtitle"],
            )
        )

        top_stats = [
            [
                Paragraph(
                    "<b>AC:</b> {}<br/><b>Speed:</b> {}".format(
                        self.armor_class, self.speed
                    ),
                    self.fonts.paragraph_styles["text"],
                ),
                Paragraph(
                    "<b>HP:</b> {}".format(self.max_hit_points),
                    self.fonts.paragraph_styles["text"],
                ),
            ]
        ]
        ts = TableStyle(
            [
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
        t = Table(top_stats, style=ts, spaceBefore=1 * mm)
        self.elements.append(t)

        # Modifiers
        abilities = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        modifiers = [
            self.strength,
            self.dexterity,
            self.constitution,
            self.intelligence,
            self.wisdom,
            self.charisma,
        ]
        # if modifiers are (int), e.g. 13, then automatically reformat as "13 (+1)"
        modifiers = [
            (m if isinstance(m, str) else "%d (%+d)" % (m, math.floor((m - 10) / 2)))
            for m in modifiers
        ]
        modifier_table_data = [
            [
                Paragraph(a, self.fonts.paragraph_styles["modifier_title"])
                for a in abilities
            ],
            [Paragraph(m, self.fonts.paragraph_styles["modifier"]) for m in modifiers],
        ]

        t = Table(
            modifier_table_data,
            [self.BASE_WIDTH / (len(abilities) + 1)] * 5,
            style=ts,
            spaceBefore=1 * mm,
        )
        self.elements.append(t)

        # Divider 1
        line_width = self.frames[0]._width
        self.elements.append(
            LineDivider(
                width=line_width,
                xoffset=-self.TEXT_MARGIN,
                fill_color=self.border_color,
            )
        )

        # Attributes
        # TODO: Handle list attributes
        text = ""
        for heading, body in (self.attributes or {}).items():
            text += "<b>{}:</b> {}<br/>".format(heading, body)
        self.elements.append(Paragraph(text, self.fonts.paragraph_styles["text"]))

        # Abilities
        for heading, body in (self.abilities or {}).items():
            paragraph = Paragraph(
                "<i><b>{}.</b></i> {}".format(heading, body),
                self.fonts.paragraph_styles["text"],
            )
            self.elements.append(paragraph)

        # Divider 2
        self.elements.append(
            LineDivider(
                width=line_width,
                xoffset=-self.TEXT_MARGIN,
                fill_color=self.border_color,
            )
        )

        # Actions
        title = Paragraph("ACTIONS", self.fonts.paragraph_styles["action_title"])
        first_action = True
        for heading, body in (self.actions or {}).items():
            paragraph = Paragraph(
                "<i><b>{}.</b></i> {}".format(heading, body),
                self.fonts.paragraph_styles["text"],
            )
            if first_action:
                element = KeepTogether([title, paragraph])
                first_action = False
            else:
                element = paragraph
            self.elements.append(element)

        if self.reactions is not None:
            # Divider 3
            self.elements.append(
                LineDivider(
                    width=line_width,
                    xoffset=-self.TEXT_MARGIN,
                    fill_color=self.border_color,
                )
            )

            title = Paragraph("REACTIONS", self.fonts.paragraph_styles["action_title"])
            first_reaction = True
            for heading, body in (self.reactions or {}).items():
                paragraph = Paragraph(
                    "<i><b>{}.</b></i> {}".format(heading, body),
                    self.fonts.paragraph_styles["text"],
                )
                if first_reaction:
                    element = KeepTogether([title, paragraph])
                    first_reaction = False
                else:
                    element = paragraph
                self.elements.append(element)

        if self.legendary is not None:
            self.elements.append(
                LineDivider(
                    width=line_width,
                    xoffset=-self.TEXT_MARGIN,
                    fill_color=self.border_color,
                )
            )

            title = Paragraph(
                "LEGENDARY ACTIONS", self.fonts.paragraph_styles["action_title"]
            )
            first_legendary = True
            for entry in self.legendary or []:
                if type(entry) == str:
                    paragraph = Paragraph(
                        entry,
                        self.fonts.paragraph_styles["text"],
                    )
                elif type(entry) == dict:
                    paragraph = Paragraph(
                        "<i><b>{}.</b></i> {}".format(*list(entry.items())[0]),
                        self.fonts.paragraph_styles["legendary_action"],
                    )
                else:
                    TypeError(
                        'Legendary action cannot be type "{}"'.format(type(entry))
                    )

                if first_legendary:
                    element = KeepTogether([title, paragraph])
                    first_legendary = False
                else:
                    element = paragraph
                self.elements.append(element)

    def _get_title_paragraph(self):
        # Title font scaling
        custom_scale = (
            min(1.0, 20 / len(self.title)) if isinstance(self, SmallCard) else 1.0
        )
        original_font_size = self.fonts.styles["title"][1] * self.fonts.FONT_SCALE
        font_size = original_font_size * custom_scale
        style = copy(self.fonts.paragraph_styles["title"])
        style.fontSize = font_size
        style.leading = font_size

        # Title
        return Paragraph(
            self.title,
            style,
        )


class ItemCardLayout(CardLayout):
    def __init__(
        self,
        title,
        subtitle,
        category,
        description,
        subcategory=None,
        image_path=ASSET_DIR / "placeholder_item.png",
        **kwargs,
    ):
        super().__init__(
            title=title, subtitle=subtitle, image_path=image_path, **kwargs
        )
        self.category = category
        self.subcategory = subcategory
        self.description = description

    def _draw_back(self, canvas, x, y):
        super()._draw_back(canvas, x, y)

        canvas.setFillColor("white")
        self.fonts.set_font(canvas, "category")
        left_of_category_text = x + self.border_front[Border.LEFT]
        width_of_category_text = y
        canvas.drawString(
            x + self.border_back[Border.LEFT],
            y + self.border_back[Border.TOP],
            self.category,
        )

        if self.subcategory is not None:
            self.fonts.set_font(canvas, "subcategory")
            canvas.drawString(
                left_of_category_text + width_of_category_text + 1 * mm,
                self.category_bottom,
                "({})".format(self.subcategory),
            )

    def fill_frames(self, canvas, x, y):

        # Title
        self.elements.append(self._get_title_paragraph())

        # Subtitle
        self.elements.append(
            Paragraph(
                self.subtitle,
                self.fonts.paragraph_styles["subtitle"],
            )
        )

        # Add a space before text
        self.elements.append(Spacer(1 * mm, 1 * mm))

        if type(self.description) == str:
            self.elements.append(
                Paragraph(self.description, self.fonts.paragraph_styles["text"])
            )
            return
        if type(self.description) != list:
            raise ValueError(
                f"Item `{self.title}` description should be a `str` or `list`"
            )

        for entry in self.description:
            if type(entry) == str:
                self.elements.append(
                    Paragraph(entry, self.fonts.paragraph_styles["text"])
                )
            if type(entry) == dict:
                for title, description in entry.items():

                    text = f"<i><b>{title}.</b></i>"
                    if description is not None:
                        text += f" {description}"

                    self.elements.append(
                        Paragraph(
                            text,
                            self.fonts.paragraph_styles["text"],
                        )
                    )

            # TODO: Tables

    def _get_title_paragraph(self):
        return Paragraph(
            self.title,
            self.fonts.paragraph_styles["title"],
        )


class MonsterCardSmall(SmallCard, MonsterCardLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.challenge_bottom = 5.5 * mm + self.bleed
        self.source_location = (
            self.width + self.border_back[Border.LEFT],
            3 * mm + self.bleed,
        )


class ItemCardSmall(SmallCard, ItemCardLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # category is centered in the footer
        self.category_bottom = 3.5 * mm + self.bleed


class MonsterCardLarge(LargeCard, MonsterCardLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.challenge_bottom = (
            self.border_back[Border.BOTTOM]
            - self.bleed
            - self.fonts.styles["challenge"][1]
        ) / 2 + self.bleed
        self.source_location = (
            self.width * 1.5 + self.STANDARD_BORDER / 2,
            self.challenge_bottom,
        )


class MonsterCardEpic(EpicCard, MonsterCardLarge):
    pass


class MonsterCardSuperEpic(SuperEpicCard, MonsterCardLarge):
    pass


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
