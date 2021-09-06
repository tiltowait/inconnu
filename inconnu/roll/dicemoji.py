"""dicemoji.py - A tool for fetching emoji for representing dice rolls."""

class Dicemoji:
    """A class that translates between dice values and emoji."""

    def __init__(self, bot):
        self.bot = bot
        self.emojis = {
            "n_crit": "<:n_crit:883181399417434132>",
            "n_succ": "<:n_succ:883181399438417940>",
            "n_fail": "<:n_fail:883181399539077163>",
            "h_crit": "<:h_crit:883181399107043429>",
            "h_succ": "<:h_succ:883181399371300974>",
            "h_fail": "<:h_fail:883181399400661042>",
            "h_bestial": "<:h_bestial:883189689895501844>"
        }


    def emojify_die(self, die: int, hunger: bool):
        """
        Fetch the emoji associated with a given die.
        Args:
            die (int): The value of the die
            hunger (bool): Whether it's a hunger die
        Returns (emoji): The associated emoji
        """

        emoji_name = "h_" if hunger else "n_"

        if die == 1:
            emoji_name += "bestial" if hunger else "fail"
        elif die == 10:
            emoji_name += "crit"
        elif die >= 6:
            emoji_name += "succ"
        else:
            emoji_name += "fail"

        return self.emojis[emoji_name]


    def emoji_string(self, dice: list, hunger: bool):
        """
        Generate a string of emoji.
        Args:
            dice (list): The dice to emojify
            hunger (bool): Whether they are hunger dice
        Returns (str): The emojified string
        """
        emojified = []

        for die in dice:
            emoji = self.emojify_die(die, hunger)
            emojified.append(emoji)

        return " ".join(emojified)
