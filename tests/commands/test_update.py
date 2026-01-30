"""Character update tests."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

import inconnu
from ctx import AppCtx
from inconnu.character.update.parse import update
from models.vchar import VChar


@pytest.fixture
def mock_update_display():
    """Mock display specifically for update tests (imported into parse.py)."""
    with patch("inconnu.character.update.parse.display", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_haven(vamp: VChar):
    """Mock Haven to return our test character."""

    async def mock_fetch():
        return vamp

    haven_instance = MagicMock()
    haven_instance.fetch = mock_fetch
    haven_instance.owner = MagicMock()

    with patch("services.Haven", return_value=haven_instance):
        yield haven_instance


async def test_update_superficial_health_increment(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test adding superficial health damage."""
    vamp.health = "......."  # All healthy
    initial_superficial = vamp.superficial_hp

    await update(ctx, "sh+2", character=vamp)

    # Should add 2 superficial damage
    assert vamp.superficial_hp == initial_superficial + 2
    mock_char_save.assert_awaited()


async def test_update_superficial_health_decrement(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test removing superficial health damage."""
    vamp.health = "...////"  # 4 superficial
    initial_superficial = vamp.superficial_hp

    await update(ctx, "sh-2", character=vamp)

    # Should remove 2 superficial damage
    assert vamp.superficial_hp == initial_superficial - 2
    mock_char_save.assert_awaited()


async def test_update_aggravated_health(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test adding aggravated health damage."""
    vamp.health = "......."
    initial_aggravated = vamp.aggravated_hp

    await update(ctx, "ah+1", character=vamp)

    assert vamp.aggravated_hp == initial_aggravated + 1
    mock_char_save.assert_awaited()


async def test_update_superficial_willpower(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test adding superficial willpower damage."""
    vamp.willpower = "......."
    initial_superficial = vamp.superficial_wp

    await update(ctx, "sw+2", character=vamp)

    assert vamp.superficial_wp == initial_superficial + 2
    mock_char_save.assert_awaited()


async def test_update_aggravated_willpower(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test adding aggravated willpower damage."""
    vamp.willpower = "......."
    initial_aggravated = vamp.aggravated_wp

    await update(ctx, "aw+1", character=vamp)

    assert vamp.aggravated_wp == initial_aggravated + 1
    mock_char_save.assert_awaited()


async def test_update_hunger(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test modifying hunger."""
    vamp.hunger = 2

    await update(ctx, "hunger+1", character=vamp)

    assert vamp.hunger == 3
    mock_char_save.assert_awaited()


async def test_update_stains(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test modifying stains."""
    vamp.humanity = 6
    vamp.stains = 2

    await update(ctx, "stains+2", character=vamp)

    assert vamp.stains == 4
    mock_char_save.assert_awaited()


async def test_update_potency(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test modifying blood potency."""
    vamp.potency = 3

    await update(ctx, "potency+1", character=vamp)

    assert vamp.potency == 4
    mock_char_save.assert_awaited()


async def test_update_humanity(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test modifying humanity."""
    vamp.humanity = 6
    vamp.stains = 2

    await update(ctx, "humanity+1", character=vamp)

    # Humanity setter wipes stains
    assert vamp.humanity == 7
    assert vamp.stains == 0
    mock_char_save.assert_awaited()


async def test_update_max_health(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test modifying max health (requires absolute value)."""
    initial_health_len = len(vamp.health)
    new_health_len = initial_health_len + 1

    await update(ctx, f"health={new_health_len}", character=vamp)

    assert len(vamp.health) == new_health_len
    mock_char_save.assert_awaited()


async def test_update_max_willpower(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test modifying max willpower (requires absolute value)."""
    initial_wp_len = len(vamp.willpower)
    new_wp_len = initial_wp_len + 1

    await update(ctx, f"willpower={new_wp_len}", character=vamp)

    assert len(vamp.willpower) == new_wp_len
    mock_char_save.assert_awaited()


async def test_update_name(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test changing character name."""
    original_name = vamp.raw_name

    await update(ctx, "name=New Name", character=vamp)

    assert vamp.raw_name == "New Name"
    assert vamp.raw_name != original_name
    mock_char_save.assert_awaited()


async def test_update_splat(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test changing character splat."""
    vamp.splat = "vampire"

    await update(ctx, "splat=mortal", character=vamp)

    assert vamp.splat == "mortal"
    mock_char_save.assert_awaited()


async def test_update_multiple_parameters(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test updating multiple parameters at once."""
    vamp.health = "......."
    vamp.hunger = 2
    vamp.humanity = 6
    vamp.stains = 1

    await update(ctx, "sh+2 hunger+1 stains-1", character=vamp)

    assert vamp.superficial_hp == 2
    assert vamp.hunger == 3
    assert vamp.stains == 0
    mock_char_save.assert_awaited()


async def test_update_parameter_aliases_health(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that parameter aliases work (hp for health)."""
    initial_health_len = len(vamp.health)
    new_health_len = initial_health_len + 1

    await update(ctx, f"hp={new_health_len}", character=vamp)

    assert len(vamp.health) == new_health_len
    mock_char_save.assert_awaited()


async def test_update_parameter_aliases_hunger(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that parameter aliases work (h for hunger)."""
    vamp.hunger = 2

    await update(ctx, "h+1", character=vamp)

    assert vamp.hunger == 3
    mock_char_save.assert_awaited()


async def test_update_parameter_aliases_superficial_health(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test various aliases for superficial health."""
    vamp.health = "......."

    # Test 'sd' alias
    await update(ctx, "sd+2", character=vamp)
    assert vamp.superficial_hp == 2
    mock_char_save.assert_awaited()


async def test_update_equals_syntax(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test using = syntax with +/-."""
    vamp.hunger = 2

    await update(ctx, "hunger=+1", character=vamp)

    assert vamp.hunger == 3
    mock_char_save.assert_awaited()


async def test_update_colon_syntax(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test using : instead of = (should be converted)."""
    vamp.hunger = 2

    await update(ctx, "hunger:+1", character=vamp)

    assert vamp.hunger == 3
    mock_char_save.assert_awaited()


async def test_update_rollback_on_error(vamp: VChar, ctx: AppCtx):
    """Test that changes are rolled back on error."""
    # Save character to establish a baseline for rollback
    await vamp.save()

    original_name = vamp.raw_name
    original_hunger = vamp.hunger

    # This should fail on 'fake' parameter after applying name change
    # Note: update() catches exceptions and shows help, doesn't raise
    await update(ctx, "name=Foo fake=Fake", character=vamp)

    # Changes should be rolled back - verify values match original
    assert vamp.raw_name == original_name
    assert vamp.hunger == original_hunger


async def test_update_rollback_complex(
    vamp: VChar,
    ctx: AppCtx,
):
    """Test rollback with multiple valid changes before error."""
    # Save character to establish a baseline for rollback
    await vamp.save()

    original_name = vamp.raw_name
    original_hunger = vamp.hunger
    original_stains = vamp.stains

    with (
        patch(
            "models.vchar.VChar.rollback", new_callable=Mock, wraps=vamp.rollback
        ) as mock_rollback,
        patch("models.vchar.VChar.save", new_callable=AsyncMock) as mock_save,
    ):
        # Multiple valid changes followed by invalid parameter
        # Note: update() catches exceptions and shows help, doesn't raise
        await update(ctx, "name=Test hunger+1 stains+1 invalid=value", character=vamp)

        # All changes should be rolled back - verify values match original
        assert vamp.raw_name == original_name
        assert vamp.hunger == original_hunger
        assert vamp.stains == original_stains
        # Character should have no pending changes after rollback
        assert not vamp.is_changed

        mock_rollback.assert_called()
        mock_save.assert_not_awaited()


async def test_update_unknown_parameter_error(
    vamp: VChar,
    ctx: AppCtx,
):
    """Test error on unknown parameter."""
    # Save character to establish baseline
    await vamp.save()

    # update() catches exceptions and shows help, doesn't raise
    await update(ctx, "notreal=5", character=vamp)
    assert not vamp.is_changed, "Character should have no pending changes (nothing was modified)"


async def test_update_duplicate_parameter_error(
    vamp: VChar,
    ctx: AppCtx,
):
    """Test error on duplicate parameter."""
    # Save character to establish baseline
    await vamp.save()

    original_hunger = vamp.hunger

    # Note: update() catches exceptions and shows help, doesn't raise
    await update(ctx, "hunger+1 hunger+2", character=vamp)

    # No changes should be applied
    assert vamp.hunger == original_hunger
    assert not vamp.is_changed


async def test_update_missing_value_error(
    vamp: VChar,
    ctx: AppCtx,
):
    """Test error on missing value."""
    # Save character to establish baseline
    await vamp.save()

    original_hunger = vamp.hunger

    # Note: update() catches exceptions and shows help, doesn't raise
    await update(ctx, "hunger=", character=vamp)

    # No changes should be applied
    assert vamp.hunger == original_hunger
    assert not vamp.is_changed


async def test_update_empty_parameters(
    ctx: AppCtx,
    mock_respond: AsyncMock,
):
    """Test calling update with empty parameters shows help."""
    # Should not raise an error, just show help
    await update(ctx, "", character=None)

    # Should have called respond (for help message)
    mock_respond.assert_awaited_once()


async def test_update_with_custom_message(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test update with custom message (used by awaken, etc)."""
    custom_msg = "Custom update message"

    await update(ctx, "sh-2", character=vamp, update_message=custom_msg)

    # Should still save
    mock_char_save.assert_awaited()


async def test_update_with_custom_fields(
    vamp: VChar,
    ctx: AppCtx,
    mock_update_display: AsyncMock,
):
    """Test update with custom display fields."""
    from inconnu.character.display import DisplayField

    fields = [DisplayField.HEALTH, DisplayField.HUNGER]

    await update(ctx, "hunger+1", character=vamp, fields=fields)

    # Verify display was called with fields
    call_args = mock_update_display.await_args
    assert call_args is not None
    # Fields are passed as kwarg
    assert "fields" in call_args.kwargs
    assert call_args.kwargs["fields"] == fields


async def test_update_damage_aliases(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that sd and sh both work for superficial health."""
    vamp.health = "......."

    # Use 'sd' (superficial damage)
    await update(ctx, "sd+2", character=vamp)
    assert vamp.superficial_hp == 2

    # Reset
    vamp.health = "......."

    # Use 'sh' (superficial health)
    await update(ctx, "sh+2", character=vamp)
    assert vamp.superficial_hp == 2
    mock_char_save.assert_awaited()


async def test_update_xp_without_permission_error(
    vamp: VChar,
    ctx: AppCtx,
):
    """Test that XP updates without permission are blocked."""
    # Save character first so rollback can work
    vamp.experience.unspent = 5
    await vamp.save()

    original_xp = vamp.experience.unspent

    # Mock permission check to return False
    with patch.object(
        inconnu.settings, "can_adjust_current_xp", new_callable=AsyncMock, return_value=False
    ):
        # Should fail permission check
        await update(ctx, "unspent_xp+2", character=vamp)

        assert vamp.experience.unspent == original_xp, "XP should be unchanged due to rollback"
        assert not vamp.is_changed, "Character should have no pending changes"
