"""Set up the package."""

from inconnu.experience.award_deduct import award_or_deduct
from inconnu.experience.bulk import bulk_award_xp
from inconnu.experience.list import list_events
from inconnu.experience.remove import remove_entry

__all__ = ("award_or_deduct", "bulk_award_xp", "list_events", "remove_entry")
