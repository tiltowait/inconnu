# Disciplines & powers

**Inconnu** tracks your character's Discipline ratings and known powers. Names don't have to be official; call them whatever you like!

> [!NOTE]
> **Adding Disciplines**
>
> ```
> /disciplines add disciplines:DISC1=VALUE [DISC2=VALUE2] ...
> ```
>
> You can add multiple Disciplines at once.

> [!TIP]
> **Example**
>
> Adding Auspex 2 and Oblivion 3 to a character:
>
> ```
> /disciplines add disciplines:Auspex=2 Oblivion=3
> ```

![Discord screenshot showing Disciplines add](../../assets/disciplines_add.png "Example")

### Powers

You can also add powers to a Discipline and roll them like specialties. Unlike specialties, they don't add dice; they just make your roll output clearer.

The syntax matches [adding specialties](specialties.md):

> [!NOTE]
> **Adding powers**
>
> ```
> /powers add powers:<DISC1>=<POWER1>,[POWER2],... [DISC2]=...
> ```

![Discord screenshot showing powers add](../../assets/powers_add.png "Example")

Removing and rolling powers work the same way, and `/traits list` shows your Disciplines and powers.

> [!NOTE]
> **Power bonus is automatically added** to rolls that include a Discipline if your Blood Potency is 2 or higher! No need to use a custom Trait.
