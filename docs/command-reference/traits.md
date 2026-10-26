---
description: Commands for adding, updating, and removing Traits.
---

# Traits

New to **Inconnu**? The [Quickstart](../guides/quickstart/README.md) walks you through Traits.

## What are Traits?

A Trait is anything you can roll: Attributes, Skills, Disciplines, and any custom Traits you add. Specialties and Discipline powers attach to a Trait.

The character wizard sets your Attributes, Skills, and (for vampires) Blood Potency. You can add, update, and remove Traits whenever you like.

> [!WARNING]
> **Universal Traits:** Every character has `willpower` and `humanity`, and vampires also have `hunger`, `surge`, `potency`, and `bane` (Bane Severity). You can roll them, and they update with your character's trackers, but you can't create or delete Traits with those names.

## /traits add

```
/traits add traits:<trait=rating ...> character:[character]
```

Adds one or more Traits.

> [!TIP]
> **Example:** Adding Oblivion 4, Fortitude 2, and a custom Trait, Stunning 2:
>
> ```
> /traits add traits:Oblivion=4 Fortitude=2 Stunning=2 character:Nadea
> ```

> [!CAUTION]
> Adding a Trait that already exists is an error. Use `/traits update` instead.

## /traits update

```
/traits update traits:<trait=rating ...> character:[character]
```

Changes the ratings of one or more existing Traits. Use each Trait's full name.

> [!TIP]
> **Example:** Raising Nadea's Awareness to 3:
>
> ```
> /traits update traits:Awareness=3 character:Nadea
> ```

## /traits list

```
/traits list character:[character] player:[player]
```

Shows the character's Traits, grouped by category, plus their specialties and powers.

## /traits delete

```
/traits delete traits:<trait ...> character:[character]
```

Removes one or more Traits.

> [!TIP]
> **Example:** Removing Oblivion and Fortitude:
>
> ```
> /traits delete traits:Oblivion Fortitude character:Nadea
> ```

> [!CAUTION]
> **This is permanent!** There is no confirmation.

## /disciplines

```
/disciplines add disciplines:<discipline=rating ...>
/disciplines update disciplines:<discipline=rating ...>
/disciplines remove disciplines:<discipline ...>
```

The same as the `/traits` commands, but for Disciplines. See [Disciplines & powers](../guides/quickstart/disciplines-and-powers.md).

## /specialties

```
/specialties add specialties:<skill=specialty,...>
/specialties remove specialties:<skill=specialty,...>
```

See [Specialties](../guides/quickstart/specialties.md).

## /powers

```
/powers add powers:<discipline=power,...>
/powers remove powers:<discipline=power,...>
```

See [Disciplines & powers](../guides/quickstart/disciplines-and-powers.md).
