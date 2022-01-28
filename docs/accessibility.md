# Accessibility Mode

By default, **Inconnu** displays its output using embeds and both custom and presupplied emoji. While this makes for attractive output, some screen-reading software has trouble with this style of presentation. To account for this, **Inconnu** has an accessibility mode that disables embeds and minimizes bolds and italics.

```
/accessibility enable:ENABLE
```

This command changes it only for the active user. To change it for the entire server, see [Server Settings](settings.md).

?> Accessibility mode will follow you across servers.

!> **Accessibility trumps inaccessibility.** If a user enables accessibility mode, that user's rolls will use accessibility mode even if a server disables it. Similarly, if a *server* enables accessibility mode, the mode will be enabled for all users, regardless of individual settings.
