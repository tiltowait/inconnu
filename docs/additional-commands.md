# Additional Commands

?> For each command listed here, the `character` parameter is optional if you only have one character.

Each command below is a "slash" or "application" command. As you type, Discord will automatically show a list of matching commands above your textbox, which you can tap or click to perform.

## Aggravated Healing

The `/aggheal` command automatically heals your character by one Aggravated damage and rolls three Rouse checks, displaying the results (and any ensuing Hunger Frenzies) in a single command.

## Awakening

Each night a character wakes, they heal Superficial Willpower damage and make a Rouse check. **Inconnu** automates this process with the `/awaken` command. It will even tell you if you were unfortunate enough to fall into torpor!

## Crippling Injuries

```
/cripple damage:[DAMAGE] character:[CHARACTER]
```

This command rolls against the "crippling injury" table foudn on p.303. If a character is not supplied, then it is necessary to provide a `damage` value.

| Parameter    | Description                                |
|--------------|--------------------------------------------|
| `damage`     | The total aggravated damage suffered       |
| `character`  | The character taking the injury            |

## Frenzy checks

```
/frenzy difficulty:<difficulty> character:[character]
```

| Parameter    | Description                                |
|--------------|--------------------------------------------|
| `difficulty` | The difficulty of the frenzy check         |
| `character`  | The character resisting frenzy             |

Per *V5*, p.219, Inconnu will roll your current Willpower plus 1/3 of Humanity, rounded down, and tell you the results.

## Mending damage

To mend Superficial damage, simply type `/mend` `[character]`. This will mend the appropriate amount of damage based on your Blood Potency (using the V5 Companion errata) and perform a Rouse check.

## Percentile Dice

A random number between 1 and `ceiling` (default `100`) may be rolled with the `/percentile` command.

## Probability calculation

It is possible to calculate roll outcome probabilities using the `/probability` command.

```
/probability roll:<roll> character:[character]
```

The `roll` parameter can be any valid roll, such as `7 3 2` (pool 7, hunger 3, difficulty 2) or even a trait-based roll like `Resolve + Academics 2 4`.

## Remorse Checks

When a character has [Stains](character-tracking.md#tracker-updates), you may perform a Remorse Check. This check follows the rules in the V5 core book: **Inconnu** rolls dice equal to the number of unmarked Humanity boxes, to a minimum of 1. If the result is a success, Humanity is maintained. If it fails, Humanity is automatically deducted by one. In either case, all accumulated Stains are removed.

```
/remorse character:[character]
```

| Parameter   | Description                                |
|-------------|--------------------------------------------|
| `character` | The character performing the remorse check |

!> While there is at least one Loresheet that increases the minimum number of dice rolled for Remorse, **Inconnu** does not yet have that functionality. It will be added in a future update.

## Resonance

You may generate a random Resonance and Temperament with the `/resonance` command.

## Rouse checks

**Inconnu** can perform basic Rouse checks. Additionally, **Inconnu** will automatically increase the indicated character's Hunger rating if the rouse is a failure.

```
/rouse count:[count] character:[character] purpose:[purpose] reroll:[Yes/No]
```

| Parameter   | Description                              |
|-------------|------------------------------------------|
| `count`     | The number of rouse checks to perform    |
| `character` | The character performing the rouse check |
| `purpose`   | The reason for the rouse check           |
| `reroll`    | Whether to re-roll failures              |

!> **Mortals and Ghouls:** Mortals may not make Rouse checks. Ghouls, on the other hand, take one level of Aggravated damage instead of making a Rouse check, as per p.234 in the V5 core book.

## Slaking Hunger

As a shorthand for `/character update hunger=-X`, the `/slake` command allows you to quickly reduce your Hunger by whatever amount you specify.
