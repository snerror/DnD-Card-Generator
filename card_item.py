import pathlib

from reportlab.lib.units import mm
from reportlab.platypus import Paragraph
from reportlab.platypus.flowables import Spacer
from card import CardLayout, Border, SmallCard

ASSET_DIR = pathlib.Path(__file__).parent.resolve() / "assets"


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


class ItemCardSmall(SmallCard, ItemCardLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # category is centered in the footer
        self.category_bottom = 3.5 * mm + self.bleed
