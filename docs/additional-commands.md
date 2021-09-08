# Additional Commands

?> For each command listed here, the `character` parameter is optional if you only have one character.

Each command below is a "slash" or "application" command. As you type, Discord will automatically show a list of matching commands above your textbox, which you can tap or click to perform.

## Rouse Checks

**Inconnu** can perform basic Rouse checks. Additionally, **Inconnu** will automatically increase the indicated character's Hunger rating if the rouse is a failure.

```
/rouse [character] [count]
```

| Parameter   | Description                              |
|-------------|------------------------------------------|
| `count`     | The number of rouse checks to perform    |
| `character` | The character performing the rouse check |

!> At the time of this writing, **Inconnu** lacks the ability to perform a Rouse *re-roll*, such as one granted by Blood Potency. This functionality is a planned improvement.

## Remorse Checks

When a character has [Stains](character-tracking.md#tracker-updates), you may perform a Remorse Check. This check follows the rules in the V5 core book: **Inconnu** rolls dice equal to the number of unmarked Humanity boxes, to a minimum of 1. If the result is a success, Humanity is maintained. If it fails, Humanity is automatically deducted by one. In either case, all accumulated Stains are removed.

```
/remorse [character]
```

| Parameter   | Description                                |
|-------------|--------------------------------------------|
| `character` | The character performing the remorse check |

!> While there is at least one Loresheet that increases the minimum number of dice rolled for Remorse, **Inconnu** does not yet have that functionality. It will be added in a future update.

## Resonance

You may generate a random Resonance and Temperament with the `/resonance` command.
