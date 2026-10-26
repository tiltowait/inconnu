---
description: Commands for creating, rolling, and managing macros.
---

# Macros

New to macros? Start with the [macros guide](../guides/macros.md).

## /macro create

```
/macro create name:<name> pool:<pool> hunger:<Yes/No> difficulty:<difficulty>
```

| Option | Description | Notes |
| --- | --- | --- |
| `name` | The macro's name | Letters and underscores; up to 50 characters |
| `pool` | The roll's pool | Same syntax as [rolls](../guides/quickstart/rolling-with-traits.md); may be `0` |
| `hunger` | Whether to use the character's current Hunger | |
| `difficulty` | The default Difficulty | Can be changed when rolling |
| `rouses` | Rouse Checks to make when rolled | 0–5; default 0 |
| `reroll_rouses` | Whether to re-roll the Rouse Checks | Default `No` |
| `staining` | Whether the Rouse Checks can give a Stain (Oblivion) | Default `No`; see [Oblivion Stains](../advanced/server-settings.md#oblivion-stains) |
| `hunt` | Offer a menu to slake Hunger when the roll succeeds | Default `No` |
| `comment` | A comment shown with the roll | Up to 300 characters |
| `character` | The character who owns the macro | |

> [!TIP]
> **Example:** A hunting macro with a Difficulty of 3:
>
> ```
> /macro create name:hunt pool:resolve+medicine hunger:Yes difficulty:3 hunt:Yes comment:Nadea hunts mortuaries for fresh bodies
> ```

## /vm

Roll a macro.

```
/vm syntax:<macro> [pool modifier] [hunger] [difficulty]
```

| Option | Description |
| --- | --- |
| `syntax` | The macro's name, optionally followed by one-time changes to the pool, Hunger, and Difficulty |
| `character` | The character who owns the macro |
| `impairment_category` | Change the roll's [Impairment](rolls/impairment.md) category, or ignore Impairment |
| `dice` | `Hide` to [hide your dice](rolls/hidden-dice.md) from other players |

To change the Difficulty, you must also give Hunger, which can be as simple as `hunger` (the character's current Hunger).

> [!TIP]
> **Example:** Rolling _hunt_ with a two-die penalty, current Hunger, and Difficulty 4:
>
> ```
> /vm syntax:hunt-2 hunger 4
> ```

> [!NOTE]
> **Why `/vm`?** If `/vr` is "vampire roll", `/vm` is "vampire roll macro". Keeping it out of the `/macro` group makes it faster to type.

## /macro update

```
/macro update macro:<macro> parameters:<KEY=VALUE ...>
```

Change one or more of a macro's settings using `KEY=VALUE` pairs:

| Key | Description | Notes |
| --- | --- | --- |
| `name` | The macro's new name | Letters and underscores |
| `pool` | The new pool | Must be a valid pool |
| `hunger` | Whether to use Hunger | `Yes` or `No` |
| `difficulty` | The default Difficulty | 0 or higher |
| `rouses` | Rouse Checks to make | 0–3 |
| `reroll_rouses` | Whether to re-roll the Rouse Checks | `Yes` or `No` |
| `staining` | Whether the Rouse Checks can give a Stain | `Yes` or `No` |
| `hunt` | Offer a menu to slake Hunger on success | `Yes` or `No` |
| `comment` | The comment shown with the roll | |

> [!TIP]
> **Example:** Making _hunt_ a hunt macro and raising its Difficulty to 4:
>
> ```
> /macro update macro:hunt parameters:hunt=yes difficulty=4
> ```

## /macro list

```
/macro list character:[character]
```

Lists the character's macros alphabetically, only to you. Long lists have paging buttons.

## /macro delete

```
/macro delete macro:<macro> character:[character]
```

> [!CAUTION]
> **This is permanent!** There is no confirmation.
