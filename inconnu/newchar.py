"""newchar.py - Handle new character creation."""

from collections import namedtuple

from . import wizard

__WIZARDS = {}

__INSTRUCTIONS = "Character creation wizard usage:\n"
__INSTRUCTIONS += "```\n"
__INSTRUCTIONS += "name=NAME — The character's name\n"
__INSTRUCTIONS += "hp=HEALTH — The character's max HP (number)\n"
__INSTRUCTIONS += "wp=WILLPOWER — The character's max WP (number)\n"
__INSTRUCTIONS += "humanity=HUMANITY — The character's Humanity (number)\n"
__INSTRUCTIONS += "type=TYPE — The type of character: vampire, mortal, or ghoul\n"
__INSTRUCTIONS += "```\n"
__INSTRUCTIONS += "**Example:** `//new name=Nadea hp=8 wp=6 humanity=7 type=vampire`"

Parameters = namedtuple('Parameters', ["name", "hp", "wp", "humanity", "type"])

async def parse(ctx, *args):
    """Parse and handle character creation arguments."""

    try:
        parameters = parse_arguments(*args)
        await ctx.reply("Please check your DMs!")

        character_wizard = wizard.Wizard(ctx, parameters)
        __WIZARDS[ctx.author.id] = character_wizard

        await character_wizard.begin_chargen()
    except (ValueError, KeyError):
        await ctx.reply(__INSTRUCTIONS)


async def process_response(message):
    """Process user response to a wizard message."""

    char_wizard = __WIZARDS[message.author.id]

    if not char_wizard:
        return

    try:
        rating = int(message.content.split()[0])

        if 0 <= rating <= 5:
            await char_wizard.assign_next_trait(rating)
        else:
            raise ValueError("Range: 0-5")
    except ValueError:
        await char_wizard.resend_last_query("Error: You must respond with a number between 0-5.")


def parse_arguments(*arguments):
    """
    Parse the user's arguments.
    Raises ValueErrors and KeyErrors on exceptions.
    """

    if len(arguments) != 5:
        raise ValueError(__INSTRUCTIONS)

    parameters = {}
    keys = ["name", "hp", "wp", "humanity", "type"]
    char_types = {"vampire": 0, "mortal": 1, "ghoul": 2}

    for argument in arguments:
        key, value = argument.split("=")
        key = key.lower()

        if not key in keys:
            raise ValueError(f"Unknown parameter `{key}`.")

        if key == "name":
            parameters[key] = value
        elif key in ["hp", "wp", "humanity"]:
            if not value.isdigit():
                raise ValueError("HP/WP/Humanity must be a positive integer.")
            parameters[key] = int(value)
        else: # "type"
            parameters[key] = char_types[value] # KeyError is handled in caller

    # Concert to the named tuple
    values = []
    for key in keys:
        values.append(parameters[key])

    return Parameters(*values)
