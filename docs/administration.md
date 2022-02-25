# Administration

**Inconnu** features a number of administration commands ranging from [server settings](settings.md) to [character management](character-tracking.md).

Server administrators can use the `player` parameter of the following commands:

* `/vr` and `/roll`
* `/character display`
* `/character update`
* `/traits list`

The `player` parameter allows admins to look up other players' character stats, modify their trackers, and roll on behalf of another player's character.

## Admin-Only Commands

### Experience Management

The `/experience` command group allows admins to create an experience log for their players' characters.

Experience can be `award`ed or `deduct`ed from characters with `/experience award` and `/experience deduct`, respectively. Both commands have the following parameters:

| Parameter   | Description                                              |
|-------------|----------------------------------------------------------|
| `player`    | The player who owns the character                        |
| `character` | The character from whom to award/deduct XP               |
| `amount`    | The amount of XP to award/deduct                         |
| `scope`     | Whether to apply the operation to lifetime or current XP |
| `reason`    | An admin-given note about the reason for the change      |

?> Players and admins may view their characters' experience logs with the `/experience log` command.

**To remove a log entry**, use the `/experience remove entry` command. This takes a `player`, `character`, and `log_index` parameter. The `log_index` is the log entry number as shown by `/experience log`.

When removing an entry, the confirmation message will give the admin an option to reverse the XP change; i.e. if the entry was an award of 10 lifetime XP, a button will appear that, when clicked, will subtract 10 lifetime XP.

## Character Transfers

```
/transfer current_owner:CURRENT_OWNER character:CHARACTER new_owner:NEW_OWNER
```

This command will transfer a character from its current owner to a new one. Both users will be pinged when this operation is complete.

?> If you transfer a character to **Inconnu**, that character will become an SPC and usable by any server admin.
