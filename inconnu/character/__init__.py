"""character - Facilities for character CRUD. This package does not contain VChar."""

from .create import create
from .display import display, display_requested
from .display import HEALTH, WILLPOWER, HUMANITY, POTENCY, HUNGER, EXPERIENCE, SEVERITY
from .update import update, update_help
from .delete import delete
