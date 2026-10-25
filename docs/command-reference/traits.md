---
description: Commands for adding, updating, and removing traits.
---

# Traits

New to **Inconnu**? The [Quickstart](../guides/quickstart/README.md) walks you through traits.

## What are traits?

A trait is anything you can roll: Attributes, Skills, Disciplines, and any custom traits you add. Specialties and Discipline powers attach to a trait.

The character wizard sets your Attributes, Skills, and (for vampires) Blood Potency. You can add, update, and remove traits whenever you like.

> [!WARNING]
> **Universal traits:** Every character has `willpower`, `humanity`, `surge`, `potency`, and `hunger`. You can roll them, and they update with your character's trackers, but you can't create or delete traits with those names.

## /traits add

```
/traits add traits:<trait=rating ...> character:[character]
```

Adds one or more traits.

> [!TIP]
> **Example:** Adding Oblivion 4, Fortitude 2, and a custom trait, Stunning 2:
>
> ```
> /traits add traits:Oblivion=4 Fortitude=2 Stunning=2 character:Nadea
> ```

> [!CAUTION]
> Adding a trait that already exists is an error. Use `/traits update` instead.

## /traits update

```
/traits update traits:<trait=rating ...> character:[character]
```

Changes the ratings of one or more existing traits. Use each trait's full name.

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

Shows the character's traits, grouped by category, plus their specialties and powers.

## /traits delete

```
/traits delete traits:<trait ...> character:[character]
```

Removes one or more traits.

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
