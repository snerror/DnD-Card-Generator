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
                    card_layout.draw_back(canvas, split, x, y)
                else:
                    card_layout.draw_front(canvas, x, y)
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
