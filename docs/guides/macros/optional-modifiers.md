---
description: Because sometimes, you need to make temporary changes.
---

# Optional modifiers

When you roll a macro, sometimes you need to make changes to your pool or your difficulty. Maybe your character is impaired or maybe the SI is extra active tonight. Maybe you have a Discipline power that lets you ignore Hunger. Whatever the case, **Inconnu** allows you to roll using one-time modifiers to your macros.

To apply optional modifiers, you simply write additional syntax after the `macro name`, modifying first the `pool`, followed by the `hunger`, and finally the `difficulty`.

> [!TIP]
> **Example:** We want to roll our _hunt_ macro. The SI is extra active tonight, raising the difficulty to 4, but we're in luck: a coterie member is helping us out, granting one bonus die.
>
> ```
> /vm syntax:hunt + 1 hunger 4
> ```
>
> You aren't limited to a simple "+1". In fact, you can add or subtract as many additional traits/numbers as you like. For this example, however, we're keeping it simple.

> [!NOTE]
> **Special trait:** `hunger` is a special trait all vampire characters have. As you might expect, it represents the character's current Hunger rating. If our Hunger was 3, then invoking `hunger` is the same as writing the number `3`.

> [!CAUTION]
> **Only vampires have Hunger!** If you try to use `hunger` with a mortal character (or ghoul), **Inconnu** will give you an error message.
