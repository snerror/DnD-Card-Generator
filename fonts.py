import pathlib

from abc import ABC

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.fonts import addMapping


ASSET_DIR = pathlib.Path(__file__).parent.resolve() / "assets"


# TODO: Clean up the font object, it seems a bit crude
# TODO: Also manage colours
class Fonts(ABC):
    styles = {}
    # Scaling factor between the font size and its actual height in mm
    FONT_SCALE = None
    FONT_DIR = ASSET_DIR / "fonts"

    def __init__(self):
        self._register_fonts()
        self.paragraph_styles = StyleSheet1()
        self.paragraph_styles.add(
            ParagraphStyle(
                name="title",
                fontName=self.styles["title"][0],
                fontSize=self.styles["title"][1] * self.FONT_SCALE,
                leading=self.styles["title"][1] * self.FONT_SCALE + 0.5 * mm,
                spaceAfter=0.5 * mm,
                alignment=TA_CENTER,
                textTransform="uppercase",
            )
        )
        self.paragraph_styles.add(
            ParagraphStyle(
                name="subtitle",
                fontName=self.styles["subtitle"][0],
                fontSize=self.styles["subtitle"][1] * self.FONT_SCALE,
                textColor=self.styles["subtitle"][2],
                backColor="red",
                leading=self.styles["subtitle"][1] * self.FONT_SCALE + 0.5 * mm,
                alignment=TA_CENTER,
                borderPadding=(0, 6),
            )
        )
        self.paragraph_styles.add(
            ParagraphStyle(
                name="text",
                fontName=self.styles["text"][0],
                fontSize=self.styles["text"][1] * self.FONT_SCALE,
                leading=self.styles["text"][1] * self.FONT_SCALE + 0.5 * mm,
                spaceBefore=1 * mm,
            )
        )
        self.paragraph_styles.add(
            ParagraphStyle(
                name="legendary_action",
                fontName=self.styles["text"][0],
                fontSize=self.styles["text"][1] * self.FONT_SCALE,
                leading=self.styles["text"][1] * self.FONT_SCALE + 0.5 * mm,
                spaceBefore=0,
            )
        )
        self.paragraph_styles.add(
            ParagraphStyle(
                name="modifier",
                fontName=self.styles["text"][0],
                fontSize=self.styles["text"][1] * self.FONT_SCALE,
                leading=self.styles["text"][1] * self.FONT_SCALE + 0.5 * mm,
                alignment=TA_CENTER,
            )
        )
        self.paragraph_styles.add(
            ParagraphStyle(
                name="action_title",
                fontName=self.styles["modifier_title"][0],
                fontSize=self.styles["modifier_title"][1] * self.FONT_SCALE,
                leading=self.styles["modifier_title"][1] * self.FONT_SCALE + 0.5 * mm,
                spaceBefore=1 * mm,
            )
        )
        self.paragraph_styles.add(
            ParagraphStyle(
                name="modifier_title",
                fontName=self.styles["modifier_title"][0],
                fontSize=self.styles["modifier_title"][1] * self.FONT_SCALE,
                leading=self.styles["modifier_title"][1] * self.FONT_SCALE + 0.5 * mm,
                alignment=TA_CENTER,
            )
        )

    def set_font(self, canvas, section, custom_scale=1.0):
        canvas.setFont(
            self.styles[section][0],
            self.styles[section][1] * self.FONT_SCALE * custom_scale,
        )
        return self.styles[section][1]

    def _register_fonts(self):
        raise NotImplemented


class FreeFonts(Fonts):
    FONT_SCALE = 1.41

    styles = {
        "title": ("Universal Serif", 2.5 * mm, "black"),
        "subtitle": ("ScalySans", 1.5 * mm, "white"),
        "challenge": ("Universal Serif", 2.25 * mm, "black"),
        "category": ("Universal Serif", 2.25 * mm, "black"),
        "subcategory": ("Universal Serif", 1.5 * mm, "black"),
        "heading": ("ScalySansBold", 1.5 * mm, "black"),
        "text": ("ScalySans", 1.5 * mm, "black"),
        "artist": ("ScalySans", 1.5 * mm, "white"),
        "modifier_title": ("Universal Serif", 1.5 * mm, "black"),
    }

    def _register_fonts(self):
        pdfmetrics.registerFont(
            TTFont("Universal Serif", self.FONT_DIR / "Universal Serif.ttf")
        )
        pdfmetrics.registerFont(TTFont("ScalySans", self.FONT_DIR / "ScalySans.ttf"))
        pdfmetrics.registerFont(
            TTFont("ScalySansItalic", self.FONT_DIR / "ScalySans-Italic.ttf")
        )
        pdfmetrics.registerFont(
            TTFont("ScalySansBold", self.FONT_DIR / "ScalySans-Bold.ttf")
        )
        pdfmetrics.registerFont(
            TTFont("ScalySansBoldItalic", self.FONT_DIR / "ScalySans-BoldItalic.ttf")
        )

        addMapping("ScalySans", 0, 0, "ScalySans")  # normal
        addMapping("ScalySans", 0, 1, "ScalySansItalic")  # italic
        addMapping("ScalySans", 1, 0, "ScalySansBold")  # bold
        addMapping("ScalySans", 1, 1, "ScalySansBoldItalic")  # italic and bold


class AccurateFonts(Fonts):
    FONT_SCALE = 1.41

    styles = {
        "title": ("ModestoExpanded", 2.5 * mm, "black"),
        "subtitle": ("ModestoTextLight", 1.5 * mm, "white"),
        "challenge": ("ModestoExpanded", 2.25 * mm, "black"),
        "category": ("ModestoExpanded", 2.25 * mm, "black"),
        "subcategory": ("ModestoExpanded", 1.5 * mm, "black"),
        "heading": ("ModestoTextBold", 1.5 * mm, "black"),
        "text": ("ModestoTextLight", 1.5 * mm, "black"),
        "artist": ("ModestoTextLight", 1.25 * mm, "white"),
        "modifier_title": ("ModestoExpanded", 1.5 * mm, "black"),
    }

    def _register_fonts(self):
        pdfmetrics.registerFont(
            TTFont("ModestoExpanded", self.FONT_DIR / "ModestoExpanded-Regular.ttf")
        )
        pdfmetrics.registerFont(
            TTFont("ModestoTextLight", self.FONT_DIR / "ModestoText-Light.ttf")
        )
        pdfmetrics.registerFont(
            TTFont(
                "ModestoTextLightItalic",
                self.FONT_DIR / "ModestoText-LightItalic.ttf",
            )
        )
        pdfmetrics.registerFont(
            TTFont("ModestoTextBold", self.FONT_DIR / "ModestoText-Bold.ttf")
        )
        pdfmetrics.registerFont(
            TTFont(
                "ModestoTextBoldItalic",
                self.FONT_DIR / "ModestoText-BoldItalic.ttf",
            )
        )

        addMapping("ModestoTextLight", 0, 0, "ModestoTextLight")  # normal
        addMapping("ModestoTextLight", 0, 1, "ModestoTextLightItalic")  # italic
        addMapping("ModestoTextLight", 1, 0, "ModestoTextBold")  # bold
        addMapping("ModestoTextLight", 1, 1, "ModestoTextBoldItalic")  # italic and bold
