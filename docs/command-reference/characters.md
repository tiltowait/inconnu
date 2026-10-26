---
description: Commands for creating, displaying, and updating characters.
---

# Characters

New to **Inconnu**? Start with the [Quickstart](../guides/quickstart/README.md).

Commands that take `player` let admins work with other players' characters.

## /character wizard

```
/character wizard
```

Gives you a link to the web-based character creator. Follow the prompts on the website. Admins can set `spc:Yes` to make a Storyteller character.

Once your character exists, add [Traits](traits.md) for anything the wizard didn't cover.

## /character import

```
/character import source:Progeny file:<file>
```

Imports a character exported from [Progeny](https://progeny.odin-matthias.de/) as a JSON file.

## /character display

```
/character display character:[character] player:[player]
```

Shows the character's Health, Willpower, Humanity, experience, and other trackers. The **Traits** button shows their Attributes, Skills, and other Traits. If you have several characters and don't name one, you can pick from a list.

## /character update

```
/character update parameters:<KEY=VALUE ...> character:[character] player:[player]
```

Updates any number of trackers at once:

| Key | Description |
| --- | --- |
| `name` | The character's new name |
| `splat` | The character type: `vampire`, `mortal`, `ghoul`, or `thinblood` |
| `health` | Maximum Health |
| `willpower` | Maximum Willpower |
| `humanity` | Humanity |
| `sh` | Superficial Health damage |
| `ah` | Aggravated Health damage |
| `sw` | Superficial Willpower damage |
| `aw` | Aggravated Willpower damage |
| `stains` | Stains |
| `hunger` | Hunger |
| `potency` | Blood Potency |
| `unspent_xp` | Unspent XP |
| `lifetime_xp` | Total XP earned, spent and unspent |

Numeric keys take `+X` or `-X` to adjust the current value, or `X` to set it.

> [!TIP]
> **Example:** _Add_ 2 Superficial Health damage, _set_ Aggravated Health damage to 1, and _add_ a Stain:
>
> ```
> /character update parameters:sh+2 ah=1 stains+1 character:Nadea
> ```

> [!WARNING]
> Lowering maximum Health or Willpower too far loses damage. Lowering `lifetime_xp` below `unspent_xp` also lowers `unspent_xp`.

## /character adjust

The same changes as `/character update`, chosen from individual options instead of typed as `KEY=VALUE` pairs: `new_name`, `health`, `willpower`, `humanity`, `template`, `sup_hp`, `agg_hp`, `sup_wp`, `agg_wp`, `stains`, `unspent_xp`, `lifetime_xp`, `hunger`, and `potency`.

## /character delete

```
/character delete character:<character>
```

**Inconnu** asks you to confirm first.

> [!CAUTION]
> **This cannot be undone!** Deleting a character also deletes its Traits, macros, and images.

## /character profile

Every character has a public profile with a biography and description. [Supporters](https://www.patreon.com/tiltowait) can also add [images](../premium/character-images.md).

```
/character profile edit:<character>
```

Opens a dialogue to edit the profile.

```
/character profile character:[character] player:[player]
```

Shows a profile. Anyone can view anyone's profile. Some of **Inconnu's** responses link to your profile on the web.

## /character convictions

```
/character convictions edit:<character>
```

Opens a dialogue with three fields for your Convictions.

```
/character convictions character:[character] player:[player]
```

Shows a character's Convictions. You can also right-click a user and choose **Apps → Convictions**.

## RP headers

Many play-by-post servers start posts with a header showing the character's status, such as the scene's location and Blush of Life. **Inconnu** can post these for you.

### /update header

```
/update header character:[character]
```

Opens a dialogue to set the scene's location, evident Merits and Flaws, and temporary effects.

### /header

```
/header
```

Posts the header. To change it for this post only, use `blush`, `hunger`, `location`, `merits`, `flaws`, or `temporary`. To change it permanently, use `/update header`.

### Fixing mistakes

Right-click a posted header and choose **Apps → Header: Edit** to change its location, or **Apps → Header: Delete** to remove it.

> [!NOTE]
> **Menu not showing up?** The Android Discord app can be finicky with context menus, or you may lack permission to use them in the channel. Ask your server admin.
