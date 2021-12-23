"""dicemoji.py - A tool for fetching emoji for representing dice rolls."""

__EMOJIS = {
    "ln_crit": "<:ln_crit:890427149213909042>​",
    "ln_fail": "<:ln_fail:890427148945489971>​",
    "ln_succ": "<:ln_succ:890427148920291339>​",
    "h_crit": "<:h_crit:888880025082953769>​",
    "h_succ": "<:h_succ:888880025493962813>​",
    "h_fail": "<:h_fail:888880025359757402>​",
    "h_bestial": "<:h_bestial:883189689895501844>​"
}


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
        emoji_name += "bestial" if hunger else "fail"
    elif die == 10:
        emoji_name += "crit"
    elif die >= 6:
        emoji_name += "succ"
    else:
        emoji_name += "fail"

    return __EMOJIS[emoji_name]
