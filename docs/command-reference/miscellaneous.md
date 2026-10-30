---
description: Commands that don't fit any other category.
---

# Miscellaneous

## Blood Potency

```
/bp rating:<rating>
```

Looks up the effects of a Blood Potency rating (1–10).

## Changelog

```
/changelog hidden:[True/False]
```

Shows **Inconnu's** most recent changes. Only you see it unless you set `hidden:False`.

## Coin Flip

```
/coinflip
```

Flips a coin.

## General Information

```
/info
```

Shows general information and help links.

## Help

```
/help section:[section]
```

Shows an overview of common commands, with a menu to browse every command by category. `section` opens a category directly.

## Invite

```
/invite
```

Shows a link to invite the bot. You can also find one on the bot's profile.

## Probability Calculation

Calculates the odds of each outcome for a roll.

```
/probability roll:<roll> reroll:[strategy] character:[character] impairment_category:[category]
```

| Option | Description | Notes |
| --- | --- | --- |
| `roll` | The pool, Hunger, and Difficulty, such as `7 3 2` or `Resolve + Academics 2 4` | May use [Traits](../guides/quickstart/rolling-with-traits.md) |
| `reroll` | Calculate using a [Willpower re-roll strategy](../guides/quickstart/willpower-re-rolls.md) | Optional |
| `character` | The character whose Traits to use | Optional |
| `impairment_category` | Change the roll's [Impairment](rolls/impairment.md) category, or ignore Impairment | Optional |

## Random Numbers

`/random` rolls a number from 1 to `ceiling` (default `100`).

## Statistics

`/statistics` shows roll statistics for each of your characters on the server: rolls made, successes, criticals, bestial failures, Willpower re-rolls, and more.

With `style:Traits`, it shows rolls and successes for each Attribute and Skill instead.

| Option | Description | Notes |
| --- | --- | --- |
| `style` | The type of stats lookup to make | `General` or `Traits` |
| `date` | Limit results to rolls after this date | Optional; `YYYYMMDD` format |
| `hidden` | Show the results only to you | Default `True` |

> [!NOTE]
> Without `date`, it covers every roll on record.

Admins can leave a roll out of statistics, or put it back, by right-clicking it and choosing **Apps → Toggle Roll Statistics**.
