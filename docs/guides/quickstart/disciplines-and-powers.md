# 🪄 Disciplines & powers

While **Inconnu** is not a reference tool, it can nonetheless track your character's Discipline ratings and known powers. There's no requirement that the name you give a Discipline is "official"; you can call them whatever you want!

> [!NOTE]
> **Adding Disciplines**
>
> ```
> /disciplines add disciplines:DISC1=VALUE [DISC2=VALUE2] ...
> ```
>
> You can add multiple Disciplines at a time.

> [!TIP]
> **Example**
>
> Adding Auspex 2 and Oblivion 3 to a character:
>
> ```
> /disciplines add disciplines:Auspex=2 Oblivion=3
> ```

![Discord screenshot showing disciplines add](../../assets/disciplines_add.png "Example")

### Powers

While not a requirement, you can add powers to a Discipline and use them in rolls just like specialties. Unlike specialties, however, using a power doesn't add dice. It's purely a way to reduce ambiguity in roll output.

The syntax is identical to [adding specialties](specialties.md):

> [!NOTE]
> **Adding powers**
>
> ```
> /powers add powers:<DISC1>=<POWER1>,[POWER2],... [DISC2]=...
> ```

![Discord screenshot showing powers add](../../assets/powers_add.png "Example")

The same holds true for removing and rolling powers. Powers and Disciplines can be found in the output of `/traits list`.

> [!NOTE]
> **Power bonus** **is automatically added** if your Blood Potency is 2 or higher! No need to use a custom trait.
