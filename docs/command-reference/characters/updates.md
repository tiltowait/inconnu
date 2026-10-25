# Updates

**Inconnu** tracks your character's basic statistics, such as Health and Willpower. This tutorial will teach you how to update these trackers.

> [!NOTE]
> **Is the following too complicated?** Try the `/character adjust` command. Its arguments behave identically to the parameters below.

```
/character update parameters:<parameters> character:[character]
```

This is a multi-parameter command. You may supply as many trackers as you like.

| Parameter    | Description                                    |
| ------------ | ---------------------------------------------- |
| `parameters` | The `tracker=value` pairs                      |
| `character`  | The name of the character to modify (optional) |

The following `parameters` are recognized:

| Parameter     | Description                                                                |
| ------------- | -------------------------------------------------------------------------- |
| `name`        | The character's new name                                                   |
| `health`      | Maximum Health                                                             |
| `willpower`   | Maximum Willpower                                                          |
| `sh`          | Superficial Health damage                                                  |
| `ah`          | Aggravated Health damage                                                   |
| `sw`          | Superficial Willpower damage                                               |
| `aw`          | Aggravated Willpower damage                                                |
| `hunger`      | Hunger                                                                     |
| `humanity`    | Humanity                                                                   |
| `stains`      | Stains                                                                     |
| `unspent_xp`  | Current unspent XP                                                         |
| `lifetime_xp` | The total XP earned over the character's lifetime (both spent and unspent) |

Apart from `name`, each key expects an integer, which you may supply in one of three forms: `+X`, `-X`, or plain `X`. The first two adjust the current value by positive or negative `X` while the last _sets_ the `tracker` to `X`.

> [!NOTE]
> **Example:** To _add_ 2 Superficial Health damage, _set_ Aggravated Health damage to 1, and _add_ 1 Stain to the character named Nadea:
>
> ```
> /character update parameters:sh+2 ah=1 stains+1 character:Nadea
> ```

> [!WARNING]
> When changing maximum Health and Willpower, **Inconnu** tries to prevent you from losing any _damage_ data; however, reduce either by too much, and some information will inevitably be lost. Similarly, when adjusting `lifetime_xp`, reducing it below `unspent_xp` will reduce `current_xp` by the appropriate amount.
