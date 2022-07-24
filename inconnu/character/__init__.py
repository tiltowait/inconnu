"""character - Facilities for character CRUD. This package does not contain VChar."""

from .bio import edit_biography, show_biography
from .convictions import convictions_set, convictions_show
from .create import create
from .delete import delete
from .display import DisplayField, display, display_requested
from .images import upload
from .update import update, update_help
