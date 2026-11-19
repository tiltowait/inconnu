"""Define the package interface."""

from inconnu.misc.aggheal import AggHealOutcome, aggheal, aggheal_update_message, heal_aggravated
from inconnu.misc.awaken import awaken
from inconnu.misc.bol import bol
from inconnu.misc.changelog import fetch_changelog, show_changelog
from inconnu.misc.coinflip import coinflip
from inconnu.misc.frenzy import frenzy
from inconnu.misc.mend import MendOutcome, mend, mend_superficial, mend_update_message
from inconnu.misc.percentile import percentile
from inconnu.misc.remorse import remorse
from inconnu.misc.rouse import (
    RouseOutcome,
    perform_rouse,
    roll_rouse_checks,
    rouse,
    rouse_update_message,
)
from inconnu.misc.slake import perform_slake, slake
from inconnu.misc.stain import stain
from inconnu.misc.transfer import transfer_character

__all__ = (
    "AggHealOutcome",
    "MendOutcome",
    "RouseOutcome",
    "aggheal",
    "aggheal_update_message",
    "awaken",
    "bol",
    "coinflip",
    "fetch_changelog",
    "frenzy",
    "heal_aggravated",
    "mend",
    "mend_superficial",
    "mend_update_message",
    "percentile",
    "perform_rouse",
    "perform_slake",
    "remorse",
    "roll_rouse_checks",
    "rouse",
    "rouse_update_message",
    "show_changelog",
    "slake",
    "stain",
    "transfer_character",
)
