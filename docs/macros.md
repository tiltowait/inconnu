# Macros

Another of **Inconnu's** advanced features is macro support. A macro is a time-saving command that allows you to save a pool and optional difficulty for later use. For example, you might save a `hunt` command that uses your `Resolve + Medicine` traits, or you might make a `summon_spirit` macro that rolls `Resolve + Oblivion` at difficulty `3`. Used this way, macros speed up your play by reducing the number of times you have to crack open the book.

?> **No Hunger?** Due to the frequency at which Hunger changes throughout normal play, macros do not track Hunger. However, when you call a macro, you can supply Hunger on the spot.

All macro management is done through the `/macro` application command prefix. As you begin typing, Discord should automatically show a list of command options above your textbox. Simply click/tap the one you want (or continue to type in the name). On the desktop, you can tab through command parameters, while mobile lets you tap through.

## Creation

```
/macro create <syntax> [character]
```

| Parameter   | Description                                   |
|-------------|-----------------------------------------------|
| `syntax`    | The pool and (optionally) hunger for the roll |
| `comment`   | A comment to add when rolling                 |
| `character` | The character who owns the macro              |

?> `syntax` follows the same syntax as standard [rolls](rolls.md#basic-syntax).

[filename](includes/character-requirement.md ':include')

## Retrieval

This command will list all macros owned by a given character.

```
/macro list [character]
```

| Parameter   | Description                                   |
|-------------|-----------------------------------------------|
| `character` | The character of interest                     |

[filename](includes/character-requirement.md ':include')

## Deletion

```
/macro delete <macro> [character]
```

| Parameter   | Description                                   |
|-------------|-----------------------------------------------|
| `macro`    | The pool and (optionally) hunger for the roll  |
| `character` | The character who owns the macro              |

[filename](includes/character-requirement.md ':include')

## Rolling

```
/vm <syntax> [character]
```

[filename](includes/character-requirement.md ':include')

* At a minimum, `syntax` must begin with the macro name
* To add *Hunger*, add a number 0-5 after the macro name
* To add *Difficulty*, add a positive integer after *Hunger*

?> **Why `/vm`?** Macro rolling does not make use of the `/macro` command family namespace. This is intentional. By keeping macro rolling similar to the general roll command, users can quickly type it without having to choose from a list. If `//v` means "vampire roll", then `/vm` means "vampire roll macro".
