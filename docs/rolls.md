# Rolls

What follows is a complete reference on **Inconnu's** roll function. If you're new to **Inconnu**, you are encouraged to read the **[Quickstart](quickstart.md)** first.

[filename](includes/parameter-style.md ':include')

## Basic Syntax

```
/vr syntax:<pool hunger difficulty> character:[character]
```

| Parameter    | Description                                              | Notes               |
|--------------|----------------------------------------------------------|---------------------|
| `pool`       | The total number of dice, including Hunger dice, to roll |                     |
| `hunger`     | Your current level of Hunger                             | Default 0           |
| `difficulty` | The test's Difficulty                                    | Default 0           |
| `comment`    | A description of the roll                                | Optional            |
| `character`  | The character performing the roll                        | Optional            |
| `player`     | The player who owns the charactor                        | Administrators only |

?> `character` is optional if you are not using a [trait pool](#trait-pools). Even with a trait pool, `character` is still optional if you only have one character in the server.

[filename](includes/admin-description.md ':include')

### Alternative Command

```
/roll pool:POOL hunger:HUNGER difficulty:DIFFICULTY
```

This command functions as an alternative to `/vr`. The main difference is that it enforces the inputting of `hunger` and `difficulty`. Some users find it easier; do note, however, that due to the way Discord works, this command is a bit more cumbersome to use, especially on mobile. The `pool` parameter behaves the same as `/vr`.

## Trait Pools

`pool` is a special parameter. It accepts [traits](trait-management.md) in addition to numbers, and multiple traits can be combined in a simple addition/subtraction equation.

**Example:** `/vr syntax:Strength + Brawl + 2 2` (Roll *Strength + Brawl + 2* with *Hunger 2* and no set *Difficulty*. This roll assumes the user has only one character.)

Here is how a trait pool looks in the Discord textbox:

![Roll with traits](images/rolls/roll-traits.png)

?> Traits are **case-insensitive**, which is a fancy way of saying capitalization doesn't matter.

[filename](includes/universal-traits.md ':include')

### Trait Shorthand

**Inconnu** does not require you to type out a full trait name. All you need is the minimum number of letters for it to unambiguously match a trait. Refer to the table below for examples of good and bad shorthand.

| Shorthand | OK? | Explanation                                               |
|-----------|-----|-----------------------------------------------------------|
| `stre`    | ❌   | Could match `strength` or `streetwise`                    |
| `ac`      | ✅   | Matches `academics`                                       |
| `b`       | ✅   | Matches `brawl`                                           |
| `in`      | ❌   | Could match `intimidation`, `insight`, or `investigation` |

**Example:** `/vr syntax:stren + b` `Nadea` (Rolls Nadea's *Strength + Brawl*, no *Hunger*, no *Difficulty*)

![Shorthand traits in a roll](images/rolls/roll-traits-short.png)

## Willpower Re-rolls

Finally, **Inconnu** allows you to perform a Willpower re-roll. At the bottom of each roll will appear up to three buttons with the name of a re-roll strategy to use. The person who made the roll (and only that person) can press one of the buttons to re-roll up to three non-Hunger dice.

The strategies are as follows.

| Strategy                 | Description                                                        | Available when ...                                        |
|--------------------------|--------------------------------------------------------------------|-----------------------------------------------------------|
| **Re-Roll Failures**   | Re-roll only non-successful dice                               | There are one or more non-successful dice                 |
| **Maximize Criticals** | Re-roll up to three failures plus non-critical successful dice | There are one or more non-critical dice                   |
| **Avoid Messy**        | Re-roll up to three critical dice                              | A Messy Critical exists with only one critical Hunger die |
| **Risky Avoid Messy**  | Re-roll up to three critical dice plus leftover failures       | A Messy Critical exists with only one critical Hunger die and there are one or more failure dice |

?> **Just how risky is "risky"?** A *Risky* re-roll has up to a **27% chance** of retaining a Messy Critical, but the actual answer depends on your roll outcome. Each non-successful die rolled by *Risky* increases the likelihood you will retain a Messy Critical. At one re-rolled die, you have only a 10% chance of retaining a Messy critical. Even increasing it to two dice yields an 18% (nearly 1 in 5) chance of retaining a Messy Critical. Is it worth it? That's up to you.
