"""dicemoji.py - A tool for fetching emoji for representing dice rolls."""

import services
from constants import Theme


def emojify(theme: Theme, dice: list[int], hunger: bool) -> str:
    """
    Generate a string of emoji.
    Args:
        theme (Theme): The emoji theme
        dice (list): The dice to emojify
        hunger (bool): Whether they are hunger dice
    Returns (str): The emojified string
    """
    emojified = []

    for die in dice:
        emoji = emojify_die(theme, die, hunger)
        emojified.append(emoji)

    return " ".join(emojified)


def emojify_die(theme: Theme, die: int, hunger: bool) -> str:
    """
    Fetch the emoji associated with a given die.
    Args:
        theme (Theme): The emoji theme
        die (int): The value of the die
        hunger (bool): Whether it's a hunger die
    Returns (emoji): The associated emoji
    """

    emoji_name = "h_" if hunger else "ln_"

    if die == 1:
        emoji_name += "bestial"
    elif die == 10:
        emoji_name += "crit"
    elif die >= 6:
        emoji_name += "succ"
    else:
        emoji_name += "fail"

    return services.emojis.emoji(theme, emoji_name)
