# Rolling

```
/vm syntax:<macro_name> [pool overrides] [hunger override] [difficulty override]
```

| Parameter             | Description                                    |
| --------------------- | ---------------------------------------------- |
| `macro_name`          | The macro's name                               |
| `pool overrides`      | Any additions/subtractions to make to the pool |
| `hunger override`     | Optionally override the macro's Hunger setting |
| `difficulty override` | Optionally override the macro's difficulty     |

> [!WARNING]
> If you wish to use `difficulty override`, then you _must_ supply a `hunger override`, which can be as simple as typing _hunger_.

> [!TIP]
> **Example:** Rolling a macro called _hunt_ with a two-die penalty, standard `hunger`, and a difficulty override of _4_.
>
> ```
> /vm syntax:hunt-2 hunger 4
> ```

> [!NOTE]
> **Why** `/vm`**?** Macro rolling does not make use of the `/macro` command family namespace. This is intentional. By keeping macro rolling similar to the general roll command, users can quickly type it without having to choose from a list. If `/vr` means "vampire roll", then `/vm` means "vampire roll macro".
