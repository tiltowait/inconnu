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

Need a quick coin toss? This will generate heads or tails.

## General Information

```
/info
```

Displays general information and help links.

## Help

```
/help section:<section>
```

Shows quick help for a topic.

## Invite

```
/invite
```

Displays a link to invite the bot. (Tip: You can also get a link by clicking on the bot's profile.)

## Probability Calculation

You can calculate roll outcome probabilities using the `/probability` command.

```
/probability roll:<roll> reroll:[strategy] character:[character] impairment_category:[category]
```

| Option | Description | Notes |
| --- | --- | --- |
| `roll` | The pool, Hunger, and difficulty, such as `7 3 2` or `Resolve + Academics 2 4` | May use [traits](../guides/quickstart/rolling-with-traits.md) |
| `reroll` | Calculate using a [Willpower re-roll strategy](../guides/quickstart/willpower-re-rolls.md) | Optional |
| `character` | The character whose traits to use | Optional |
| `impairment_category` | Change the roll's [Impairment](rolls/impairment.md) category, or ignore Impairment | Optional |

## Random Numbers

A random number between 1 and `ceiling` (default `100`) may be rolled with the `/random` command.

## Statistics

Want to see how many rolls you've made? How many successes, crits, bestial failures, and the like? How many times you've used a Willpower re-roll? The `/statistics` command will show all of this information for each of your characters on the server.

Additionally, this command can show statistics for a specific trait. Currently, this is limited to showing the number of rolls made and number of successes gleaned in a given time period.

| Option | Description | Notes |
| --- | --- | --- |
| `style` | The type of stats lookup to make | "General" shows basic statistics, like number of criticals; "Traits" shows number of successes for each Attribute and Skill rolled |
| `date` | Limit results to rolls after this date | Optional; `YYYYMMDD` format |
| `hidden` | Show the results only to you | Default `True` |

> [!NOTE]
> If `date` is omitted, it will show all statistics for the character(s) the bot has ever recorded.

Admins can leave a roll out of statistics, or put it back, by right-clicking it and choosing **Apps → Toggle Roll Statistics**.
