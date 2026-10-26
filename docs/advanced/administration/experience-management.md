---
description: >-
  Maintain a log of player-character experience gains and expenditures with the
  /experience command group.
---

# Experience Management

`/experience award` and `/experience deduct` add or remove a character's XP. Both take:

| Parameter   | Description                                              |
| ----------- | -------------------------------------------------------- |
| `player`    | The player who owns the character                        |
| `character` | The character to award or deduct XP  |
| `amount`    | The amount of XP to award/deduct                         |
| `scope`     | Whether to apply the operation to lifetime or unspent XP |
| `reason`    | An admin-given note about the reason for the change      |

> [!NOTE]
> Players and admins may view their characters' experience logs with the `/experience log` command. Admins can also right-click a user and choose **Apps → Experience Log**.

**To remove a log entry**, use `/experience remove entry` with `player`, `character`, and `log_index` (the entry's number in `/experience log`).

The confirmation offers a button to reverse the entry's XP change, such as subtracting 10 lifetime XP for a 10-XP award.

## Bulk experience

`/bulk award xp` awards XP to many characters at once. It opens a dialogue with two fields:

| Parameter       | Description                                                  |
| --------------- | ------------------------------------------------------------ |
| Reason          | The reason the XP is being granted. **Example:** "Weekly XP" |
| Experience list | Characters and the XP to grant, one per line |

Each line of the list follows this format:

```
N xp <@User ID> Character name
```

`<@User ID>` is a user mention, using the player's Discord ID.

If any line has an error, such as a misspelled character name, **no** XP is awarded; **Inconnu** shows which lines it understood and which failed.

### Example

```
5 xp <@1234567890> Nadea Theron
3 xp <@0987654321> Billy Bill
4 xp <@3485734857> Jimmy Maxwell
```
