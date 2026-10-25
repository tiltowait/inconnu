---
description: For users familiar with Thirst ... or who just want to save a little time.
---

# ⚡ Advanced: Roll shorthand

> [!NOTE]
> **Shorthand Roll Syntax**
>
> ```
> /vr syntax:<pool> [hunger] [difficulty]
> ```
>
> **Note:** `hunger` and `difficulty` are optional!

This command behaves identically to `/roll`; the only difference is that the `pool`, `hunger`, and `difficulty` parameters are all combined into one `syntax` parameter. Both mobile users and those familiar with the popular Thirst bot may find this command easier to use.

<details>

<summary>Example</summary>

```
/vr syntax:intelligence+investigation hunger 3
```

This will roll the character's Intelligence and Investigation, using the current Hunger rating, at difficulty 3.

</details>

> [!WARNING]
> Because it is more prone to user error, however, all the examples in this documentation use the more explicit `/roll` command.

### Trait shorthand

As a reminder, when you roll with traits, you only need to provide **Inconnu** with enough information to infer which trait you want. When you supply a trait name, **Inconnu** finds all traits that start with your input. If only one trait starts with your input, then that's a match. This means you can supply _less_ than the full name of a trait, so long as it's unambiguous.

Let's look at an example. Consider the standard character sheet, which has seven traits that start with the letter "S":

* Science
* Stamina
* Stealth
* Streetwise
* Strength
* Subterfuge
* Survival

If you send the command, `/vr syntax: s`, then **Inconnu** won't know what to do with it, because it found seven potential matches. What if you give `st`? Then the bot will find "Stamina", "Stealth", "Streetwise", and "Strength"—still too many, but now it's only four. If you gave `sta`, on the other hand, only "Stamina" matches, and you have a match.

Thus, the following shorthand will roll Intelligence and Investigation, using current Hunger, at difficulty 3:

```
/vr syntax: inte+inv hun 3
```

> [!NOTE]
> When you create a macro, your traits will be expanded to their full match.

> [!WARNING]
> Your [custom traits](../traits/adding-traits.md) follow the same rules! This means that if you added a trait called "Staking", you would from then on need to write `stam` to match "Stamina" and `stak` to match "Staking."
