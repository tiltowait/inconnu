"""rollresult.py - Class for calculating the results of a roll."""

class RollResult:
    """A container class that determines the result of a roll."""

    def __init__(self, normal, hunger, difficulty):
        """
        Args:
            normal (DiceThrow): The rolled normal dice
            hunger (DiceThrow): The rolled hunger dice
            difficulty (int): The target number of successes
        """
        self.normal = normal
        self.hunger = hunger
        self.pool = normal.count + hunger.count
        self.difficulty = difficulty
        self.descriptor = None


    # We could technically do this with stored properties, but the math is extremely
    # fast, so we will do it this way for legibility. This will also more easily let
    # us perform Willpower re-rolls.

    # Embed data

    @property
    def embed_color(self):
        """Determine the Discord embed color based on the result of the roll."""
        if self.is_critical:
            return 0x00FF00 # Green
        if self.is_messy:
            return 0xEA3323 # Red-orange
        if self.is_successful:
            return 0x7777FF # Blurple-ish
        if self.is_failure:
            return 0x808080 # Gray
        if self.is_total_failure:
            return 0x000000 # Black

        # Bestial failure
        return 0x5C0700 # Dark red


    @property
    def main_takeaway(self):
        """The roll's main takeaway--i.e. "SUCCESS", "FAILURE", etc."""
        if self.is_critical:
            return "**CRITICAL!**"
        if self.is_messy:
            return "**MESSY CRITICAL!**"
        if self.is_successful:
            return "**SUCCESS!**"
        if self.is_failure:
            return "**FAILURE!**"
        if self.is_total_failure:
            return "**TOTAL FAILURE!**"

        # Bestial failure
        return "**BESTIAL FAILURE!**"


    # Roll Reflection

    @property
    def total_successes(self):
        """The total number of successes."""
        total_tens = self.normal.tens + self.hunger.tens
        crits = total_tens - (total_tens % 2)

        return self.normal.successes + self.hunger.successes + crits


    @property
    def margin(self):
        """Return the roll's success margin."""
        return self.total_successes - self.difficulty


    @property
    def is_critical(self):
        """Return true if the roll is a critical, but not messy, success."""
        critical = self.normal.tens >= 2 and self.hunger.tens == 0
        return critical and self.is_successful


    @property
    def is_messy(self):
        """Return true if the roll is a messy critical."""
        messy = self.normal.tens > 0 and self.hunger.tens > 0
        return messy and self.is_successful


    @property
    def is_successful(self):
        """Return true if the roll meets or exceeds its target."""
        return self.margin >= 0


    @property
    def is_failure(self):
        """Return true if the target successes weren't achieved, but it isn't bestial."""
        return self.hunger.ones == 0 and self.total_successes >= 0


    @property
    def is_total_failure(self):
        """Return true if no successes were rolled, and no ones on hunger dice."""
        return self.total_successes == 0 and self.hunger.ones == 0


    @property
    def is_bestial(self):
        """Return true if the roll is a bestial failure."""
        bestial = self.hunger.ones > 0
        return bestial and not self.is_successful


    # Re-roll strategies

    @property
    def can_reroll_failures(self):
        """Whether there are any non-Hunger failures to re-roll."""
        return self.normal.failures > 0


    @property
    def can_maximize_criticals(self):
        """Whether there are any non-critical non-Hunger failures to re-roll."""
        return self.normal.tens != self.normal.count


    @property
    def can_avoid_messy_critical(self):
        """Whether it's possible to avoid a messy critical, assuming we have one."""
        if not self.is_messy:
            return False

        return self.hunger.tens == 1
