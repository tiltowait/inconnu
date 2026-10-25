---
description: Follow this guide to learn all about macros!
---

# Macros

Macros automate your rolls. With a single command, you can roll a complex pool, make a Rouse check, earn Stains for Oblivion rolls, and even slake Hunger. A character can have as many macros as you need.

Every macro command, with all its options, is in the [macro reference](../command-reference/macros.md).

## Your first macro

The simplest macro is a saved roll:

```
/macro create name:<name> pool:<pool> hunger:<Yes/No> difficulty:<difficulty>
```

* `name`: What you'll type to roll it. It must be unique to the character.
* `pool`: Any [valid roll pool](quickstart/rolling-with-traits.md). Traits are better than raw numbers, since they stay current when your character changes.
* `hunger`: Whether to use your character's current Hunger. Usually `Yes`.
* `difficulty`: The roll's difficulty.

> [!TIP]
> **Example:** Nadea is a Graverobber, so she hunts with _Resolve + Medicine_. She also has a Medicine [specialty](quickstart/specialties.md), _Cadavers_.
>
> ```
> /macro create name:hunt pool:resolve+medicine.cadavers hunger:Yes difficulty:3
> ```

## Rolling a macro

```
/vm syntax:<macro name>
```

> [!TIP]
> **Example:** Rolling Nadea's _hunt_ macro:
>
> ```
> /vm syntax:hunt
> ```

## Optional modifiers

Sometimes a roll needs a one-time change: the SI is extra active tonight, or a coterie member is helping. Write the changes after the macro's name: first the pool, then Hunger, then difficulty.

> [!TIP]
> **Example:** A coterie member grants a bonus die, and the difficulty rises to 4:
>
> ```
> /vm syntax:hunt + 1 hunger 4
> ```
>
> You can add or subtract as many traits and numbers as you like.

> [!NOTE]
> `hunger` is a special trait every vampire has: their current Hunger. If Nadea's Hunger is 3, `hunger` means `3`.

> [!CAUTION]
> **Only vampires have Hunger!** Using `hunger` with a mortal or ghoul gives an error.

## Making it a hunt

Macros can do more than roll. With `/macro update`, we'll make _hunt_ offer a menu to slake Hunger when the roll succeeds, and permanently raise its difficulty:

```
/macro update macro:hunt parameters:hunt=yes difficulty=4
```

In the menu, red buttons are harmful drinks and blue are safe. Once you slake, **Inconnu** makes a Resonance check.

Macros can also make Rouse checks (`rouses`), re-roll them (`reroll_rouses`), and give Stains for Oblivion (`staining`). See [`/macro update`](../command-reference/macros.md#macro-update) for every setting.

## Rouse-only macros

A macro's pool can be `0`, which makes a quick, labeled Rouse check. Powers like Toughness don't need a roll, but `/rouse reroll:Yes purpose:Toughness` is a lot to type every time.

> [!TIP]
> **Example:** Nadea has Blood Potency 3 and Toughness:
>
> ```
> /macro create name:toughness pool:0 hunger:Yes difficulty:0 rouses:1 reroll_rouses:Yes comment:Toughness
> ```
>
> Now `/vm syntax:toughness` makes the Rouse check.

> [!NOTE]
> With a pool of 0, `hunger` and `difficulty` are ignored.

> [!WARNING]
> **A macro with no pool and no Rouse checks does nothing!**
