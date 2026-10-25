---
description: Learn how to save a standard roll for later use.
---

# Your first macro

First, we'll look at the most basic type of macro: a saved roll.

> [!NOTE]
> **Macro Creation**
>
> ```
> /macro create name:<name> pool:<pool> hunger:<Yes/No> difficulty:<difficulty>
> ```

Let's take a look at those parameters.

* `name`: When you use a macro (more on that later), you will invoke it by its `name`. This `name` needs to be unique to the character.
* `pool`: This must be a [valid roll pool](../quickstart/rolling-with-traits.md) using either traits (preferred) or raw numbers.
* `hunger`: This is a simple yes or no: Whether to use your character's current Hunger rating or to set it to zero. Most of the time, you want _Yes_.
* `difficulty`: The difficulty against which the roll will be made.

> [!NOTE]
> **Example:** Let's make a macro called _hunt_. Our Predator Type is Graverobber, which gives us a hunting pool of _Resolve + Medicine_. We also have a _Medicine_ specialty that applies, called _Cadavers_, which we [added to our character](../quickstart/specialties.md).
>
> ```
> /macro create pool:resolve+medicine.cadavers hunger:Yes difficulty:3
> ```
>
> It's that simple!

Next, we'll see how to use the macro we just created.
