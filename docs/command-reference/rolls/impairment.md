---
description: How Inconnu applies Impairment penalties to your rolls.
---

# Impairment

When a character is Impaired, **Inconnu** removes 2 dice from the affected rolls for you.

| Condition | Impairment | Penalized rolls |
| --- | --- | --- |
| Every Health box is damaged | Physical | Physical |
| Every Willpower box is damaged | Mental | Social and Mental |
| Degeneration (Stains exceed unmarked Humanity boxes) | Total | All |

If every Health box is Aggravated, **Inconnu** also tells you that you're in torpor (vampires) or dead (everyone else).

### Which rolls are penalized

**Inconnu** decides a roll's category from the **Attributes** in its pool:

* **Physical:** Strength, Dexterity, Stamina
* **Social and Mental:** Charisma, Manipulation, Composure, Intelligence, Wits, Resolve

Skills, Disciplines, and custom traits don't affect the category. A pool with both a Physical and a Social or Mental Attribute is penalized by either kind of Impairment. Pools without an Attribute, such as `7` or `Auspex + Awareness`, are never penalized automatically.

The penalty shows in the roll's **Pool** field:

```
Strength + Brawl - 2 (physical impairment)
```

### Changing the category for one roll

`/vr`, `/roll`, `/vm`, and `/probability` take an `impairment_category` option:

| Choice | Effect |
| --- | --- |
| `Physical` | Treat the roll as Physical |
| `Mental/Social` | Treat the roll as Social or Mental |
| `Ignore` | Don't apply Impairment |

Use it when the pool doesn't say what the roll is. For instance, a Discipline roll with no Attribute, or Strength + Intimidation used socially. When the option changes the outcome, the roll's footer says so (for example, `Override: Impairment ignored`).

> [!TIP]
> **Example:** Your character is mentally Impaired and rolls Wits + Awareness to notice an ambush. Your Storyteller rules it isn't affected:
>
> ```
> /vr syntax:wits+awareness impairment_category:Ignore
> ```

### Turning it off

If you'd rather subtract the dice yourself, turn off **Automatically apply Impairment?** in [`/settings scope:Yourself`](../../advanced/server-settings.md#automatically-apply-impairment). **Inconnu** then reminds you of your Impairment in the roll's footer instead. The setting is per player and follows you across servers.

`impairment_category` still applies its penalty when the setting is off.

> [!NOTE]
> [Hidden rolls](hidden-dice.md) don't show the penalty or Impairment reminders to other players, since they would reveal your character's condition.
