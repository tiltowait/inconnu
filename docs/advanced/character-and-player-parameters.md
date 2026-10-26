# Character and Player Parameters

Many commands take optional `character` and `player` options.

* `character`: Which of your characters to use. Without it, **Inconnu** picks the one that fits, or shows a menu to choose from.
* `player`: Usually admin-only. Lets admins view, roll as, or change another player's character.

> [!NOTE]
> **Automatic Character Filtering**
>
> Without a `character`, **Inconnu** narrows your characters by context. If you have a mortal and a vampire, `/bol` uses the vampire, since mortals can't Blush. If only one character has a _Necromancy_ Trait, rolling _Necromancy_ uses that one.
