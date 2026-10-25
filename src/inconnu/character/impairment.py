"""character/impairment.py - Describing a character's impairment to players."""

from models import IMPAIRMENT_DICE, Impairment, VChar


def incapacitation_reminder(character: VChar) -> str | None:
    """A reminder that the character is in torpor or dead, if applicable."""
    if not character.incapacitated:
        return None
    if character.is_vampire:
        return "You are IN TORPOR!"
    return "You are DEAD!"


def impairment_reminder(character: VChar, *, automatic: bool = False) -> str | None:
    """A description of the character's impairment, if any. Incapacitation takes
    priority. If the penalty is applied automatically, say which rolls receive it;
    otherwise, remind the player to subtract the dice themselves."""
    if character.incapacitated:
        return incapacitation_reminder(character)
    if automatic:
        return _automatic_reminder(character.impairment_state)
    return _manual_reminder(character.impairment_state)


def _automatic_reminder(impairment: Impairment) -> str | None:
    """Tell the player which of their rolls will be penalized."""
    penalty = f"will receive a -{IMPAIRMENT_DICE} penalty."
    match impairment:
        case Impairment.TOTAL:
            return f"You are totally impaired. Your physical, social, and mental rolls {penalty}"
        case Impairment.PHYSICAL:
            return f"You are physically impaired. Your physical rolls {penalty}"
        case Impairment.MENTAL:
            return f"You are mentally impaired. Your social and mental rolls {penalty}"
        case _:
            return None


def _manual_reminder(impairment: Impairment) -> str | None:
    """Remind the player to subtract the penalty from their pools."""
    match impairment:
        case Impairment.TOTAL:
            return (
                "You are totally impaired. "
                f"Remember to subtract {IMPAIRMENT_DICE} dice from all pools."
            )
        case Impairment.PHYSICAL:
            return (
                f"You are physically impaired. Subtract {IMPAIRMENT_DICE} dice from physical pools."
            )
        case Impairment.MENTAL:
            return (
                "You are mentally impaired. "
                f"Subtract {IMPAIRMENT_DICE} dice from social and mental pools."
            )
        case _:
            return None
