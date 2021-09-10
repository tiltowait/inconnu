# Quickstart

## The *Quickest* Quickstart

Don't care about managing characters? Trait pools don't interest you? That's fine; you can still use Inconnu.

### Basic Roll Syntax

```
//v <pool> [hunger] [difficulty]
```

[More information here.](rolls.md) Now, on with the show ...

## Creating your first character

You may store as many characters on as many servers as you like. Each character is unique to the server on which you created it. To create a character, type:

```
/character create
```

You should see the command show up above the textbox. Discord will require you to provide a name for the character, character type, HP, WP, etc.

Once you have finished, **Inconnu** will DM you with the creation wizard. Follow the prompts to supply the ratings for all 9 Attributes and 27 Skills. Once you've finished, you're good to go!

!> You must complete the creation wizard before you can use your character. It can take a little while, but it's a one-time deal (per character) that enables you to access Inconnu's advanced features. So have your character sheet ready and get going!

## Trait Pools

As discussed above, the basic roll syntax calls for a `pool` plus optional values for `hunger` and `difficulty`. While you can provide raw numbers for these values, you may also provide variables in the form of your character traits. The `pool`, in particular, is very flexible, allowing you to build a simple math equation to determine the number of dice to roll.

**Example:** Nadea is performing research at the library. She's at *hunger 2*, and the information is hard to find, so the roll is against *difficulty 4*. The pool is *Resolve* plus *Academics*, and she has a research specialty that grants her a bonus die. The roll syntax is:

```
//v resolve + academics + 1 2 4
```

**Inconnu** will look up her *Resolve* and *Academics* traits and add them together with *1* to produce the correct pool, wich is then rolled against *difficulty 4* with *hunger 2*.

?> Notice that we didn't capitalize *Resolve* or *Academics*? That's fine. **Inconnu** doesn't care about cases. In fact, we didn't even need to write out the entire trait names! You can provide an abbreviated name so long as **Inconnu** can expand it to a *single* trait name. Thus, we could have supplied `r` for *Resolve* and `ac` for *Academics*, making our syntax a much quicker `//v r + ac + 1 2 4`!

!> You'll notice we didn't provide a character name in our roll. So long as you have only **one character**, you won't need to supply a character name for most functions. As soon as you add a second, however, you will need to supply the name of the character so **Inconnu** knows which traits to look up.

You may also supply a trait for `hunger` (appropriately enough, you can use *hunger*) and `difficulty`, but only the `pool` may have math operators.

## Adding additional traits

In addition to the standard array of Attributes and Skills, you may define as many additional 1-5-dot traits as you like. A common use is to add your Discipline ratings, as these are frequently rolled.

Nadea has *4* dots in *Oblivion*, *2* in *Fortitude* and *2* in *Potence*. To add it, we simply write:

```
/traits add Oblivion=4 Fortitude=2 Potence=2
```

You can add an arbitrary number of traits in a single command. If you want to *update* an *existing* trait, you can use `/traits update` instead. And, of course, you may delete traits with `/traits delete`.

?> **Want to keep things secret?** **Inconnu** features Incognito Mode. Simply omit the ratings from your added traits, and you will be prompted to set them in DMs. Our command for Nadea thus becomes: `/traits add Oblivion Fortitude Potence`. You can mix and match explicit and secret traits in a single command.

!> Unlike with rolls, trait modification and deletion require you to be *explicit* in your typing. You can't write *ac* to represent *Academics*. This is done to prevent you from accidentally creating a bunch of useless traits or modifying/deleting the wrong thing.

## Modifying your base trackers

As we saw when we created Nadea, each character has base trackers: Humanity, Health, Willpower, and Hunger. In addition, **Inconnu** tracks both *current* XP and *total* XP. Modifying these is done with the `/character update` command and is similar to the initial character creation process or adding traits.

There are, however, some additional factors to consider. While you can increase your total *Health* by *1* with `/character update health=+1`, you can also apply damage with the special `sh` and `ah` keys. The former applies/sets/removes *Superficial Damage*, and the latter applies *Aggravated Damage*.

Nadea got in a scrap and took *2* levels of *Superficial Damage* plus *1* level of *Aggravated Damage*. To reflect this, we type:

```
/character update sh=+2 ah=+1
```

Similarly, Willpower damage uses the `sw` and `aw` keys, and you can set *current XP* with the `current_xp` key and *total XP* with the `total_xp` key.

Humanity has its own damage type in the form of Stains. To apply Stains: `/character update stains=+X` to add, `-x` to subtract, and plain `x` to set to an absolute value.

## Rouse, Remorse, and Resonance

Finally, we have three last commands: `/rouse`, `/remorse`, and `/resonance`.

### Rouse Checks

**Inconnu** can perform a rouse check and automatically update your Hunger in a single roll: `/rouse`. In fact, if you want to perform multiple rouses at once, you can simply add a number: `/rouse 2`. If the die resulted in a 1 or a 10, **Inconnu** will let you know (currently, Oblivion rouse checks result in Stains if you roll either of those two numbers).

### Remorse Checks

If your character has any Stains, you can run `/remorse`. This rolls a number of dice equal to the number of unmarked Humanity boxes (minimum 1). If successful, your Humanity stays the same. If unsuccessful, your Humanity is automatically decreased by 1. In either case, your Stains are wiped clean.

?> Every time you manually set your Humanity with `/character update humanity=X`, your Stains are automatically cleared. This way, you can quickly reflect character degeneration.

## That's it!

You should now have all the information you need to use **Inconnu** effectively. If you ever forget how to use a certain command, there is a comprehensive help system behind the `/help` command. If you want a more detailed (or at least easier to read) reference, you may click the links in the sidebar.
