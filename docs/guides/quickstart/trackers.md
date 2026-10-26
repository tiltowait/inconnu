---
description: >-
  In addition to Attributes, Skills, and custom Traits, Inconnu keeps track of
  Health, Willpower, Humanity, Hunger, and more.
---

# Trackers

As you saw when you [created your character](creating-a-character.md), each character has trackers: Health, Willpower, and Humanity, plus Hunger and Blood Potency for vampires. **Inconnu** also tracks _lifetime_ and _unspent_ XP. You change these with `/character adjust`.

Its optional parameters cover nearly every aspect of your character.

> [!TIP]
> **Example:** Nadea takes two Superficial Health damage, one Aggravated Health damage, and one Superficial Willpower damage.
>
> ```
> /character adjust sup_hp:+2 agg_hp:+1 sup_wp:+1
> ```

### Plus, minus, or nothing

In the example, `+2` and `+1` add damage, and `-` would remove it. Leave off the sign, and **Inconnu** _sets_ the value instead: with three Superficial Health damage, `sup_hp:2` brings it down to two.

> [!NOTE]
> **Why not just subtract Health?** The `health` parameter sets the size of your Health track. Damage is tracked separately, so you add damage rather than subtracting Health.
