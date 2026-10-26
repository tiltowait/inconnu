---
description: >-
  In addition to Attributes, Skills, and custom Traits, Inconnu keeps track of
  Health, Willpower, Humanity, Hunger, and more.
---

# Trackers

As you saw when you [created your character](creating-a-character.md), each character has base trackers: Humanity, Health, Willpower, Hunger, and Blood Potency. In addition, **Inconnu** tracks both _lifetime_ XP and _unspent_ XP. Modifying these is done with the `/character adjust` command.

This command has over a dozen optional parameters for modifying nearly every aspect of your character.

> [!TIP]
> **Example:** Nadea has taken two levels of Superficial Health damage, one level of Aggravated Health damage, and one level of Superficial Willpower damage.
>
> ```
> /character adjust sup_hp:+2 agg_hp:+1 sup_wp:+1
> ```

### Plus, minus, or nothing

In the example above, we wrote `+2` and `+1`. We could of course have reduced damage by subtracting (with `-`) instead. But what happens if we leave off `+` or `-`? In that case, **Inconnu** will _set_ the value to that level rather than adding or subtracting from the current value. If you have three levels of Superficial Health damage, `sup_hp:2` (without the plus sign) will reduce your damage to two boxes.

> [!NOTE]
> **Why can't I just subtract Health?** New users sometimes get confused about having to "add" damage versus "subtracting" Health. There's an important distinction: the `health` parameter reflects the overall size (number of boxes) of your Health track. When you "add" damage, you are _applying_ it.
