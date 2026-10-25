---
description: >-
  Maintain a log of player-character experience gains and expenditures with the
  /experience command group.
---

# Experience Management

Experience can be awarded to or deducted from characters with `/experience award` and `/experience deduct`, respectively. Both commands have the following parameters:

| Parameter   | Description                                              |
| ----------- | -------------------------------------------------------- |
| `player`    | The player who owns the character                        |
| `character` | The character from whom to award/deduct XP               |
| `amount`    | The amount of XP to award/deduct                         |
| `scope`     | Whether to apply the operation to lifetime or current XP |
| `reason`    | An admin-given note about the reason for the change      |

> [!NOTE]
> Players and admins may view their characters' experience logs with the `/experience log` command. Admins can also right-click a user and choose **Apps → Experience Log**.

**To remove a log entry**, use the `/experience remove entry` command. This takes a `player`, `character`, and `log_index` parameter. The `log_index` is the log entry number as shown by `/experience log`.

When removing an entry, the confirmation message will give the admin an option to reverse the XP change; i.e. if the entry was an award of 10 lifetime XP, a button will appear that, when clicked, will subtract 10 lifetime XP.

### Bulk experience

If you manage a large server, the `/bulk award xp` command can save a lot of time. This command pops up a modal dialogue with the following required parameters:

| Parameter       | Description                                                  |
| --------------- | ------------------------------------------------------------ |
| Reason          | The reason the XP is being granted. **Example:** "Weekly XP" |
| Experience list | A list of characters and the XP to grant, separated by line. |

The `list` must follow this format:

```
N xp <@User ID> Character name
```

Where `N` is the amount of XP to give that character, `User ID` is the player's Discord ID, and `Character name` is the character's name.

If there are any errors in your input (misspelled character name, invalid user, etc.), then **no** experience will be rewarded. You will instead see a list of lines **Inconnu** understood, followed by a list of error lines.

#### Syntax example:

```
5 xp <@1234567890> Nadea Theron
3 xp <@0987654321> Billy Bill
4 xp <@3485734857> Jimmy Maxwell
```
