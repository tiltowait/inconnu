# Updating

```
/macro update macro:MACRO parameters:PARAMETERS character:CHARACTER
```

| Parameter    | Description                      |
| ------------ | -------------------------------- |
| `macro`      | The name of the macro to update  |
| `parameters` | The `KEY=VALUE` pairs            |
| `character`  | The character who owns the macro |

The `parameters` are the same as in macro creation.

| Key             | Description                                 | Notes                |
| --------------- | ------------------------------------------- | -------------------- |
| `name`          | The macro's new name                        | A-Z plus underscores |
| `pool`          | The replacement pool                        | Must be a valid pool |
| `hunger`        | Whether to use Hunger in the roll           | "Yes" or "No"        |
| `difficulty`    | The roll's difficulty                       | Must be 0 or higher  |
| `rouses`        | The number of Rouse checks to make          | Must be 0-3          |
| `reroll_rouses` | Whether to re-roll the macro's Rouse checks | "Yes" or "No"        |
| `comment`       | A comment to add when rolling               |                      |

> [!TIP]
> **Example:** Updating the `difficulty` to _4_.
>
> ```
> /macro update macro:hunt parameters:difficulty=4
> ```

> [!NOTE]
> As with many other commands, you may update multiple parameters at once.
