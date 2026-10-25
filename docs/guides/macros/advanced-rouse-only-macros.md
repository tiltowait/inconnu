# Advanced: Rouse-only macros

We learned earlier that a macro's `pool` can be any valid [roll pool](../quickstart/rolling-with-traits.md). What we _didn't_ learn is that a macro's pool may also be _0._

Why would you want a pool of 0? Many players use "zero-pool" macros for commented Rouse checks. Let's say your character has the _Toughness_ power. This power doesn't require a roll to activate. While you _could_ use `/rouse purpose:Toughness`, that's a lot of typing. And what if your Blood Potency is 3 or higher? It becomes an even longer command: `/rouse reroll:Yes purpose:Toughness`.

To save time, you can make a "Rouse-only macro".

> [!TIP]
> **Example:** Nadea has Blood Potency 3 and the Toughness power. To save time, we want a macro called _Toughness_ that makes the appropriate, labeled Rouse check.
>
> ```
> /macro create name:toughness pool:0 hunger:Yes difficulty:0 rouses:1 reroll_rouses:Yes comment:Toughness
> ```
>
> With this macro created, we can perform the Rouse check with a much shorter `/vm syntax:toughness`.

> [!NOTE]
> With a zero-pool macro, `hunger` and `difficulty` are effectively ignored.

> [!WARNING]
> **It's possible to make a macro that does nothing!** If there's no pool and no Rouse check, then ... nothing will happen.
