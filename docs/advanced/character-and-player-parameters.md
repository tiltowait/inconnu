# Character and Player Parameters

Many commands offer optional `character` and `player` parameters, which are used to facilitate lookups.

* `character`: If you have more than one character, you may use this parameter to specify which character to use for a given command. If you do not supply the parameter, **Inconnu** will do its best to figure out which character you want. If it cannot, then a menu will pop up requesting you to select the character.
* `player`: In most instances, use of the `player` parameter is limited to server administrators. With it, administrators can view, roll as, or make changes to a character owned by another user.

> [!NOTE]
> **Automatic Character Filtering**
>
> If you don't specify a `character`, **Inconnu** will attempt to filter based on context. For instance, if you have a mortal and a vampire character, then running `/bol` will automatically use the vampire, because mortals can't use the Blush of Life. Similarly, if one of your characters has a custom Trait called _Necromancy_, then using `/roll` with _Necromancy_ in the pool will signify you want to use that character.
