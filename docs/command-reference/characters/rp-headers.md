# RP Headers

Many play-by-post servers use some form of role-play headers that list current character status (such as scene location and Blush of Life). If your server uses headers, **Inconnu** can cut down the amount of copy+pasting your players need to do, as well as make life easier for mobile users!

### Setting the Header

```
/update header character:<CHARACTER> blush:<Yes/No/NA>
```

Once entered, this command surfaces a modal dialogue that allows you to set scene location, evident merits/flaws, and temporary effects impacting your character.

### Posting the Header

```
/header
```

Yes, it's that simple. But if you need to make one-time changes, then there are several optional parameters you can set:

| Parameter   | Description                                             |
| ----------- | ------------------------------------------------------- |
| `blush`     | Whether Blush of Life is active                         |
| `location`  | The location for the scene                              |
| `merits`    | Apparent merits possessed by the character              |
| `flaws`     | Apparent flaws suffered by the character                |
| `temporary` | Any temporary effects currently impacting the character |

> [!NOTE]
> The parameters you set in `/header` are **temporary**. They only impact that specific header. To make permanent changes, use `/update header`.

### Fixing Mistakes

If you post a duplicate header or want to change a header's details after-the-fact, you can do so via a context menu command. Right-click your header message, hover over "Apps", and select "Delete RP Header" or "Fix RP Header".

> [!WARNING]
> You can't set Blush of Life via the context menu.

> [!NOTE]
> Menu not showing up? The Android Discord client can be very finnicky with context menu commands. You may also not have permissions in the channel to use them. Speak with your server admin!
