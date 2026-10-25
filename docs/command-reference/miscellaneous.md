---
description: Commands that don't fit any other category.
---

# Miscellaneous

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

The `ROLL` parameter can be any valid roll, such as `7 3 2` (pool 7, hunger 3, difficulty 2) or even a trait-based roll like `Resolve + Academics 2 4`.

The `STRATEGY` parameter allows you to specify a specific [Willpower re-roll strategy](../guides/quickstart/willpower-re-rolls.md).

|            |                                                                                                               | Notes                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `roll`     | The roll syntax to use                                                                                        | May be any valid roll, [including trait-based rolls](../guides/quickstart/rolling-with-traits.md) |
| `strategy` | Run the simulations using a specific [Willpower re-roll strategy](../guides/quickstart/willpower-re-rolls.md) | Optional                                                                                          |
| `impairment_category` | Change the roll's [Impairment](rolls/impairment.md) category, or ignore Impairment | Optional |

## Random Numbers

A random number between 1 and `ceiling` (default `100`) may be rolled with the `/random` command.

## Statistics

Want to see how many rolls you've made? How many successes, crits, bestial failures, and the like? How many times you've used a Willpower re-roll? The `/statistics` command will show all of this information for each of your characters on the server.

Additionally, this command can show statistics for a specific trait. Currently, this is limited to showing the number of rolls made and number of successes gleaned in a given time period.

| Parameter | Description                            | Notes                                                                                                                                    |
| --------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `style`   | The type of stats lookup to make       | "General" shows basic statistics, like number of criticals, etc.; "Traits" shows number of successes for each Attribute and Skill rolled |
| `date`    | Limit results to rolls after this date | Optional; YYYYMMDD format                                                                                                                |

> [!NOTE]
> If `date` is omitted, it will show all statistics for the character(s) the bot has ever recorded.
