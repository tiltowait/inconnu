# Character Tracking

The following is a complete reference for Inconnu's character tracking and management features. If this is your first time using Inconnu, you are encouraged to read the **[Quickstart](quickstart.md)** first.

[filename](includes/parameter-style.md ':include')

?> Looking for traits? Check out **[Trait Management](trait-management.md)**.

All character management is done through the `/character` application command prefix. As you begin typing, Discord should automatically show a list of command options above your textbox. Simply click/tap the one you want (or continue to type in the name). On the desktop, you can tab through command parameters, while mobile lets you tap through.

## Character Creation

Character creation is done with the `/character create` command, which requires the following parameters:

| Parameter   | Description                                               |
|-------------|-----------------------------------------------------------|
| `name`      | The character's name. May contain letters and underscores |
| `splat`     | The "type" of character: vampire, mortal, or ghoul        |
| `humanity`  | The character's Humanity rating (Number)                  |
| `health`    | The number of Health levels the character has             |
| `willpower` | The number of Willpower levels the character has          |

The only option that requires any typing (and thus the only one it is possible to get wrong) is `character`. Once you've entered your command, Inconnu will DM you and guide you throguh the rest of the character creation process. This will fill out every Skill and Attribute on the character sheet.

#### Example

![Character creation example](includes/character-create.png)

## Character Display

```
/character display [character]
```

| Parameter   | Description                                               |
|-------------|-----------------------------------------------------------|
| `character` | The name of the character to display                      |

The `character` field is only required if you have more than one character in the server.

* If you have only one character or supply `character`, that character will be displayed
* If you have multiple characters, a list of them will be displayed

## Tracker Updates

```
/character update <parameters> [character]
```
This is a multi-parameter command. You may supply as many trackers as you like.

| Parameter    | Description                                               |
|--------------|-----------------------------------------------------------|
| `parameters` | The `tracker=value` pairs                                 |
| `character`  | The name of the character to modify                       |

?> `character` is optional if you have only one character.

The following `trackers` names are recognized:

| Parameter    | Description                                               |
|--------------|-----------------------------------------------------------|
| `name`       | The character's new name                                  |
| `health`     | Maximum Health                                            |
| `willpower`  | Maximum Willpower                                         |
| `sh`         | Superficial Health damage                                 |
| `ah`         | Aggravated Health damage                                  |
| `sw`         | Superficial Willpower damage                              |
| `aw`         | Aggravated Willpower damage                               |
| `hunger`     | Hunger                                                    |
| `humanity`   | Humanity                                                  |
| `stains`     | Stains                                                    |
| `current_xp` | Current XP                                                |
| `total_xp`   | Total XP                                                  |

**Example:** `/character update sh=+2 ah=+1` (Add two *Superficial Health* and one *Aggravated Health* damage)

Apart from `name`, each key expects an integer, which you may supply in one of three forms: `+X`, `-X`, or plain `X`. The first two adjust the current value by positive or negative `X` while the last *sets* the `tracker` to `X`.

!> When changing maximum Health and Willpower, **Inconnu** tries to prevent you from losing any *damage* data; however, reduce either by too much, and some information will inevitably be lost. Similarly, when adjusting `total_xp`, reducing it below `current_xp` will reduce `current_xp` by the appropriate amount.

## Character Deletion

```
/character delete <character>
```

`character` is mandatory. When running this command, **Inconnu** will give you a confirmation box before deleting the character.

!> **This cannot be undone!** Deleting a character also removes all associated traits and macros.
