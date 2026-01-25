"""Image-related command interface."""

from inconnu.character.images.display import display_images as display
from inconnu.character.images.upload import upload_image as upload

__all__ = ("display", "upload")
