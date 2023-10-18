"""dicemoji.py - A tool for fetching emoji for representing dice rolls."""

import inconnu


def emojify(dice: list, hunger: bool):
    """
    Generate a string of emoji.
    Args:
        dice (list): The dice to emojify
        hunger (bool): Whether they are hunger dice
    Returns (str): The emojified string
    """
    emojified = []

    for die in dice:
        emoji = emojify_die(die, hunger)
        emojified.append(emoji)

    return " ".join(emojified)


def emojify_die(die: int, hunger: bool):
    """
    Fetch the emoji associated with a given die.
    Args:
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

    return inconnu.emojis[emoji_name]
