"""c_help.py - Defines constants for help messages."""

# Some of the help comments can get rather long, so we define them here rather
# than in commands.py in order not to clutter up that file.

# Gameplay commands

ROLL_BRIEF = "Roll the dice"
ROLL_DESC = "Roll a dice pool from explicit values or using stored traits."
ROLL_USAGE = "[character] <pool> [hunger] [difficulty]"
ROLL_HELP = """
character:  The character performing the roll
               Optional if you only have one character
               Optional if you aren't rolling traits
pool:       May use character traits and simple math.
               Ex: 7
               Ex: strength + brawl - 2
hunger:     The number of hunger dice to roll (default 0)
difficulty: The difficulty of the roll (default 0)
"""
