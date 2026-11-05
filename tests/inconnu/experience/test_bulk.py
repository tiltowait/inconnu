"""Tests for inconnu/experience/bulk.py."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import OperationFailure

import errors
import inconnu.experience.bulk as bulk_module
from inconnu.experience.bulk import _BulkModal
from models import VChar
from tests.characters import gen_char

type MockInteraction = MagicMock
type MockSession = MagicMock

ADMIN_ID = 7


def _character(user: int, name: str) -> VChar:
    """A character owned by the user."""
    char = gen_char("vampire")
    char.user = user
    char.name = name
    return char


@pytest.fixture
def characters() -> dict[tuple[int, str], VChar]:
    """The server's characters, by owner and lowercase name."""
    chars = [_character(1, "Nadea"), _character(2, "Billy"), _character(2, "Jimmy")]
    return {(char.user, char.name.lower()): char for char in chars}


@pytest.fixture
def interaction() -> MockInteraction:
    """The admin's modal submission. Only user 1 is still in the server."""
    member = MagicMock(spec=discord.Member)
    member.mention = "<@1>"

    inter = MagicMock(spec=discord.Interaction)
    inter.response = MagicMock(spec=discord.InteractionResponse)
    inter.response.defer = AsyncMock()
    inter.followup = MagicMock(spec=discord.Webhook)
    inter.followup.send = AsyncMock()
    inter.guild = MagicMock(spec=discord.Guild)
    inter.guild.get_member.side_effect = lambda user_id: member if user_id == 1 else None
    inter.user = MagicMock(spec=discord.Member)
    inter.user.id = ADMIN_ID
    return inter


@pytest.fixture(autouse=True)
def mock_fetchone(characters: dict[tuple[int, str], VChar]) -> Iterator[AsyncMock]:
    """Look characters up in the fixture."""

    async def fetchone(_guild, user: int, name: str) -> VChar:
        if (char := characters.get((user, name.lower()))) is None:
            raise errors.CharacterNotFoundError(f"No character named {name}")
        return char

    with patch.object(
        bulk_module.services.char_mgr, "fetchone", new_callable=AsyncMock, side_effect=fetchone
    ) as mock:
        yield mock


@pytest.fixture
def session() -> MockSession:
    """The transaction's session."""
    return MagicMock(spec=AsyncClientSession)


@pytest.fixture(autouse=True)
def mock_transaction(session: MockSession) -> Iterator[AsyncMock]:
    """Run transactions without a database."""

    async def transaction(callback):
        return await callback(session)

    with patch.object(
        bulk_module.db, "transaction", new_callable=AsyncMock, side_effect=transaction
    ) as mock:
        yield mock


@pytest.fixture
def mock_save() -> Iterator[AsyncMock]:
    """Patch character saves."""
    with patch.object(VChar, "save", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_error() -> Iterator[AsyncMock]:
    """Patch the error embed."""
    with patch.object(bulk_module.ui.embeds, "error", new_callable=AsyncMock) as mock:
        yield mock


async def _submit(interaction: MockInteraction, entries: str, reason: str = "Weekly XP"):
    """Fill out and submit the modal."""
    modal = _BulkModal(title="Bulk Award XP")
    modal.children[0].value = reason  # pyright: ignore[reportAttributeAccessIssue]
    modal.children[1].value = entries  # pyright: ignore[reportAttributeAccessIssue]
    await modal.callback(interaction)


async def test_bulk_award(
    interaction: MockInteraction,
    characters: dict[tuple[int, str], VChar],
    mock_save: AsyncMock,
    mock_error: AsyncMock,
):
    """Valid entries award lifetime XP, ignoring spacing, case, and blank lines."""
    await _submit(interaction, "5 xp <@1> Nadea\n\n  3xp   <@!2>  billy  ")

    nadea, billy, jimmy = characters.values()
    assert (nadea.experience.lifetime, nadea.experience.unspent) == (5, 5)
    assert (billy.experience.lifetime, billy.experience.unspent) == (3, 3)
    assert not jimmy.experience.log

    entry = nadea.experience.log[0]
    assert (entry.event, entry.reason, entry.admin) == ("award_lifetime", "Weekly XP", ADMIN_ID)
    assert mock_save.await_count == 2
    interaction.followup.send.assert_awaited_once()
    mock_error.assert_not_awaited()


@pytest.mark.parametrize(
    "bad_line,error",
    [
        ("five xp <@2> Jimmy", "**Invalid syntax:**"),
        ("0 xp <@2> Jimmy", "**Zero XP:**"),
        ("3 xp <@2> Nobody", "**Not found:**"),
        ("3 xp <@1> NADEA", "**Duplicate:**"),
    ],
)
async def test_bulk_award_errors(
    interaction: MockInteraction,
    characters: dict[tuple[int, str], VChar],
    mock_save: AsyncMock,
    mock_error: AsyncMock,
    bad_line: str,
    error: str,
):
    """Any bad line means nobody gets XP, and the bad line is reported."""
    await _submit(interaction, f"5 xp <@1> Nadea\n{bad_line}")

    assert all(not char.experience.log for char in characters.values())
    mock_save.assert_not_awaited()
    interaction.followup.send.assert_not_awaited()

    assert mock_error.await_args is not None
    _, message, *fields = mock_error.await_args.args
    assert "NO XP HAS BEEN AWARDED" in message
    assert dict(fields)["Errors"].strip().startswith(error)
    assert "Nadea" in dict(fields)["Would Award"]


async def test_bulk_award_mentions_missing_members(
    interaction: MockInteraction, mock_error: AsyncMock
):
    """Users who left the server are shown by ID."""
    await _submit(interaction, "3 xp <@2> Nobody")

    assert mock_error.await_args is not None
    fields = dict(mock_error.await_args.args[2:])
    assert fields["Errors"].strip() == "**Not found:** 2: `Nobody`"


@pytest.mark.parametrize("error", [errors.WrongGuild, errors.WrongOwner])
async def test_bulk_award_other_players_character_id(
    error: type[errors.CharacterError],
    interaction: MockInteraction,
    mock_error: AsyncMock,
    mock_fetchone: AsyncMock,
):
    """A character ID belonging to someone else is reported, not raised."""
    mock_fetchone.side_effect = error("Doesn't belong to this user")

    await _submit(interaction, "3 xp <@2> 507f1f77bcf86cd799439011")

    assert mock_error.await_args is not None
    fields = dict(mock_error.await_args.args[2:])
    assert fields["Errors"].strip() == "**Not found:** 2: `507f1f77bcf86cd799439011`"


async def test_bulk_award_surfaces_unexpected_errors(
    interaction: MockInteraction, mock_fetchone: AsyncMock
):
    """A bug in the lookup isn't disguised as a missing character."""
    mock_fetchone.side_effect = KeyError("bug")

    with pytest.raises(KeyError):
        await _submit(interaction, "3 xp <@2> Nobody")


async def test_bulk_award_no_input(
    interaction: MockInteraction, mock_save: AsyncMock, mock_error: AsyncMock
):
    """Blank input is an error."""
    await _submit(interaction, "\n  \n")

    mock_save.assert_not_awaited()
    assert mock_error.await_args is not None
    assert mock_error.await_args.args[1] == "You didn't supply any input!"


async def test_bulk_award_blank_reason(
    interaction: MockInteraction,
    characters: dict[tuple[int, str], VChar],
    mock_save: AsyncMock,
    mock_error: AsyncMock,
):
    """A reason of only whitespace is refused before anything is awarded."""
    await _submit(interaction, "5 xp <@1> Nadea", reason="   ")

    assert all(not char.experience.log for char in characters.values())
    mock_save.assert_not_awaited()
    assert mock_error.await_args is not None
    assert mock_error.await_args.args[1] == "The reason can't be blank."


async def test_bulk_award_saves_in_transaction(
    interaction: MockInteraction,
    session: MockSession,
    mock_transaction: AsyncMock,
    mock_save: AsyncMock,
):
    """Every save is in the transaction, and the confirmation follows the commit."""
    order = MagicMock()
    order.attach_mock(mock_transaction, "transaction")
    order.attach_mock(interaction.followup.send, "send")

    await _submit(interaction, "5 xp <@1> Nadea\n3 xp <@2> Billy")

    assert mock_save.await_count == 2
    assert all(call.kwargs["session"] is session for call in mock_save.await_args_list)
    assert [call[0] for call in order.mock_calls] == ["transaction", "send"]


async def test_bulk_award_retry_awards_once(
    interaction: MockInteraction,
    characters: dict[tuple[int, str], VChar],
    session: MockSession,
    mock_transaction: AsyncMock,
    mock_save: AsyncMock,
):
    """A retried transaction saves again without awarding again."""

    async def retried(callback):
        await callback(session)
        return await callback(session)

    mock_transaction.side_effect = retried
    await _submit(interaction, "5 xp <@1> Nadea")

    nadea = characters[(1, "nadea")]
    assert nadea.experience.lifetime == 5
    assert len(nadea.experience.log) == 1
    assert mock_save.await_count == 2


@pytest.mark.usefixtures("mock_save")
async def test_bulk_award_transaction_fails(
    interaction: MockInteraction,
    characters: dict[tuple[int, str], VChar],
    mock_transaction: AsyncMock,
    mock_error: AsyncMock,
):
    """If the transaction fails, the cached characters lose the XP too."""
    mock_transaction.side_effect = OperationFailure("Write conflict")
    await _submit(interaction, "5 xp <@1> Nadea\n3 xp <@2> Billy")

    for char in characters.values():
        assert (char.experience.lifetime, char.experience.unspent) == (0, 0)
        assert not char.experience.log
    interaction.followup.send.assert_not_awaited()
    assert mock_error.await_args is not None
    assert "no XP was awarded" in mock_error.await_args.args[1]


@pytest.mark.usefixtures("mock_save")
async def test_bulk_award_unexpected_error(
    interaction: MockInteraction,
    characters: dict[tuple[int, str], VChar],
    mock_transaction: AsyncMock,
):
    """Other errors propagate, but the cached characters are still restored."""
    mock_transaction.side_effect = RuntimeError("Bug")

    with pytest.raises(RuntimeError):
        await _submit(interaction, "5 xp <@1> Nadea")

    assert not characters[(1, "nadea")].experience.log
