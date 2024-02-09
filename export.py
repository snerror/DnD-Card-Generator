import math

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from generator import MonsterCard, ItemCard
from card import get_card_width, get_card_height
from card_item import *
from card_monster import *


class ExportCards:
    def __init__(self, cards, canvas):
        self.cards = cards
        self.canvas = canvas

    def export_singles(self):
        self.canvas.setPageSize((get_card_width("small") * 2, get_card_height("small")))

        for card in self.cards:
            card.draw(self.canvas, 0, 0, True)
            card.draw(self.canvas, get_card_width("small"), 0, False)
            self.canvas.showPage()

    # TODO - This is a bit of a mess, needs to be refactored and finished
    def export_grid(self):
        max_cards = 9
        pages_needed = math.ceil(len(self.cards) / max_cards)

        for i in range(pages_needed):
            c = self.cards[i * max_cards : i * max_cards + max_cards]

            while len(c) < max_cards:
                c.append(self.empty_card())

            self.draw_cards_grid(c, False)
            self.draw_cards_grid(c, True)

    def draw_cards_grid(self, cards, invert=False):
        card_width = 63 * mm
        card_height = 89 * mm

        cards_per_row = math.floor(A4[0] / card_width)
        rows_per_page = math.floor(A4[1] / card_height)

        x = 0 if invert == False else A4[0] - (card_width * cards_per_row)
        y = A4[1] - card_height

        current_col, current_row = 0, 0
        i = 0

        if invert:
            cards = self.mix_array(cards, cards_per_row)

        for card in cards:
            card.draw(self.canvas, x, y, front=invert)

            current_col += 1
            x += card_width
            if current_col >= cards_per_row:
                current_row += 1
                current_col = 0
                x = 0 if invert == False else A4[0] - (card_width * cards_per_row)
                y -= card_height
                if current_row >= rows_per_page:
                    self.canvas.showPage()
                    current_row, current_col = 0, 0
                    x, y = 0, A4[1] - card_height

            i += 1

    def mix_array(self, arr, segment_size):
        num_segments = len(arr) // segment_size + (
            1 if len(arr) % segment_size != 0 else 0
        )

        new_order = []
        for i in range(num_segments):
            start = i * segment_size
            end = min(start + segment_size, len(arr))
            segment = arr[start:end]

            segment = segment[::-1]

            new_order.extend(segment)

        return new_order

    def empty_card(self):
        return ItemCard(title="", subtitle="", description="", category="")
