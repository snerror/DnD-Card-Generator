import os
import pathlib

from copy import copy
from enum import Enum, IntEnum
from abc import ABC
import PIL

from reportlab.lib import utils
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from reportlab.graphics import renderPDF
from reportlab.platypus import Frame
from reportlab.platypus.flowables import Flowable, Spacer, Image
from svglib.svglib import svg2rlg
from fonts import FreeFonts

ASSET_DIR = pathlib.Path(__file__).parent.resolve() / "assets"


class Orientation(Enum):
    NORMAL = 1
    TURN90 = 2


class Border(IntEnum):
    LEFT = 0
    RIGHT = 1
    BOTTOM = 2
    TOP = 3


class TemplateTooSmall(Exception):
    pass


class CardLayout(ABC):
    CARD_CORNER_DIAMETER = 3 * mm
    BACKGROUND_CORNER_DIAMETER = 2 * mm
    LOGO_WIDTH = 42 * mm
    STANDARD_BORDER = 2.5 * mm
    STANDARD_MARGIN = 1.0 * mm
    TEXT_MARGIN = 2 * mm
    BASE_WIDTH = 63 * mm
    BASE_HEIGHT = 89 * mm
    TITLE_BAR_HEIGHT = 4.8 * mm

    def __init__(
        self,
        title,
        subtitle,
        background=ASSET_DIR / "background.png",
        artist=None,
        image_path=None,
        border_color="#ec1923",
        border_front=(0, 0, 0, 0),  # uninitialized
        border_back=(0, 0, 0, 0),  # uninitialized
        width=0,  # uninitialized
        height=0,  # uninitialized
        bleed=0,  # uninitialized
        fonts=FreeFonts(),
        **kwargs,
    ):
        self.frames = []
        self.title = title
        self.subtitle = subtitle
        self.artist = artist
        self.fonts = fonts
        self.background_image_path = background
        self.border_color = border_color
        self.border_front = tuple([v + bleed for v in border_front])
        self.border_back = tuple([v + bleed for v in border_back])
        self.width = width + 2 * bleed
        self.height = height + 2 * bleed
        self.bleed = bleed
        self.front_image_path = os.path.abspath(image_path)
        self.front_orientation = best_orientation(
            self.front_image_path, self.width, self.height
        )
        self.elements = []
        self.front_margins = tuple(
            [x + self.STANDARD_MARGIN for x in self.border_front]
        )

    def set_size(self, canvas):
        canvas.setPageSize(A4)

    def draw(self, canvas, split, x=0, y=0):
        self.draw_front(canvas, x, y)
        self.draw_back(canvas, split, x + self.width, y)

    def draw_front(self, canvas, x=0, y=0):
        self._draw_front(canvas, x, y)

    def draw_back(self, canvas, split, x=0, y=0):
        self._draw_back(canvas, x, y)
        self.fill_frames(canvas, x, y)
        self._draw_frames(canvas, split, x, y)

    def fill_frames(self, canvas, x, y):
        pass

    def _draw_front_frame(self, canvas, x, y, width, height):
        front_frame = Frame(
            x + self.border_front[Border.LEFT],
            y + self.border_front[Border.BOTTOM],
            width - self.border_front[Border.LEFT] - self.border_front[Border.RIGHT],
            height - self.border_front[Border.TOP] - self.border_front[Border.BOTTOM],
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=self.TEXT_MARGIN,
        )

        # DEBUG
        # front_frame.drawBoundary(canvas)

        title_paragraph = self._get_title_paragraph()

        # Nasty hack alert!
        # There is no way to know how big the text will be and Frame only
        # supports top to bottom layout. This means we have no way of
        # knowing the maximum image size.
        #
        # As a hack to get around this, we have to:
        #  1. mock out the paragraphs drawOn method
        #  2. "draw" the paragraph
        #  3. Calculate how tall it was
        #  4. Reset the frame and restore the original drawOn

        def mock(*args, **kwargs):
            pass

        original_drawOn = title_paragraph.drawOn
        title_paragraph.drawOn = mock
        result = front_frame.add(title_paragraph, canvas)
        if not result:
            raise Exception("Failed to draw title in front frame")

        title_height = (
            front_frame.y1 + front_frame.height - front_frame._y + self.TEXT_MARGIN
        )
        title_paragraph.drawOn = original_drawOn
        front_frame._reset()

        available_height = front_frame.height - title_height - self.TEXT_MARGIN * 2

        image_width, image_height = get_image_size(
            self.front_image_path,
            front_frame.width,
            available_height,
        )

        elements = []

        # Add spacer if image doesn't fully fill frame
        space = front_frame.height - (image_height + title_height)
        if space > 0:
            elements.append(Spacer(front_frame.width, space / 2))

        elements.append(Image(self.front_image_path, image_width, image_height))

        # Add second spacer
        if space > 0:
            elements.append(Spacer(front_frame.width, space / 2))

        elements.append(title_paragraph)
        front_frame.addFromList(elements, canvas)

    def _draw_frames(self, canvas, split=False, x=0, y=0):
        frames = iter(self.frames)
        current_frame = next(frames)

        current_frame = Frame(
            x + self.border_front[Border.LEFT],
            y + self.border_front[Border.BOTTOM],
            self.width
            - self.border_front[Border.LEFT]
            - self.border_front[Border.RIGHT],
            self.height - self.border_front[Border.TOP],
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=self.TEXT_MARGIN,
        )

        # Draw the elements
        while len(self.elements) > 0:
            element = self.elements.pop(0)

            if type(element) == LineDivider:

                # Don't place a Line Divider if there is nothing after it
                if len(self.elements) == 0:
                    break

                # Caluclate how much space is left
                available_width = current_frame._getAvailableWidth()
                available_height = current_frame._y - current_frame._y1p

                # Calculate how much heigh is required for the line and the next element
                _, line_height = element.wrap(available_width, 0xFFFFFFFF)
                _, next_height = self.elements[0].wrap(available_width, 0xFFFFFFFF)

                # Dont draw it if it will be the last thing on the frame
                if available_height < line_height + next_height:
                    continue

            # DEBUG: Draw frame boundary
            # current_frame.drawBoundary(canvas)

            result = current_frame.add(element, canvas)
            if result == 0:
                # Could not draw into current frame
                if split:
                    # Try splitting the element into the remaining space
                    remaining = current_frame.split(element, canvas)
                    if len(remaining):
                        # it can fit, so add the fragment that can fit
                        current_frame.add(remaining.pop(0), canvas)
                        self.elements = remaining + self.elements
                        continue

                # We couldn't draw the element, so put it back
                self.elements.insert(0, element)
                try:
                    current_frame = next(frames)
                # No more frames
                except StopIteration:
                    break

        # If there are undrawn elements, raise an error
        if len(self.elements) > 0:
            raise TemplateTooSmall("Template too small")

    def _draw_front(self, canvas, x=0, y=0):
        canvas.saveState()

        # Draw red border
        self._draw_single_border(canvas, x, y, self.width, self.height)

        # Parchment background
        self._draw_single_background(
            canvas,
            x,
            y,
            self.border_front,
            self.width,
            self.height,
            self.front_orientation,
        )

        # Set card orientation
        if self.front_orientation == Orientation.TURN90:
            canvas.rotate(90)
            canvas.translate(0, -self.width)
            width = self.height
            height = self.width
        else:
            width = self.width
            height = self.height

        # D&D logo
        dnd_logo = svg2rlg(ASSET_DIR / "logo.svg")
        if dnd_logo is not None:
            factor = self.LOGO_WIDTH / dnd_logo.width
            dnd_logo.width *= factor
            dnd_logo.height *= factor
            dnd_logo.scale(factor, factor)
            logo_margin = (
                self.border_front[Border.TOP] - self.bleed - dnd_logo.height
            ) / 2
            renderPDF.draw(
                dnd_logo,
                canvas,
                x + (width - self.LOGO_WIDTH) / 2,
                y + height - self.border_front[Border.TOP] + logo_margin,
            )

        self._draw_front_frame(canvas, x, y, width, height)

        # Artist
        if self.artist:
            canvas.setFillColor("white")
            artist_font_height = self.fonts.set_font(canvas, "artist")
            canvas.drawCentredString(
                width / 2,
                self.border_front[Border.BOTTOM] - artist_font_height - 1 * mm,
                "Artist: {}".format(self.artist),
            )

        canvas.restoreState()

    def _draw_back(self, canvas, x, y):
        # Draw red border
        self._draw_single_border(canvas, x, y, self.width, self.height)

        # Parchment background
        self._draw_single_background(
            canvas, x, y, self.border_back, self.width, self.height
        )

    def _draw_single_border(self, canvas, x, y, width, height):
        canvas.saveState()
        canvas.setFillColor(self.border_color)
        canvas.roundRect(
            x,
            y,
            width,
            height,
            max(self.CARD_CORNER_DIAMETER - self.bleed, 0.0 * mm),
            stroke=0,
            fill=1,
        )
        canvas.restoreState()

    def _draw_single_background(
        self, canvas, x, y, margins, width, height, orientation=Orientation.NORMAL
    ):
        canvas.saveState()

        canvas.setFillColor("white")
        clipping_mask = canvas.beginPath()

        if orientation == Orientation.TURN90:
            clipping_mask.roundRect(
                x + margins[Border.BOTTOM],
                y + margins[Border.LEFT],
                width - margins[Border.TOP] - margins[Border.BOTTOM],
                height - margins[Border.RIGHT] - margins[Border.LEFT],
                self.BACKGROUND_CORNER_DIAMETER,
            )
        else:
            clipping_mask.roundRect(
                x + margins[Border.LEFT],
                y + margins[Border.BOTTOM],
                width - margins[Border.RIGHT] - margins[Border.LEFT],
                height - margins[Border.TOP] - margins[Border.BOTTOM],
                self.BACKGROUND_CORNER_DIAMETER,
            )
        canvas.clipPath(clipping_mask, stroke=0, fill=1)

        if self.background_image_path is not None:
            canvas.drawImage(
                self.background_image_path, x, y, width=width, height=height, mask=None
            )

        canvas.restoreState()


class SmallCard(CardLayout):
    def __init__(
        self,
        width=CardLayout.BASE_WIDTH,
        height=CardLayout.BASE_HEIGHT,
        border_front=(2.5 * mm, 2.5 * mm, 7.0 * mm, 7.0 * mm),
        border_back=(2.5 * mm, 2.5 * mm, 9.2 * mm, 2.5 * mm),
        **kwargs,
    ):
        super().__init__(
            width=width,
            height=height,
            border_front=border_front,
            border_back=border_back,
            **kwargs,
        )

        frame = Frame(
            # X
            self.width + self.border_back[Border.LEFT],
            # Y
            self.border_back[Border.BOTTOM],
            # Width
            self.width - self.border_back[Border.LEFT] - self.border_back[Border.RIGHT],
            # Height
            self.height
            - self.border_back[Border.TOP]
            - self.border_back[Border.BOTTOM],
            # Padding
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=0,
        )
        self.frames.append(frame)


class LargeCard(CardLayout):
    def __init__(
        self,
        width=CardLayout.BASE_WIDTH * 2,
        height=CardLayout.BASE_HEIGHT,
        border_front=(3.5 * mm, 3.5 * mm, 7.0 * mm, 7.0 * mm),
        border_back=(4.0 * mm, 4.0 * mm, 8.5 * mm, 3.0 * mm),
        **kwargs,
    ):
        super().__init__(
            width=width,
            height=height,
            border_front=border_front,
            border_back=border_back,
            **kwargs,
        )

        left_frame = Frame(
            # X
            self.width + self.border_back[Border.LEFT],
            # Y
            self.border_back[Border.BOTTOM],
            # Width
            self.width / 2 - self.border_back[Border.LEFT] - self.STANDARD_BORDER / 2,
            # Height
            self.height
            - self.border_back[Border.TOP]
            - self.border_back[Border.BOTTOM],
            # Padding
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=0,
        )
        right_frame = Frame(
            # X
            self.width * 1.5 + self.STANDARD_BORDER / 2,
            # Y
            self.border_back[Border.BOTTOM],
            # Width
            self.width / 2 - self.border_back[Border.LEFT] - self.STANDARD_BORDER / 2,
            # Height
            self.height
            - self.border_back[Border.BOTTOM]
            - self.border_back[Border.TOP],
            # Padding
            leftPadding=self.TEXT_MARGIN,
            bottomPadding=self.TEXT_MARGIN,
            rightPadding=self.TEXT_MARGIN,
            topPadding=1 * mm,
            showBoundary=True,
        )
        self.frames.append(left_frame)
        self.frames.append(right_frame)

    def draw(self, canvas, split):
        super().draw(canvas, split)
        canvas.setFillColor(self.border_color)
        canvas.rect(
            self.width * 1.5 - self.STANDARD_BORDER / 2,
            0,
            self.STANDARD_BORDER,
            self.height,
            stroke=0,
            fill=1,
        )


class EpicCard(LargeCard):
    def __init__(
        self,
        height=CardLayout.BASE_WIDTH * 2,
        border_back=(4.0 * mm, 4.0 * mm, 6.5 * mm, 3.0 * mm),
        **kwargs,
    ):
        super().__init__(height=height, border_back=border_back, **kwargs)

        # Card is square, don't rotate it
        self.front_orientation = Orientation.NORMAL


class SuperEpicCard(EpicCard):
    def __init__(self, height=CardLayout.BASE_WIDTH * 3, **kwargs):
        super().__init__(height=height, **kwargs)


# Draws a line across the frame, unless it is at the top of the frame, in which
# case nothing is drawn
class LineDivider(Flowable):
    def __init__(
        self,
        xoffset=0,
        width=None,
        fill_color="red",
        line_height=0.25 * mm,
        spacing=1 * mm,
    ):
        self.xoffset = xoffset
        self.width = width
        self.fill_color = fill_color
        self.spacing = spacing
        self.line_height = line_height
        self.height = self.line_height + self.spacing

    def _at_top(self):
        at_top = False
        frame = getattr(self, "_frame", None)
        if frame:
            at_top = getattr(frame, "_atTop", None)
        return at_top

    def wrap(self, *args):
        if self._at_top():
            return (0, 0)
        else:
            return (self.width, self.height)

    def draw(self):
        if not self._at_top():
            canvas = self.canv
            canvas.setFillColor(self.fill_color)
            canvas.rect(self.xoffset, 0, self.width, self.line_height, stroke=0, fill=1)


# Returns the width and height an image should be to fit into the available
# space, while maintaining aspect ratio
def get_image_size(path, available_width, available_height):
    img = utils.ImageReader(path)
    image_width, image_height = img.getSize()

    width_ratio = available_width / image_width
    height_ratio = available_height / image_height
    best_ratio = min(width_ratio, height_ratio)

    return (image_width * best_ratio, image_height * best_ratio)


# Returns the best orientation for the given image aspect ration
def best_orientation(image_path, card_width, card_height):
    image = PIL.Image.open(image_path)
    image_width, image_height = image.size
    if (image_width > image_height) == (card_width > card_height):
        return Orientation.NORMAL
    else:
        return Orientation.TURN90

def get_card_width(card_type):
    if card_type == "small":
        return 63 * mm
    elif card_type == "large":
        return 126 * mm
    elif card_type == "epic":
        return 189 * mm
    elif card_type == "super-epic":
        return 252 * mm
    else:
        raise ValueError("Invalid card type: {}".format(card_type))

def get_card_height(card_type):
    if card_type == "small":
        return 89 * mm
    elif card_type == "large":
        return 89 * mm
    elif card_type == "epic":
        return 126 * mm
    elif card_type == "super-epic":
        return 189 * mm
    else:
        raise ValueError("Invalid card type: {}".format(card_type))