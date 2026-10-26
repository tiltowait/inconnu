---
description: Sky's the limit.
---

# Custom Traits

Running homebrew? Have some Merits or Flaws you roll? You can track these (and any other Trait with a 0-5 rating) with **custom Traits**.

### Adding Traits

> [!NOTE]
> **Syntax:**
>
> ```
> /traits add traits:<TRAIT=RATING> [TRAIT2=RATING2] [TRAIT3=RATING3] ...
> ```

As you can see, you can add several Traits at once; you don't need to enter them one at a time. Let's look at an example.

> [!TIP]
> **Example:** Nadea has 3 dots in _Status_, _2_ in _Fame_, and the _Stunning_ Merit, which gives two dice.
>
> ```
> /traits add traits:Status=3 Fame=2 Stunning=2
> ```

<details>

<summary>Automatic Disciplines</summary>

**Inconnu** automatically converts the following custom Traits to Disciplines:

* Animalism
* Auspex
* BloodSorcery
* Celerity
* Dominate
* Fortitude
* Obeah
* Obfuscate
* Oblivion
* Potence
* Presence
* Protean
* Valeren
* Vicissitude
* WarriorValeren
* WatcherValeren

</details>

### Updating and deleting Traits

For safety, **Inconnu** doesn't allow you to `add` a Trait you already have. To modify an existing Trait, use the `/traits update traits:` command. This has the same syntax as `/traits add`.

Deleting Traits, on the other hand, can be done with `/traits delete traits:`. You can delete multiple Traits at once; simply separate them with spaces.

> [!WARNING]
> Unlike with rolls, Trait modification and deletion require you to be _explicit_ in your typing. You can't write _ac_ to represent _Academics_. This is done to prevent you from accidentally creating a bunch of useless Traits or modifying/deleting the wrong thing.

> [!NOTE]
> **If you delete a core Trait,** such as Strength or Athletics, **Inconnu** will instead make it a 0-dot Trait. This way, you won't receive errors if called to roll for a core Trait you accidentally deleted.
