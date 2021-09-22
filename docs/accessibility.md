# Accessibility Mode

By default, **Inconnu** displays its output using embeds and both custom and presupplied emoji. While this makes for attractive output, some screen-reading software has trouble with this style of presentation. To account for this, **Inconnu** has an accessibility mode that disables embeds and minimizes bolds and italics.

```
/accessibility enable:ENABLE scope:[SCOPE]
```

| Parameter | Description                                                                    | Notes               |
|-----------|--------------------------------------------------------------------------------|---------------------|
| `enable`  | Whether to enable accessibility mode                                           | Required            |
| `scope`   | "Self only" to affect only yourself; "Entire server" to affect the entire server | Default `Self only` |

?> If you enable accessibility mode for yourself, the setting will follow you across servers.

!> **Accessibility trumps inaccessibility.** If a user enables accessibility mode, that setting will override a server's *disabling* of the feature (but only for that user). Similarly, if a *server* enables accessibility mode, it overrides any user's explicit disabling of the feature.
