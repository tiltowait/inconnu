# Adding Traits

```
/trait add traits:<trait=rating ...> character:[character]
```

| Parameter   | Description                                        |
| ----------- | -------------------------------------------------- |
| `trait`     | The name of the trait to add                       |
| `rating`    | The trait's rating (Optional)                      |
| `character` | The name of the character being updated (Optional) |

Multiple traits can be added at once.

> [!TIP]
> **Example:** Adding Oblivion 4, Fortitude 2, and Stunning 2 to Nadea:
>
> ```
> /traits add traits:Oblivion=4 Fortitude=2 Stunning=2 character:Nadea
> ```

> [!CAUTION]
> Attempting to add a trait that already exists will result in an error. Check the next page to learn how to update traits.
