# 🎲 Gameplay Shortcuts

The following shortcuts encompass common actions. Using them prevents needing to issue complex `/character update` commands.

> [!NOTE]
> Most of these commands have an optional `character` parameter. To keep things simple, it is omitted from the command listings.

## Aggravated Healing

The `/aggheal` command automatically heals your character by one Aggravated damage and rolls three Rouse checks, displaying the results (and any ensuing Hunger Frenzies) in a single command.

> [!NOTE]
> Only vampires and thin-bloods make Rouse checks.

## Applying Stains

```
/stain delta:<DELTA>
```

| Parameter | Description                           | Notes                                                 |
| --------- | ------------------------------------- | ----------------------------------------------------- |
| `delta`   | The number of stains to add or remove | Can be positive or negative. Always adds or subtracts |

## Awakening

Each night a character wakes, they heal Superficial Willpower damage and make a Rouse check. **Inconnu** automates this process with the `/awaken` command. It will even tell you if you were unfortunate enough to fall into torpor!

> [!NOTE]
> Instead of making a Rouse check, mortals and ghouls will heal a number of Superficial Health damage equal to their Stamina rating.

## Blush of Life

```
/bol
```

This command performs a "blush of life" check for your character, taking your Humanity into account. It is equivalent to `/rouse` `count:1` `purpose:Blush of Life`, plus `reroll:Yes` if your character is at Humanity 8. At Humanity 9 and 10, it will inform you that you do not need to make the check.

## Crippling Injuries

```
/cripple damage:[DAMAGE]
```

This command rolls against the "crippling injury" table foudn on p.303. If a character is not supplied, then it is necessary to provide a `damage` value.

| Parameter | Description                          |
| --------- | ------------------------------------ |
| `damage`  | The total aggravated damage suffered |

## Frenzy checks

```
/frenzy difficulty:<difficulty> penalty:[penalty] bonus:[bonus]
```

| Parameter    | Description                        |
| ------------ | ---------------------------------- |
| `difficulty` | The difficulty of the frenzy check |
| `penalty`    | A dice penalty to apply            |
| `bonus`      | Bonus dice to apply to the roll    |

Per _V5_, p.219, Inconnu will roll your current Willpower plus 1/3 of Humanity, rounded down, and tell you the results.

## Mending damage

To mend Superficial damage, simply type `/mend`. This will mend the appropriate amount of damage based on your Blood Potency (using the V5 Companion errata) or Stamina (for mortals) and perform a Rouse check.

## Remorse Checks

When a character has Stains, you may perform a Remorse Check. This check follows the rules in the V5 core book: **Inconnu** rolls dice equal to the number of unmarked Humanity boxes, to a minimum of 1. If the result is a success, Humanity is maintained. If it fails, Humanity is automatically deducted by one. In either case, all accumulated Stains are removed.

```
/remorse min_override:[OVERRIDE]
```

> [!NOTE]
> **What is `min_override`?** This parameter facilitates loresheets that allow you to roll a minimum number of dice on Remorse checks. _**Most players can ignore this parameter!**_ If you use it, the response embed will say so.

## Resonance & Temperament

You may generate a random Resonance and Temperament with the `/resonance` command. To get a random Temperament with a specified Resonance, use `/temperament`.

## Rouse checks

**Inconnu** can perform basic Rouse checks. Additionally, **Inconnu** will automatically increase the indicated character's Hunger rating if the rouse is a failure.

```
/rouse count:[count] purpose:[purpose] reroll:[Yes/No]
```

| Parameter | Description                           |
| --------- | ------------------------------------- |
| `count`   | The number of rouse checks to perform |
| `purpose` | The reason for the rouse check        |
| `reroll`  | Whether to re-roll failures           |

> [!WARNING]
> **Mortals and Ghouls:** Mortals may not make Rouse checks. Ghouls, on the other hand, take one level of Aggravated damage instead of making a Rouse check, as per p.234 in the V5 core book.

## Slaking Hunger

Use `/slake` to quickly reduce your Hunger by whatever amount you specify.

> [!NOTE]
> **If you are at Hunger 4 or 5,** you will get a button to test for Hunger Frenzy. Only vampires and thin-bloods can slake Hunger.
