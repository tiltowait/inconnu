"""Awaken tests."""

from unittest.mock import AsyncMock, patch

from ctx import AppCtx
from inconnu.misc.awaken import awaken
from models.vchar import VChar


async def test_vamp_awaken_rouse_success_no_wp(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test vampire awakening with rouse success and no WP to recover."""
    vamp.willpower = "......."  # No superficial damage
    initial_hunger = vamp.hunger

    with patch("inconnu.d10", return_value=7):  # Rouse success
        await awaken(ctx, vamp)

    # Hunger should not increase
    assert vamp.hunger == initial_hunger
    mock_char_save.assert_awaited()


async def test_vamp_awaken_rouse_failure(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test vampire awakening with rouse failure."""
    vamp.hunger = 2
    vamp.willpower = "......."  # No superficial damage

    with patch("inconnu.d10", return_value=3):  # Rouse failure
        await awaken(ctx, vamp)

    # Hunger should increase
    assert vamp.hunger == 3
    mock_char_save.assert_awaited()


async def test_vamp_awaken_rouse_failure_at_hunger_5(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test vampire awakening with rouse failure at hunger 5 triggers torpor."""
    vamp.hunger = 5
    vamp.willpower = "......."

    with patch("inconnu.d10", return_value=3):  # Rouse failure
        await awaken(ctx, vamp)

    # Hunger stays at 5
    assert vamp.hunger == 5
    mock_char_save.assert_awaited()


async def test_vamp_awaken_wp_recovery(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test vampire awakening recovers Superficial Willpower damage."""
    vamp.willpower = "...////"  # 3 healthy, 4 superficial
    recovery_amount = vamp.willpower_recovery  # max(Resolve=1, Composure=2) = 2
    initial_superficial = vamp.superficial_wp

    with patch("inconnu.d10", return_value=7):  # Rouse success
        await awaken(ctx, vamp)

    # Should recover willpower_recovery amount
    expected_remaining = initial_superficial - recovery_amount
    assert vamp.superficial_wp == expected_remaining
    mock_char_save.assert_awaited()


async def test_vamp_awaken_blush_turns_off(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that vampire awakening turns off Blush of Life."""
    vamp.header.blush = 1  # Blushed

    with patch("inconnu.d10", return_value=7):
        await awaken(ctx, vamp)

    # Blush should be turned off
    assert vamp.header.blush == 0
    mock_char_save.assert_awaited()


async def test_vamp_awaken_logs_correctly(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that vampire awakening logs both awaken and rouse."""
    vamp.stat_log = {}

    with patch("inconnu.d10", return_value=7):
        await awaken(ctx, vamp)

    # Should log both awaken and rouse
    assert "awaken" in vamp.stat_log
    assert "rouse" in vamp.stat_log
    assert vamp.stat_log["awaken"] == 1
    assert vamp.stat_log["rouse"] == 1
    mock_char_save.assert_awaited()


async def test_thin_blood_awaken_rouse_check(
    thin_blood: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that thin-bloods perform rouse checks like full vampires."""
    thin_blood.hunger = 2
    thin_blood.willpower = "......."

    with patch("inconnu.d10", return_value=3):  # Failure
        await awaken(ctx, thin_blood)

    # Hunger should increase
    assert thin_blood.hunger == 3
    mock_char_save.assert_awaited()


async def test_thin_blood_blush_unchanged(
    thin_blood: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that thin-blood blush is not changed on awakening."""
    thin_blood.header.blush = -1  # Thin-bloods have -1

    with patch("inconnu.d10", return_value=7):
        await awaken(ctx, thin_blood)

    # Blush should remain unchanged
    assert thin_blood.header.blush == -1
    mock_char_save.assert_awaited()


async def test_mortal_awaken_health_recovery(
    mortal: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test mortal awakening recovers health based on Stamina."""
    mortal.health = "...////"  # 3 healthy, 4 superficial
    mortal.willpower = "......."
    initial_superficial = mortal.superficial_hp

    await awaken(ctx, mortal)

    # Should recover Stamina amount (3 from fixture)
    expected_remaining = initial_superficial - 3
    assert mortal.superficial_hp == expected_remaining
    mock_char_save.assert_awaited()


async def test_mortal_awaken_no_rouse_check(
    mortal: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that mortals don't perform rouse checks."""
    mortal.willpower = "......."
    initial_hunger = mortal.hunger  # Should be 0 for mortals

    with patch("inconnu.d10") as mock_d10:
        await awaken(ctx, mortal)

    # d10 should not be called
    mock_d10.assert_not_called()
    # Hunger should remain 0
    assert mortal.hunger == initial_hunger
    mock_char_save.assert_awaited()


async def test_mortal_awaken_wp_recovery(
    mortal: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test mortal awakening also recovers Willpower."""
    mortal.health = "......."
    mortal.willpower = "...////"  # 3 healthy, 4 superficial
    recovery_amount = mortal.willpower_recovery  # max(Resolve=1, Composure=2) = 2
    initial_superficial = mortal.superficial_wp

    await awaken(ctx, mortal)

    # Should recover WP
    expected_remaining = initial_superficial - recovery_amount
    assert mortal.superficial_wp == expected_remaining
    mock_char_save.assert_awaited()


async def test_ghoul_awaken_health_recovery_double_stamina(
    ghoul: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test ghoul awakening recovers health at double Stamina rate."""
    ghoul.health = ".//////"  # 1 healthy, 6 superficial
    ghoul.willpower = "......."
    initial_superficial = ghoul.superficial_hp

    await awaken(ctx, ghoul)

    # Should recover Stamina * 2 amount (3 * 2 = 6)
    expected_remaining = initial_superficial - 6
    assert ghoul.superficial_hp == expected_remaining
    mock_char_save.assert_awaited()


async def test_ghoul_awaken_no_rouse_check(
    ghoul: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that ghouls don't perform rouse checks."""
    ghoul.willpower = "......."

    with patch("inconnu.d10") as mock_d10:
        await awaken(ctx, ghoul)

    # d10 should not be called
    mock_d10.assert_not_called()
    mock_char_save.assert_awaited()


async def test_mortal_awaken_both_recoveries(
    mortal: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test mortal awakening recovers both health and WP."""
    mortal.health = "...////"  # 4 superficial HP
    mortal.willpower = "...////"  # 4 superficial WP
    initial_superficial_hp = mortal.superficial_hp
    initial_superficial_wp = mortal.superficial_wp

    await awaken(ctx, mortal)

    # Should recover both
    # Stamina = 3, WP recovery = 2
    assert mortal.superficial_hp == initial_superficial_hp - 3
    assert mortal.superficial_wp == initial_superficial_wp - 2
    mock_char_save.assert_awaited()


async def test_vamp_awaken_zero_wp_recovery(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test vampire awakening with no WP to recover."""
    vamp.willpower = "......."  # No damage
    initial_superficial = vamp.superficial_wp

    with patch("inconnu.d10", return_value=7):
        await awaken(ctx, vamp)

    # WP should not change
    assert vamp.superficial_wp == initial_superficial
    mock_char_save.assert_awaited()


async def test_mortal_awaken_zero_health_recovery(
    mortal: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test mortal awakening with no health to recover."""
    mortal.health = "......."  # No damage
    mortal.willpower = "......."
    initial_superficial = mortal.superficial_hp

    await awaken(ctx, mortal)

    # Health should not change
    assert mortal.superficial_hp == initial_superficial
    mock_char_save.assert_awaited()


async def test_awaken_logs_awaken_for_all_types(
    mortal: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that all character types log 'awaken'."""
    mortal.stat_log = {}

    await awaken(ctx, mortal)

    # Should log awaken
    assert "awaken" in mortal.stat_log
    assert mortal.stat_log["awaken"] == 1
    mock_char_save.assert_awaited()


async def test_vamp_awaken_partial_wp_recovery(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test vampire awakening with partial WP recovery."""
    vamp.willpower = "....../"  # 6 healthy, 1 superficial
    recovery_amount = vamp.willpower_recovery  # 2
    initial_superficial = vamp.superficial_wp  # 1

    with patch("inconnu.d10", return_value=7):
        await awaken(ctx, vamp)

    # Should only recover what's there (1 < 2, so recover 1)
    assert vamp.superficial_wp == 0
    mock_char_save.assert_awaited()


async def test_mortal_awaken_partial_health_recovery(
    mortal: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test mortal awakening with partial health recovery."""
    mortal.health = "........./"  # 9 healthy, 1 superficial
    mortal.willpower = "......."
    initial_superficial = mortal.superficial_hp  # 1

    await awaken(ctx, mortal)

    # Stamina is 3, but only 1 superficial damage, so only recover 1
    assert mortal.superficial_hp == 0
    mock_char_save.assert_awaited()


async def test_vamp_awaken_rouse_logging(
    vamp: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that vampires log rouse even on success."""
    vamp.stat_log = {}

    with patch("inconnu.d10", return_value=7):  # Success
        await awaken(ctx, vamp)

    # Should log rouse regardless of success/failure
    assert "rouse" in vamp.stat_log
    assert vamp.stat_log["rouse"] == 1
    mock_char_save.assert_awaited()


async def test_mortal_no_rouse_logging(
    mortal: VChar,
    ctx: AppCtx,
    mock_char_save: AsyncMock,
):
    """Test that mortals don't log rouse."""
    mortal.stat_log = {}

    await awaken(ctx, mortal)

    # Should not log rouse
    assert "rouse" not in mortal.stat_log
    mock_char_save.assert_awaited()
