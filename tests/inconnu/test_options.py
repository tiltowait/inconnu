"""Tests for inconnu/options.py."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

import inconnu.options as options_module
from inconnu.options import _character_autocomplete
from models import VChar

GUILD_ID = 1
USER_ID = 10
OTHER_ID = 20
REFUSAL = "Only Storytellers can look up other players"

# Each owner's characters, by name. SPCs belong to VChar.SPC_OWNER.
CHARACTERS = {USER_ID: ["Mine"], OTHER_ID: ["Theirs"], VChar.SPC_OWNER: ["SPC"]}

type MockAutocompleteContext = MagicMock
type MockFetchall = AsyncMock


def make_ctx(player: int | None = None) -> MockAutocompleteContext:
    """An autocomplete context for USER_ID, who may have filled in a player.
    Like Discord, the player arrives as a string snowflake."""
    ctx = MagicMock(spec=discord.AutocompleteContext)
    ctx.interaction = MagicMock(spec=discord.Interaction)
    ctx.interaction.guild = MagicMock(spec=discord.Guild)
    ctx.interaction.guild.id = GUILD_ID
    ctx.interaction.user = MagicMock(spec=discord.Member)
    ctx.interaction.user.id = USER_ID
    ctx.options = {"player": str(player)} if player is not None else {}
    ctx.value = ""
    return ctx


def make_char(name: str) -> VChar:
    """A character with the given name."""
    char = MagicMock(spec=VChar)
    char.name = name
    char.id_str = name.lower()
    return char


@pytest.fixture(autouse=True)
def mock_fetchall() -> Iterator[MockFetchall]:
    """Serve CHARACTERS instead of the database."""

    async def fetchall(_guild: int, owner: int) -> list[VChar]:
        """Return the owner's characters."""
        return [make_char(name) for name in CHARACTERS.get(owner, [])]

    with patch.object(options_module.services.char_mgr, "fetchall", side_effect=fetchall) as mock:
        yield mock


async def names(ctx: MockAutocompleteContext, storyteller: bool, allow_lookups: bool) -> list[str]:
    """The names of the choices the autocomplete offers."""
    autocomplete = _character_autocomplete(allow_lookups)
    with patch.object(
        options_module, "is_storyteller", new_callable=AsyncMock, return_value=storyteller
    ):
        return [choice.name for choice in await autocomplete(ctx)]


@pytest.mark.parametrize("allow_lookups", [True, False])
async def test_own_player_lists_own_characters(allow_lookups: bool):
    """Naming yourself as the player isn't a lookup, so anyone gets their own
    characters."""
    assert await names(make_ctx(USER_ID), False, allow_lookups) == ["Mine"]


@pytest.mark.parametrize(
    "storyteller,allow_lookups,expected",
    [
        (False, False, [REFUSAL]),
        (False, True, ["Theirs"]),
        (True, False, ["Theirs"]),
    ],
)
async def test_other_player(storyteller: bool, allow_lookups: bool, expected: list[str]):
    """Another player's characters are listed for Storytellers, or for anyone
    when the command allows lookups."""
    assert await names(make_ctx(OTHER_ID), storyteller, allow_lookups) == expected


@pytest.mark.parametrize("storyteller,expected", [(True, ["Mine", "SPC"]), (False, ["Mine"])])
async def test_no_player_adds_spcs_for_storytellers(storyteller: bool, expected: list[str]):
    """Without a player, Storytellers also get the server's SPCs."""
    assert await names(make_ctx(), storyteller, False) == expected
