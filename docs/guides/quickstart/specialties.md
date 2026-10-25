# 🥇 Specialties

When you create a character in V5, you are given several skill specialties that add a single die to appropriate rolls. You can enter them in the [character wizard](creating-a-character.md), or add them afterward.

> [!NOTE]
> **Adding Specialties**
>
> ```
> /specialties add specialties:<TRAIT1>=<SPEC1>,<SPEC2>,...<SPECN> [TRAIT2]=...
> ```

As you can see, you can add multiple specialties at a time. You can treat these specialties as normal skills and attributes; they are automatically worth one die each. You can add them to your rolls just like you add any other skill.

> [!TIP]
> **Example:** Nadea has a Medicine specialty called _Cadavers_.
>
> ```
> /specialties add specialties:Medicine=Cadavers
> ```

![Discord screenshot showing the specialties add command](../../assets/specialties_add.png "Example screenshot")

To remove specialties, you use the same syntax:

> [!WARNING]
> **Removing Specialties**
>
> ```
> /specialties remove specialties:<TRAIT1>=<SPEC1>,[SPEC2]...
> ```

### Listing specialties

You can see your specialties near the bottom of the `/traits list` command:

![Discord screenshot showing specialties in traits list](../../assets/specialties_list.png "Example display")

### Rolling

You can roll with a specialty using "dot-syntax". For example, if you have a Brawl specialty called Kindred, you can access it by `brawl.kindred`.

![Discord screenshot showing a specialty roll](../../assets/roll_specialty.png "Example roll")

> [!NOTE]
> Just like normal traits, you can use shorthand so long as **Inconnu** can tell what specialty and skill combo you're referring to. Instead of `brawl.kindred`, you might write `brawl.kin`, `b.k`, or even `.k`—so long as what you type is unambiguous.

When you roll with a specialty, one die is automatically added to the dice pool. In addition, the specialty is written in parentheses after the Skill (e.g. "Brawl (Kindred)").

![Discord screenshot showing a roll with a specialty](../../assets/specialty_output.png "Example output")
