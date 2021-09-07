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

# Character CRUD commands

CHAR_NEW_BRIEF = "Create a new character"
CHAR_NEW_DESCRIPTION = "Create a new vampire, mortal, or ghoul."
CHAR_NEW_USAGE = "name=NAME splat=SPLAT humanity=X hp=Y wp=Z"
CHAR_NEW_HELP = """
name:      The character's name
splat:     vampire, mortal, or ghoul
humanity:  Their Humanity rating
hp:        Their max Health
wp:        Their max Willpower

Aside from tracking stats, characters let you roll traits, such as strength or occult. For more info:

     //help v
"""


CHAR_UPDATE_BRIEF = "Update a character's basic statistics"
CHAR_UPDATE_USAGE = "[character] <stat>=<value> ..."
CHAR_UPDATE_HELP = """
character:  The character to update
               Optional if you only have one character
stat:       The stat to update
               Options:
                  name
                  humanity
                  hunger
                  hp
                  wp
                  cur_xp (current XP)
                  total_xp
"""


# Trait CRUD stuff

TRAITS_COMMAND_BRIEF = "Character trait management commands"
TRAITS_COMMAND_USAGE = "<subcommand>"
TRAITS_COMMAND_HELP = TRAITS_COMMAND_BRIEF + "."


TRAITS_ADD_BRIEF = "Add trait(s) to a character"
TRAITS_ADD_USAGE = "[character] <trait>[=rating] ..."
TRAITS_ADD_HELP = """
character:  The character to add the traits to
               Optional if you have only one character
trait:      The name of the trait to add
rating:     The trait's rating

Multiple traits may be added at a time. If you omit RATING, then you will be prompted to supply ratings in DMs.

If a character already has a listed trait, the command will result in an error. To update existing traits, use:

     //traits update
"""


TRAITS_LIST_BRIEF = "Display a character's traits"
TRAITS_LIST_USAGE = "[character]"
TRAITS_LIST_HELP = """
character:  The character whose traits will be shown

Traits will not display in the main chat. Instead, a list will be DMed to you.
"""


TRAITS_UPDATE_BRIEF = "Update a character's trait(s)"
TRAITS_UPDATE_USAGE = "[character] <trait>[=rating] ..."
TRAITS_UPDATE_HELP = """
character:  The character whose traits will be updated
               Optional if you have only one character
trait:      The name of the trait to update
rating:     The trait's new rating

Multiple traits may be updated at a time. If you omit RATING, then you will be prompted to supply ratings in DMs.

If the character does not already have the traits, then the command will error. To add traits, use:

     //traits add
"""


TRAITS_DELETE_BRIEF = "Remove traits from a character"
TRAITS_DELETE_USAGE = "[character] <trait> ..."
TRAITS_DELETE_HELP = """
character:  The character from which to remove the traits
               Optional if you have only one character
trait:      The list of traits to remove, separated by spaces

If the character does not possess one or more of the provided traits, the command will fail, with none of the traits being removed.
"""
