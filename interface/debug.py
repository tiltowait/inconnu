"""interface/debug.py - Specialized debugging symbols/behavior."""

import os

from discord_ui.tools import MISSING

# When set, slash commands will only work on the Inconnu Support server. Therefore,
# $INCONNU_DEV should not be set on the production server.
WHITELIST = [882411164468932609, 826628660450689074] if "INCONNU_DEV" in os.environ else MISSING

if isinstance(WHITELIST, list):
    print("Limiting commands to the following guilds:", WHITELIST)
