---
description: Sky's the limit.
---

# Custom Traits

Running homebrew? Have some Merits or Flaws you roll? You can track these (and any other Trait with a 0–5 rating) with **custom Traits**.

### Adding Traits

> [!NOTE]
> **Syntax:**
>
> ```
> /traits add traits:<TRAIT=RATING> [TRAIT2=RATING2] [TRAIT3=RATING3] ...
> ```

You can add several Traits at once. For example:

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

For safety, you can't `add` a Trait you already have. To change one, use `/traits update traits:`, which takes the same syntax.

To delete Traits, use `/traits delete traits:`, separating names with spaces. This also deletes any associated [specialties](specialties.md) or [powers](disciplines-and-powers.md#powers).

> [!WARNING]
> Unlike rolls, updates and deletions need full names: _ac_ won't match _Academics_. That keeps you from changing or deleting the wrong Trait.

> [!NOTE]
> Deleting a core Trait, such as Strength or Athletics, sets it to 0 instead.
