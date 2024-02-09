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
from card import (
    CardLayout,
    SmallCard,
    LargeCard,
    EpicCard,
    SuperEpicCard,
    TemplateTooSmall,
    Border,
    LineDivider,
)
from card_item import ItemCardLayout


ASSET_DIR = pathlib.Path(__file__).parent.resolve() / "assets"


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


class MonsterCardSmall(SmallCard, MonsterCardLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.challenge_bottom = 5.5 * mm + self.bleed
        self.source_location = (
            self.width + self.border_back[Border.LEFT],
            3 * mm + self.bleed,
        )


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
