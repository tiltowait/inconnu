# Updating your macros

Sometimes you need to update a macro. Maybe you mistyped something, or maybe you have a new specialty that applies to the roll. To make a permanent change to a macro (not simply a [one-time modifier](optional-modifiers.md)), you need the `/macro update` command.

> [!NOTE]
> **Updating Macros**
>
> ```
> /macro update macro:<macro name> parameters:[parameters]
> ```

Just what are these `parameters`? The first several are self-explanatory:

* `name`: Set this to change the macro's name.
* `pool`: For updating the macro's pool. Accepts any valid pool.
* `hunger`: Set to \*Yes\* or \*No\* to include Hunger in the roll.
* `difficulty`: The macro's new default difficulty. Must be a number 0 or higher.

The next five take a little more explaining.

* `rouses`: You can set a macro to make one or more Rouse checks as part of the roll. This is useful for activating Disciplines. This number must be 0 or higher.
* `reroll_rouses`: Whether to re-roll failed the macro's failed Rouse checks once each. Does nothing if `rouses` is 0 or unset.
* `staining`: A simple _Yes/No_ setting. Use this if the Rouse checks set in `rouses` are part of an Oblivion roll. With staining set to _Yes_, then a 1 or a 10 on a Rouse check will give your character one Stain.
* `hunt`: Another _Yes/No_ setting. If set to _Yes_, then a successfull roll will surface a menu for slaking Hunger. Red buttons are harmful drinks, and blue are safe. Once you slake, the menu will be replaced with an automatic Resonance check.
* `comment`: A comment that will be added to the bottom of the roll's readout.

> [!NOTE]
> All of these update parameters are available as optional parameters when you create a macro.

> [!TIP]
> **Example:** We [made a macro](your-first-macro.md) called _hunt_ earlier. Let's tell **Inconnu** that it is, in fact, a `hunt` macro. Let's also permanently set the difficulty to 4. Those dang SI aren't going away.
>
> ```
> /macro update macro:hunt parameters:hunt=yes difficulty=4
> ```
>
> Now, whenever we `/vm syntax:hunt`, we will get a menu to slake Hunger if the roll is successful.

> [!NOTE]
> **Just like when** [**adding traits**](../quickstart/custom-traits.md)**,** you may update multiple macro parameters at a time.
