# Updating Traits

This command uses the same syntax as [adding traits](adding-traits.md).

```
/traits update traits:<trait=rating ...> character:[character]
```

| Parameter   | Description                             |
| ----------- | --------------------------------------- |
| `trait`     | The name of the trait to update         |
| `rating`    | The trait's rating (Optional)           |
| `character` | The name of the character being updated |

Multiple traits can be updated at once.

> [!NOTE]
> **Example:** Updating Nadea's Awareness trait to 3:
>
> ```
> /traits update traits:Awareness=3 character:Nadea
> ```

> [!WARNING]
> You must provide the full name of the trait to update.

> [!CAUTION]
> Attempting to update a trait that doesn't exist will yield an error. Read the previous page to learn how to add traits.
