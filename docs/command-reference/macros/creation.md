# Creation

```
/macro create name:<name> pool:<pool> hunger:[Yes/No] hunt:[Yes/No] difficulty:[difficulty] comment:[comment] character:[character]
```

| Parameter       | Description                                     | Notes                                                                             |
| --------------- | ----------------------------------------------- | --------------------------------------------------------------------------------- |
| `name`          | The name of the macro                           | A-Z plus underscores                                                              |
| `pool`          | The pool and (optional) difficulty for the roll |                                                                                   |
| `hunger`        | Whether to use Hunger in the roll               |                                                                                   |
| `hunt`          | Whether this is a "hunt" macro                  | If set to _Yes_, then success on the roll will surface a dialogue to slake Hunger |
| `difficulty`    | The roll's difficulty (default 0)               | Default 0                                                                         |
| `rouses`        | The number of Rouse checks to make              | Default 0                                                                         |
| `reroll_rouses` | Whether to re-roll the macro's Rouse checks     | Default `No`                                                                      |
| `staining`      | Whether to give a stain on a 1 or 10            | Default `No`                                                                      |
| `comment`       | A comment to add when rolling                   | Optional                                                                          |
| `character`     | The character who owns the macro                |                                                                                   |

> [!NOTE]
> `pool` follows the same syntax as standard [rolls](../../guides/quickstart/rolling-with-traits.md) and may include traits.

> [!NOTE]
> **Automatic rouse checks:** If `rouses` is greater than 0, **Inconnu** will automatically make an appropriate number of Rouse checks when you use the macro. `reroll_rouses` will have no effect if `rouses` is equal to 0.

> [!WARNING]
> Macro names may not exceed 50 characters. Macro comments may not exceed 300 characters.

> [!TIP]
> **Example:** Creating a macro called hunt with a `pool` of _Resolve + Medicine_, `difficulty` 3, using current Hunger, and a comment:
>
> ```
> /macro create name:hunt pool:resolve+medicine hunger:Yes difficulty:3 comment:Nadea hunts mortuaries for fresh bodies hunt:Yes
> ```
