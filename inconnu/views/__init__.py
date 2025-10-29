"""Set up the package."""

import discord

from errorreporter import reporter
from inconnu.views.basicselector import BasicSelector
from inconnu.views.convictionsmodal import ConvictionsModal
from inconnu.views.disablingview import DisablingView
from inconnu.views.dropdown import Dropdown
from inconnu.views.frenzyview import FrenzyView
from inconnu.views.ratingview import RatingView
from inconnu.views.reportingview import ReportingView
from inconnu.views.traitsview import TraitsView

__all__ = (
    "BasicSelector",
    "ConvictionsModal",
    "DisablingView",
    "Dropdown",
    "FrenzyView",
    "RatingView",
    "ReportingView",
    "TraitsView",
)
