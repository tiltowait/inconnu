"""display/trackmoji.py - A tool for converting a stress track to emoji."""

from ..constants import DAMAGE

class Trackmoji:
    """A class that translates between stress tracks and emoji."""

    def __init__(self, bot):
        self.bot = bot
        self.emojis = {
            DAMAGE.none: 883516968777449472,
            DAMAGE.superficial: 883516968337035317,
            DAMAGE.aggravated: 883516968727089202,
            "hunger": 883527494832119858,
            "no_hunger": 883527495394164776,
            "hu_filled": 883532393946972160,
            "hu_unfilled": 883532394051809290,
            "stain": 883536498950025258
        }


    # Public Methods

    def emojify_track(self, track: str) -> str:
        """Convert a stress track into an emoji string."""
        emoji_track = []
        for box in track:
            emoji_track.append(self.__emojify_stressbox(box))

        return " ".join(emoji_track)


    def emojify_hunger(self, level: int) -> str:
        """Create a hunger emoji track."""
        filled = level
        unfilled = 5 - level

        hunger = [self.__hungermoji(True) for _ in range(filled)]
        unfilled = [self.__hungermoji(False) for _ in range(unfilled)]
        hunger.extend(unfilled)

        return " ".join(hunger)


    def emojify_humanity(self, humanity: int, stains: int) -> str:
        """Create a humanity emoji track."""

        # Humanity fills from the right, to a max of 10. Stains fill from the right
        # and can overlap filled boxes
        unfilled = 10 - humanity - stains
        if unfilled < 0:
            unfilled = 0 # So we don't accidentally add to filled boxes
        filled = 10 - unfilled - stains

        filled = [self.__humanitymoji(True) for _ in range(filled)]
        unfilled = [self.__humanitymoji(False) for _ in range(unfilled)]
        stains = [self.__stainmoji() for _ in range(stains)]

        track = filled
        track.extend(unfilled)
        track.extend(stains)

        return " ".join(track)


    # Private Methods

    def __emojify_stressbox(self, box: str):
        """Convert a stress box value to an emoji."""
        if len(box) == 0:
            raise ValueError("Invalid stress box") # Should never happen

        box = box[0]

        emoji = self.emojis[box]
        if isinstance(emoji, int):
            # Need to convert
            emoji = str(self.bot.get_emoji(emoji))
            self.emojis[box] = emoji

        return emoji


    def __hungermoji(self, hungry: bool) -> str:
        """Return a filled or unfilled hunger emoji."""
        hunger = "hunger" if hungry else "no_hunger"
        emoji = self.emojis[hunger]

        if isinstance(emoji, int):
            # Need to convert
            emoji = str(self.bot.get_emoji(emoji))
            self.emojis[hunger] = emoji

        return emoji


    def __humanitymoji(self, filled) -> str:
        """Return a filled or unfilled humanity emoji."""
        humanity = "hu_filled" if filled else "hu_unfilled"
        return self.__fetch_emoji(humanity)


    def __stainmoji(self) -> str:
        """Return a stain emoji."""
        return self.__fetch_emoji("stain")


    def __fetch_emoji(self, key) -> str:
        """Fetch an emoji from a key, caching as necessary."""
        emoji = self.emojis[key]

        if isinstance(emoji, int):
            # Need to convert
            emoji = str(self.bot.get_emoji(emoji))
            self.emojis[key] = emoji

        return emoji
