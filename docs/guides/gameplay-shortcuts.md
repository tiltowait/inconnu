# Gameplay Shortcuts

These commands handle common actions and update your character, so you don't need `/character update`.

> [!NOTE]
> Most of these commands take an optional `character`, left out of the listings below.

## Aggravated Healing

`/aggheal` heals one Aggravated damage and makes the three Rouse Checks it costs.

> [!NOTE]
> Only vampires and thin-bloods make Rouse Checks.

## Applying Stains

```
/stain delta:<DELTA>
```

`delta` is the number of Stains to add (positive) or remove (negative).

## Awakening

`/awaken` heals Superficial Willpower damage and makes the night's Rouse Check, telling you if you fall into torpor.

> [!NOTE]
> Mortals heal Superficial Health damage equal to their Stamina instead of making a Rouse Check, and ghouls heal twice that.

## Blush of Life

```
/bol
```

Makes the Blush of Life's Rouse Check, accounting for Humanity: it's `/rouse count:1 purpose:Blush of Life`, re-rolled at Humanity 8 and skipped at 9 and 10.

`ministry_alt` uses the Ministry's alternate Bane, Cold-Blooded: one Rouse Check per point of Bane Severity.

## Crippling Injuries

```
/cripple damage:<DAMAGE>
```

Rolls on the crippling injury table (p.303) for your total Aggravated damage, `damage`.

## Frenzy checks

```
/frenzy difficulty:<difficulty> penalty:[penalty] bonus:[bonus]
```

| Parameter    | Description                        |
| ------------ | ---------------------------------- |
| `difficulty` | The Difficulty of the frenzy check |
| `penalty`    | `Brujah Fury` (the Brujah Bane) or `Malkavian Terror` (-2 dice) |
| `bonus`      | `Cold Dead Hunger`, `The Dream`, `Gentle Mind`, `Jewel in the Garden`, `The Heart of Darkness`, or 1–7 extra dice |

Rolls your current Willpower plus a third of your Humanity, rounded down (_V5_, p.219), with a minimum of one die.

## Mending damage

`/mend` heals Superficial damage based on your Blood Potency (per the V5 Companion errata), or Stamina for mortals and ghouls. Vampires also make a Rouse Check.

## Remorse Checks

Rolls one die per unmarked Humanity box (minimum 1). On a success, Humanity holds; on a failure, it drops by 1. Either way, Stains are cleared.

```
/remorse min_override:[OVERRIDE] lasombra_alt:[True/False]
```

`lasombra_alt` applies the alternate Lasombra Bane, removing dice equal to your Bane Severity.

> [!NOTE]
> **`min_override`** sets a minimum number of dice, for loresheets that allow one. Most players can ignore it; when it's used, the result says so.

## Resonance & Temperament

`/resonance` rolls a random Resonance and Temperament; `/temperament` rolls a Temperament for a Resonance you choose.

## Rouse Checks

Makes Rouse Checks, raising Hunger on each failure. A 1 or 10 on the roll reminds you to take a Stain if it was for Oblivion. The server's [Oblivion Stains](../advanced/server-settings.md#oblivion-stains) setting can change which results count.

```
/rouse count:[count] purpose:[purpose] reroll:[Yes/No]
```

| Parameter | Description                           |
| --------- | ------------------------------------- |
| `count`   | The number of Rouse Checks to perform |
| `purpose` | The reason for the Rouse Check        |
| `reroll`  | Whether to re-roll failures           |

> [!WARNING]
> **Mortals and ghouls:** Mortals can't make Rouse Checks. Ghouls take one Aggravated damage instead (_V5_, p.234).

## Slaking Hunger

Lowers Hunger by the amount you give.

> [!NOTE]
> **At Hunger 4 or 5,** you'll get a button to test for Hunger frenzy. Only vampires and thin-bloods can slake.
