"""views/dropdown.py - An easy-to-construct dropdown menu."""

from discord import SelectOption
from discord.ui import Select


class Dropdown(Select):
    """An easy-to-construct dropdown that takes tuples as its parameters."""

    def __init__(self, placeholder, *items):
        options = []
        for label, value in items:
            options.append(SelectOption(label=label, value=value))

        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)
