---
description: >-
  Unlike other dice rollers, Inconnu allows you to roll by naming your
  Attributes and Skills.
---

# Rolling with Traits

> [!NOTE]
> **Basic roll syntax:**
>
> ```
> /roll pool:<POOL> hunger:<HUNGER> difficulty:<DIFFICULTY>
> ```

You can use plain numbers, but **Inconnu** really shines when you use _Traits_: the Attributes and Skills you entered when making your character, plus any custom Traits you add later.

> [!TIP]
> **Example:** Nadea is researching at the library. She's at _Hunger 2_, and the information is hard to find, so the roll is at _Difficulty 4_. She rolls _Resolve_ plus _Academics_, with a bonus die from her research specialty.
>
> ```
> /roll pool:resolve + academics + 1 hunger:Use Current difficulty:4
> ```
>
> **Inconnu** reads this as:
>
> * `pool`: Resolve + Academics + 1
> * `hunger`: Nadea's current Hunger rating
> * `difficulty`: 4

> [!NOTE]
> **Notice we didn't capitalize _Resolve_ or _Academics_?** **Inconnu** doesn't mind. We didn't even need the full names: any abbreviation that matches a _single_ Trait works, so `r + ac + 1` would have done just as well.

> [!NOTE]
> **You might have noticed we didn't name a character.** You rarely need to. If you have several, **Inconnu** picks the one whose Traits fit the roll, or shows a menu to choose from.
