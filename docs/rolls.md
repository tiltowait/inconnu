# Rolls

What follows is a complete reference on **Inconnu's** roll function. If you're new to **Inconnu**, you are encouraged to read the **[Quickstart](quickstart.md)** first.

[filename](includes/parameter-style.md ':include')

## Basic Syntax

```
/vr <syntax: pool hunger difficulty> [character]

```
| Parameter    | Description                                              |
|--------------|----------------------------------------------------------|
| `pool`       | The total number of dice, including Hunger dice, to roll |
| `hunger`     | Your current level of Hunger (default 0)                 |
| `difficulty` | The test's Difficulty (default 0)                        |
| `character`  | The character performing the roll                        |

?> `character` is optional if you are not using a [trait pool](#trait-pools). Even if you are using one, `character` is still optional if you only have one character in the server.

## Trait Pools

`pool` is a special parameter. It accepts [traits](trait-management.md) in addition to numbers, and multiple traits can be combined in a simple addition/subtraction equation.

**Example:** `/vr Strength + Brawl + 2 2` (Roll *Strength + Brawl + 2* with *Hunger 2* and no set *Difficulty*. This roll assumes the user has only one character.)

?> Traits are **case-insensitive**, which is a fancy way of saying capitalization doesn't matter.

### Trait Shorthand

**Inconnu** does not require you to type out a full trait name. All you need is the minimum number of letters for it to unambiguously match a trait. Refer to the table below for examples of good and bad shorthand.

| Shorthand | OK? | Explanation                                               |
|-----------|-----|-----------------------------------------------------------|
| `stre`    | ❌   | Could match `strength` or `streetwise`                    |
| `ac`      | ✅   | Matches `academics`                                       |
| `b`       | ✅   | Matches `brawl`                                           |
| `in`      | ❌   | Could match `intimidation`, `insight`, or `investigation` |

**Example:** `/vr stren + b` `Nadea` (Rolls Nadea's *Strength + Brawl*, no *Hunger*, no *Difficulty*)

## Comments
```
/vr <syntax> # Comment

```
Anything after a `#` will be ignored by **Inconnu's** roll parser and will be added to the bottom of the roll outcome view.

**Example:** `/vr stren + br + 2 2 0 # Nadea punches Jake` `Nadea` (Rolls Nadea's *Strength + Brawl + 2*, *Hunger 2*, no *Difficulty* with a comment of *Nadea punches Jake*.)

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
