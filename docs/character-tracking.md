# Character Tracking

The following is a complete reference for Inconnu's character tracking and management features. If this is your first time using Inconnu, you are encouraged to read the **[Quickstart](quickstart.md)** first.

[filename](includes/parameter-style.md ':include')

?> Looking for traits? Check out **[Trait Management](trait-management.md)**.


## Character Creation

Character creation is done with the `//new` command, which has the following, required syntax:

```
//new name=N type=T hp=HP wp=W humanity=HU

```

| Parameter  | Description                                               |
|------------|-----------------------------------------------------------|
| `name`     | The character's name. May contain letters and underscores |
| `type`     | The "type" of character: vampire, mortal, or ghoul        |
| `hp`       | The number of Health levels the character has (Number)    |
| `wp`       | The number of Willpower levels the character has (Number) |
| `humanity` | The character's Humanity rating (Number)                  |

## Character Display

```
//display [character]

```

| Parameter   | Description                                               |
|-------------|-----------------------------------------------------------|
| `character` | The name of the character to display                      |

If `character` is omitted, then one of two things will happen:

* If you have only one character, that character will be displayed
* If you have multiple characters, a list of them will be displayed

## Tracker Updates

```
//update [character] <tracker>=<rating> ...

```
This is a multi-parameter command. You may supply as many trackers as you like.

| Parameter   | Description                                               |
|-------------|-----------------------------------------------------------|
| `character` | The name of the character to modify                       |
| `tracker`   | The tracker to modify                                     |

?> `character` is optional if you have only one character.

The following trackers are available:

| Parameter   | Description                                               |
|-------------|-----------------------------------------------------------|
| `name`      | The character's new name                                  |
| `Health`    | Maximum Health                                            |
| `Willpower` | Maximum Willpower                                         |
| `sh`        | Superficial Health damage                                 |
| `ah`        | Aggravated Health damage                                  |
| `sw`        | Superficial Willpower damage                              |
| `aw`        | Aggravated Willpower damage                               |
| `hunger`    | Hunger                                                    |
| `humanity`  | Humanity                                                  |
| `stains`    | Stains                                                    |
| `cur_xp`    | Current XP                                                |
| `total_xp`  | Total XP                                                  |

Apart from `name`, each key expects an integer, which you may supply in one of three forms: `+X`, `-X`, or plain `X`. The first two adjust the current value by positive or negative `X`. The last, however, *sets* the tracker to `X`.

!> When changing maximum Health and Willpower, **Inconnu** tries to prevent you from losing any *damage* data; however, modify it too much, and some will necessarily be lost. Similarly, when adjusting `total_xp`, reducing it below `cur_xp` will reduce `cur_xp` by the appropriate amount.

## Character Deletion

```
//delete <character>

```
`character` is mandatory. When running this command, **Inconnu** will give you a confirmation box before deleting the character.

!> **This cannot be undone!** Deleting a character also removes all associated traits.
