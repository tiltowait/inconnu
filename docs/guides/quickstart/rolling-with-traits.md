---
description: >-
  Unlike other dice rollers, Inconnu allows you to roll by naming your
  Attributes and Skills.
---

# 🎲 Rolling with traits

> [!NOTE]
> **Basic roll syntax:**
>
> ```
> /roll pool:<POOL> hunger:<HUNGER> difficulty:<DIFFICULTY>
> ```

While you can supply raw numbers for each of these parameters, **Inconnu** really shines when you use _traits_. Traits are the Attributes and Skills you supplied while making the character, plus any custom traits you might define later.

> [!TIP]
> **Example:** Nadea is performing research at the library. She's at _hunger 2_, and the information is hard to find, so the roll is against _difficulty 4_. The pool is _Resolve_ plus _Academics_, and she has a research specialty that grants her a bonus die.
>
> ```
> /roll pool:resolve + academics + 1 hunger:Use Current difficulty:4
> ```
>
> From this syntax, **Inconnu** interprets the following:
>
> * `pool`: Resolve + Academics + 1
> * `hunger`: Nadea's current Hunger rating
> * `difficulty:` 4

> [!NOTE]
> **Notice that we didn't capitalize _Resolve_ or _Academics_?** That's fine. **Inconnu** doesn't care about that. In fact, we didn't even need to write the full trait names! You can provide an abbreviated name so long as **Inconnu** can match it to a _single_ trait name. Thus, we could have supplied `r` for _Resolve_ and `ac` for _Academics_, making our `pool` a much quicker `r + ac + 1`!

> [!WARNING]
> **You might have noticed we didn't provide a character name in our roll.** So long as you have only **one character**, you won't need to supply a character name for most functions. As soon as you add a second, however, you will need to supply the name of the character so **Inconnu** knows which traits to look up. Even then, in certain circumstances, Inconnu is smart enough to know which character can perform a given interaction. Feel free to experiment!
